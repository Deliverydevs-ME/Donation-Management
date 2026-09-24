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
		if not self.status:
			self.status = "Active"
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(frappe._("End Date cannot be before Start Date."))
		self.validate_maktab_head_count()

	def validate_maktab_head_count(self):
		if self.status != "Active" or not self.ilaqi_maktab:
			return

		head_count = cint(frappe.db.get_value("Ilaqi Maktab", self.ilaqi_maktab, "head_count"))
		active_assignments = get_active_assignment_count(self.ilaqi_maktab, exclude_assignment=self.name)

		if active_assignments + 1 > head_count:
			frappe.throw(
				frappe._(
					"Cannot assign employee to Ilaqi Maktab {0}. Head Count is {1} and active assignments would become {2}."
				).format(self.ilaqi_maktab, head_count, active_assignments + 1)
			)
