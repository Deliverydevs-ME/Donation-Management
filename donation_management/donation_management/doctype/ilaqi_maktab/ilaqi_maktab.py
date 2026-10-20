# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, cint, flt, getdate, today


class IlaqiMaktab(Document):
	def validate(self):
		self.validate_maktab_name()

		if flt(self.fixed_contribution) < 0:
			frappe.throw(frappe._("Fixed Contribution cannot be negative."))
		if flt(self.expected_monthly_cost) < 0:
			frappe.throw(frappe._("Expected Monthly Cost cannot be negative."))
		if not self.status:
			self.status = "Active"
		self.validate_head_count_capacity()

	def validate_maktab_name(self):
		"""Allow an amendment to reuse the name of its cancelled original."""
		if not self.maktab_name:
			return

		existing = frappe.db.exists(
			"Ilaqi Maktab",
			{
				"maktab_name": self.maktab_name,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)
		if existing:
			frappe.throw(
				frappe._("Maktab Name {0} already exists in Ilaqi Maktab {1}.").format(
					self.maktab_name, existing
				),
				title=frappe._("Duplicate Maktab Name"),
			)

	def validate_head_count_capacity(self):
		if self.is_new():
			return

		active_assignments = get_active_assignment_count(self.name)
		if active_assignments > cint(self.head_count):
			frappe.throw(
				frappe._(
					"Head Count cannot be less than active assigned employees. Current active assignments: {0}."
				).format(active_assignments)
			)


def get_frequency_months(frequency):
	return {
		"Monthly": 1,
		"Quarterly": 3,
		"Half Yearly": 6,
		"Yearly": 12,
	}.get(frequency or "Monthly", 1)


def get_active_assignment_count(ilaqi_maktab, exclude_assignment=None):
	if not ilaqi_maktab:
		return 0

	conditions = [
		"assignment.ilaqi_maktab = %(ilaqi_maktab)s",
		"detail.parenttype = 'Maktab Employee Assignment'",
		"detail.parentfield = 'assigned_employees'",
		"detail.status = 'Active'",
	]
	values = {"ilaqi_maktab": ilaqi_maktab}
	if exclude_assignment:
		conditions.append("assignment.name != %(exclude_assignment)s")
		values["exclude_assignment"] = exclude_assignment

	return frappe.db.sql(
		"""
			select count(detail.name)
			from `tabMaktab Employee Assignment Detail` detail
			inner join `tabMaktab Employee Assignment` assignment on assignment.name = detail.parent
			where {0}
		""".format(" and ".join(conditions)),
		values,
	)[0][0]


@frappe.whitelist()
def get_assigned_employees(ilaqi_maktab):
	if not ilaqi_maktab:
		return []

	doc = frappe.get_doc("Ilaqi Maktab", ilaqi_maktab)
	doc.check_permission("read")

	assignments = frappe.db.sql(
		"""
			select
				assignment.name,
				detail.employee,
				detail.start_date,
				detail.end_date,
				detail.salary_cost,
				detail.status
			from `tabMaktab Employee Assignment Detail` detail
			inner join `tabMaktab Employee Assignment` assignment on assignment.name = detail.parent
			where assignment.ilaqi_maktab = %(ilaqi_maktab)s
				and detail.parenttype = 'Maktab Employee Assignment'
				and detail.parentfield = 'assigned_employees'
			order by detail.status asc, detail.start_date desc, detail.modified desc
		""",
		{"ilaqi_maktab": ilaqi_maktab},
		as_dict=True,
	)
	for assignment in assignments:
		assignment.employee_name = frappe.db.get_value("Employee", assignment.employee, "employee_name")

	return assignments


@frappe.whitelist()
def generate_payment_schedule(ilaqi_maktab, from_date=None, to_date=None):
	doc = frappe.get_doc("Ilaqi Maktab", ilaqi_maktab)
	doc.check_permission("write")

	if doc.status != "Active":
		frappe.throw(frappe._("Payment schedule can only be generated for Active Ilaqi Maktab records."))

	from_date = getdate(from_date or today())
	to_date = getdate(to_date or add_months(from_date, 12))
	if to_date < from_date:
		frappe.throw(frappe._("To Date cannot be before From Date."))

	months = get_frequency_months(doc.frequency)
	due_date = from_date
	created = []
	while due_date <= to_date:
		existing = frappe.db.exists(
			"Maktab Payment Schedule",
			{"ilaqi_maktab": doc.name, "due_date": due_date, "docstatus": ["!=", 2]},
		)
		if not existing:
			schedule = frappe.get_doc(
				{
					"doctype": "Maktab Payment Schedule",
					"ilaqi_maktab": doc.name,
					"frequency": doc.frequency,
					"due_date": due_date,
					"due_amount": doc.fixed_contribution,
					"outstanding_amount": doc.fixed_contribution,
					"status": "Pending",
				}
			)
			schedule.insert(ignore_permissions=True)
			created.append(schedule.name)
		due_date = add_months(due_date, months)

	return {"created": created, "count": len(created)}


@frappe.whitelist()
def get_financial_position(ilaqi_maktab):
	payments = frappe.db.sql(
		"""
		select coalesce(sum(amount), 0) as collected, coalesce(sum(advance_amount), 0) as advance
		from `tabMaktab Payment`
		where ilaqi_maktab = %s and docstatus = 1
		""",
		ilaqi_maktab,
		as_dict=True,
	)[0]
	expenses = frappe.db.sql(
		"""
		select coalesce(sum(amount), 0) as expenses
		from `tabMaktab Expense`
		where ilaqi_maktab = %s and docstatus = 1
		""",
		ilaqi_maktab,
		as_dict=True,
	)[0]
	schedules = frappe.db.sql(
		"""
		select coalesce(sum(due_amount), 0) as expected,
			coalesce(sum(outstanding_amount), 0) as outstanding
		from `tabMaktab Payment Schedule`
		where ilaqi_maktab = %s and docstatus != 2
		""",
		ilaqi_maktab,
		as_dict=True,
	)[0]
	return {
		"expected": flt(schedules.expected),
		"collected": flt(payments.collected),
		"advance": flt(payments.advance),
		"outstanding": flt(schedules.outstanding),
		"expenses": flt(expenses.expenses),
		"net_position": flt(payments.collected) - flt(expenses.expenses),
	}
