# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class DonationBookCollection(Document):
	def validate(self):
		self.total_amount = flt(self.cash_amount) + flt(self.online_amount) + flt(self.returned_unused_amount)
		if flt(self.total_amount) <= 0:
			frappe.throw(frappe._("Total Amount must be greater than zero."))

	def on_cancel(self):
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.cancel()
