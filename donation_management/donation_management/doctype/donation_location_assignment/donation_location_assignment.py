# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class DonationLocationAssignment(Document):
	def validate(self):
		self.validate_dates()
		self.validate_employee()
		self.validate_overlap()
		self.set_status()

	def before_submit(self):
		self.set_status()

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", "Cancelled", update_modified=False)

	def validate_dates(self):
		if not self.start_date:
			frappe.throw(frappe._("Start Date is required."))

		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(frappe._("End Date cannot be before Start Date."))

	def validate_employee(self):
		if not self.employee:
			frappe.throw(frappe._("Employee is required."))

		status = frappe.db.get_value("Employee", self.employee, "status")
		if not status:
			frappe.throw(frappe._("Employee {0} was not found.").format(self.employee))
		if status != "Active":
			frappe.throw(frappe._("Employee {0} must be Active.").format(self.employee))

	def validate_overlap(self):
		if not self.employee or not self.start_date:
			return

		overlap = frappe.db.sql(
			"""
			select name
			from `tabDonation Location Assignment`
			where employee = %(employee)s
				and docstatus = 1
				and name != %(name)s
				and start_date <= %(effective_end)s
				and ifnull(end_date, '9999-12-31') >= %(start_date)s
			limit 1
			""",
			{
				"employee": self.employee,
				"name": self.name or "",
				"start_date": getdate(self.start_date),
				"effective_end": getdate(self.end_date) if self.end_date else "9999-12-31",
			},
		)
		if overlap:
			frappe.throw(
				frappe._("Employee {0} already has an overlapping Donation Location Assignment {1}.").format(
					self.employee,
					overlap[0][0],
				)
			)

	def set_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
			return

		current_date = getdate(today())
		if self.docstatus == 0:
			self.status = "Draft"
		elif self.end_date and getdate(self.end_date) < current_date:
			self.status = "Expired"
		elif getdate(self.start_date) > current_date:
			self.status = "Scheduled"
		else:
			self.status = "Active"


def get_assignment_for_date(employee, donation_date):
	if not employee or not donation_date:
		return None

	rows = frappe.get_all(
		"Donation Location Assignment",
		filters={
			"employee": employee,
			"docstatus": 1,
			"start_date": ["<=", getdate(donation_date)],
		},
		fields=["name", "donation_location", "start_date", "end_date"],
		order_by="start_date desc, creation desc",
	)
	rows = [
		row
		for row in rows
		if not row.end_date or getdate(row.end_date) >= getdate(donation_date)
	]

	if len(rows) > 1:
		frappe.throw(
			frappe._("Multiple active Donation Location Assignments found for Employee {0} on {1}.").format(
				employee,
				frappe.format_value(donation_date, {"fieldtype": "Date"}),
			)
		)

	return rows[0] if rows else None


@frappe.whitelist()
def get_effective_donation_location(employee=None, donation_date=None):
	assignment = get_assignment_for_date(employee, donation_date)
	if not assignment:
		return {}

	return {
		"assignment": assignment.name,
		"donation_location": assignment.donation_location,
	}
