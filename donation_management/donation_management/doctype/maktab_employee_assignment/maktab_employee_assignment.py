# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate

from donation_management.donation_management.doctype.ilaqi_maktab.ilaqi_maktab import (
	get_active_assignment_count,
)


class MaktabEmployeeAssignment(Document):
	def validate(self):
		self.validate_assigned_employees()
		self.validate_maktab_head_count()

	def validate_assigned_employees(self):
		if not self.assigned_employees:
			frappe.throw(frappe._("Add at least one employee to Assigned Employees."))

		employees = set()
		for row in self.assigned_employees:
			if row.employee in employees:
				frappe.throw(frappe._("Employee {0} can only be added once.").format(row.employee))
			employees.add(row.employee)

			if not row.status:
				row.status = "Active"
			if row.end_date and getdate(row.end_date) < getdate(row.start_date):
				frappe.throw(
					frappe._("Row {0}: End Date cannot be before Start Date.").format(row.idx)
				)

	def validate_maktab_head_count(self):
		if not self.ilaqi_maktab:
			return

		head_count = cint(frappe.db.get_value("Ilaqi Maktab", self.ilaqi_maktab, "head_count"))
		active_assignments = get_active_assignment_count(self.ilaqi_maktab, exclude_assignment=self.name)
		active_rows = sum(row.status == "Active" for row in self.assigned_employees)

		if active_assignments + active_rows > head_count:
			frappe.throw(
				frappe._(
					"Cannot assign employee to Ilaqi Maktab {0}. Head Count is {1} and active assignments would become {2}."
				).format(self.ilaqi_maktab, head_count, active_assignments + active_rows)
			)
