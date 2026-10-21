# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from donation_management.donation_management.doctype.ilaqi_maktab.ilaqi_maktab import (
	sync_head_count,
)


class MaktabEmployeeAssignment(Document):
	def validate(self):
		self.validate_assigned_employees()

	def after_insert(self):
		self.sync_maktab_head_counts()

	def on_update(self):
		previous = self.get_doc_before_save()
		self.sync_maktab_head_counts(previous.ilaqi_maktab if previous else None)

	def on_trash(self):
		sync_head_count(self.ilaqi_maktab, exclude_assignment=self.name)

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

	def sync_maktab_head_counts(self, previous_maktab=None):
		for ilaqi_maktab in {self.ilaqi_maktab, previous_maktab} - {None, ""}:
			sync_head_count(ilaqi_maktab)
