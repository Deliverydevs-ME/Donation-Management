# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class MaktabExpense(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()
		if flt(self.amount) <= 0:
			frappe.throw(frappe._("Amount must be greater than zero."))
		if not frappe.db.exists("Ilaqi Maktab", self.ilaqi_maktab):
			frappe.throw(frappe._("Ilaqi Maktab {0} was not found.").format(self.ilaqi_maktab))
