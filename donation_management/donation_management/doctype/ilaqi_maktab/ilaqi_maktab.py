# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, flt, getdate, today

from donation_management.donation_management.validations import validate_unique_field


class IlaqiMaktab(Document):
	def validate(self):
		validate_unique_field(self, "maktab_name", "Maktab Name")

		if flt(self.fixed_contribution) < 0:
			frappe.throw(frappe._("Fixed Contribution cannot be negative."))
		if flt(self.expected_monthly_cost) < 0:
			frappe.throw(frappe._("Expected Monthly Cost cannot be negative."))
		if not self.status:
			self.status = "Active"


def get_frequency_months(frequency):
	return {
		"Monthly": 1,
		"Quarterly": 3,
		"Half Yearly": 6,
		"Yearly": 12,
	}.get(frequency or "Monthly", 1)


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
