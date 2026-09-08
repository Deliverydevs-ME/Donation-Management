# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class DonationCashHandover(Document):
	def validate(self):
		if not self.company:
			from donation_management.donation_management.api import get_default_company

			self.company = get_default_company()

		if not self.handover_datetime:
			self.handover_datetime = now_datetime()

		self.variance = flt(self.amount) - flt(self.received_amount)
		if self.status == "Received" and self.variance:
			frappe.throw(frappe._("Variance must be resolved before marking handover as Received."))

	def on_submit(self):
		self.status = "Received"
		self.db_set("status", "Received", update_modified=False)

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", "Cancelled", update_modified=False)
