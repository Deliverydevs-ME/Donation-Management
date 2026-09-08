# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today


class DonationBookCustodyTransfer(Document):
	def validate(self):
		if not self.transfer_date:
			self.transfer_date = today()

		if self.book:
			book = frappe.db.get_value(
				"Book",
				self.book,
				["book_type", "issued_to_employee", "warehouse"],
				as_dict=True,
			)
			if not book:
				frappe.throw(frappe._("Book {0} was not found.").format(self.book))
			self.book_type = book.book_type
			self.issued_to_employee = self.issued_to_employee or book.issued_to_employee
			self.warehouse = self.warehouse or book.warehouse

	def on_submit(self):
		self.status = "Issued"
		self.db_set("status", "Issued", update_modified=False)

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", "Cancelled", update_modified=False)
