# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class MaktabPayment(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(frappe._("Amount must be greater than zero."))
