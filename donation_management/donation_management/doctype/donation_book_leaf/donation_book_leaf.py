# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DonationBookLeaf(Document):
	def validate(self):
		self.validate_used_leaf_details()
		self.validate_unique_leaf()

	def validate_used_leaf_details(self):
		if self.status != "Used":
			return

		missing = []
		if not self.donor:
			missing.append(frappe._("Donor"))
		if not self.manual_receipt_date:
			missing.append(frappe._("Manual Receipt Date"))
		if missing:
			frappe.throw(
				frappe._("{0} is required when Donation Book Leaf is marked Used.").format(
					", ".join(missing)
				)
			)

	def validate_unique_leaf(self):
		if not self.book or not self.receipt_number:
			return

		existing = frappe.db.sql(
			"""
			select name
			from `tabDonation Book Leaf`
			where book = %(book)s
				and ifnull(book_serial_no, '') = %(book_serial_no)s
				and receipt_number = %(receipt_number)s
				and name != %(name)s
			limit 1
			""",
			{
				"book": self.book,
				"book_serial_no": self.book_serial_no or "",
				"receipt_number": self.receipt_number,
				"name": self.name or "",
			},
		)
		if existing:
			frappe.throw(
				frappe._("Receipt Number {0} already exists for Book {1}.").format(
					self.receipt_number,
					self.book,
				)
			)
