# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


class MaktabPaymentSchedule(Document):
	def validate(self):
		if not frappe.db.exists("Ilaqi Maktab", self.ilaqi_maktab):
			frappe.throw(frappe._("Ilaqi Maktab {0} was not found.").format(self.ilaqi_maktab))
		if flt(self.due_amount) < 0:
			frappe.throw(frappe._("Due Amount cannot be negative."))
		if flt(self.collected_amount) < 0 or flt(self.advance_amount) < 0:
			frappe.throw(frappe._("Collected and Advance Amount cannot be negative."))

		self.outstanding_amount = max(flt(self.due_amount) - flt(self.collected_amount), 0)
		if flt(self.outstanding_amount) <= 0:
			self.status = "Paid"
		elif flt(self.collected_amount) > 0:
			self.status = "Partially Paid"
		elif self.due_date and getdate(self.due_date) < getdate(today()):
			self.status = "Overdue"
		else:
			self.status = "Pending"
