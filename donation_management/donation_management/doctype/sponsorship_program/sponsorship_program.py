# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from donation_management.donation_management.validations import validate_unique_field


class SponsorshipProgram(Document):
	def validate(self):
		validate_unique_field(self, "program_name", "Program Name")

		if flt(self.monthly_donation) <= 0:
			frappe.throw(frappe._("Monthly Donation must be greater than zero."))

		if flt(self.duration_months) <= 0:
			frappe.throw(frappe._("Duration Months must be greater than zero."))

		self.total_program_donation = flt(self.monthly_donation) * flt(self.duration_months)
