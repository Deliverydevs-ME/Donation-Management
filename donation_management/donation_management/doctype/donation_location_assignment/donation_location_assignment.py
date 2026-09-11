# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class DonationLocationAssignment(Document):
	def validate(self):
		self.validate_dates()
		self.validate_employee()
		validate_assignment_conflicts(
			employee=self.employee,
			donation_location=self.donation_location,
			start_date=self.start_date,
			end_date=self.end_date,
			name=self.name,
		)
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
		validate_assignment_overlap(self.employee, self.start_date, self.end_date, self.name)

	def validate_duplicate_assignment(self):
		validate_duplicate_assignment(
			self.employee,
			self.donation_location,
			self.start_date,
			self.end_date,
			self.name,
		)

	def validate_same_employee_same_dates(self):
		validate_same_employee_same_dates(self.employee, self.start_date, self.end_date, self.name)

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


def format_date_for_message(value):
	if not value:
		return frappe._("blank")

	return frappe.format_value(value, {"fieldtype": "Date"})


def get_assignment_conflict(employee=None, donation_location=None, start_date=None, end_date=None, name=None):
	if not employee or not start_date:
		return None

	duplicate = get_duplicate_assignment(employee, donation_location, start_date, end_date, name)
	if duplicate:
		return {
			"type": "duplicate",
			"title": frappe._("Duplicate Donation Location Assignment"),
			"message": frappe._(
				"Donation Location Assignment {0} already exists for Employee {1}, Location {2}, Start Date {3}, and End Date {4}."
			).format(
				duplicate.name,
				employee,
				donation_location,
				format_date_for_message(start_date),
				format_date_for_message(end_date),
			),
		}

	same_dates = get_same_employee_same_dates_assignment(employee, start_date, end_date, name)
	if same_dates:
		return {
			"type": "same_dates",
			"title": frappe._("Employee Already Assigned"),
			"message": frappe._(
				"Employee {0} already has Donation Location Assignment {1} for the same Start Date {2} and End Date {3}. Existing Location: {4}."
			).format(
				employee,
				same_dates.name,
				format_date_for_message(start_date),
				format_date_for_message(end_date),
				same_dates.donation_location or frappe._("blank"),
			),
		}

	overlap = get_overlapping_assignment(employee, start_date, end_date, name)
	if overlap:
		return {
			"type": "overlap",
			"title": frappe._("Overlapping Assignment"),
			"message": frappe._(
				"Employee {0} already has overlapping Donation Location Assignment {1} from {2} to {3}."
			).format(
				employee,
				overlap.name,
				format_date_for_message(overlap.start_date),
				format_date_for_message(overlap.end_date),
			),
		}

	return None


def get_duplicate_assignment(employee, donation_location, start_date, end_date=None, name=None):
	if not employee or not donation_location or not start_date:
		return None

	duplicate = frappe.db.sql(
		"""
		select name
		from `tabDonation Location Assignment`
		where employee = %(employee)s
			and donation_location = %(donation_location)s
			and docstatus != 2
			and name != %(name)s
			and start_date = %(start_date)s
			and ifnull(end_date, '') = %(end_date)s
		limit 1
		""",
		{
			"employee": employee,
			"donation_location": donation_location,
			"name": name or "",
			"start_date": getdate(start_date),
			"end_date": getdate(end_date) if end_date else "",
		},
		as_dict=True,
	)
	return duplicate[0] if duplicate else None


def get_same_employee_same_dates_assignment(employee, start_date, end_date=None, name=None):
	if not employee or not start_date:
		return None

	existing = frappe.db.sql(
		"""
		select name, donation_location
		from `tabDonation Location Assignment`
		where employee = %(employee)s
			and docstatus != 2
			and name != %(name)s
			and start_date = %(start_date)s
			and ifnull(end_date, '') = %(end_date)s
		limit 1
		""",
		{
			"employee": employee,
			"name": name or "",
			"start_date": getdate(start_date),
			"end_date": getdate(end_date) if end_date else "",
		},
		as_dict=True,
	)
	return existing[0] if existing else None


def get_overlapping_assignment(employee, start_date, end_date=None, name=None):
	if not employee or not start_date:
		return None

	overlap = frappe.db.sql(
		"""
		select name, start_date, end_date
		from `tabDonation Location Assignment`
		where employee = %(employee)s
			and docstatus != 2
			and name != %(name)s
			and start_date <= %(effective_end)s
			and ifnull(end_date, '9999-12-31') >= %(start_date)s
		limit 1
		""",
		{
			"employee": employee,
			"name": name or "",
			"start_date": getdate(start_date),
			"effective_end": getdate(end_date) if end_date else "9999-12-31",
		},
		as_dict=True,
	)
	return overlap[0] if overlap else None


def throw_assignment_conflict(conflict):
	if not conflict:
		return

	frappe.throw(conflict["message"], title=conflict["title"])


def validate_duplicate_assignment(employee, donation_location, start_date, end_date=None, name=None):
	conflict = get_assignment_conflict(employee, donation_location, start_date, end_date, name)
	if conflict and conflict["type"] == "duplicate":
		throw_assignment_conflict(conflict)


def validate_same_employee_same_dates(employee, start_date, end_date=None, name=None):
	conflict = get_assignment_conflict(employee, None, start_date, end_date, name)
	if conflict and conflict["type"] in ("duplicate", "same_dates"):
		throw_assignment_conflict(conflict)


def validate_assignment_overlap(employee, start_date, end_date=None, name=None):
	overlap = get_overlapping_assignment(employee, start_date, end_date, name)
	if not overlap:
		return

	throw_assignment_conflict(
		{
			"type": "overlap",
			"title": frappe._("Overlapping Assignment"),
			"message": frappe._(
				"Employee {0} already has overlapping Donation Location Assignment {1} from {2} to {3}."
			).format(
				employee,
				overlap.name,
				format_date_for_message(overlap.start_date),
				format_date_for_message(overlap.end_date),
			),
		}
	)


@frappe.whitelist()
def validate_assignment_conflicts(employee=None, donation_location=None, start_date=None, end_date=None, name=None):
	conflict = get_assignment_conflict(employee, donation_location, start_date, end_date, name)
	throw_assignment_conflict(conflict)
	return {"ok": True}


@frappe.whitelist()
def get_effective_donation_location(employee=None, donation_date=None):
	assignment = get_assignment_for_date(employee, donation_date)
	if not assignment:
		return {}

	return {
		"assignment": assignment.name,
		"donation_location": assignment.donation_location,
	}
