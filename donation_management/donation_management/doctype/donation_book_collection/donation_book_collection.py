# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from donation_management.donation_management.api import (
	create_collection_journal_entry,
	get_default_company,
	set_collection_accounting_details,
	validate_collection_accounting_details,
)
from donation_management.donation_management.doctype.book.book import sync_donation_book_leaves


class DonationBookCollection(Document):
	def validate(self):
		self.set_defaults()
		self.total_amount = flt(self.cash_amount) + flt(self.online_amount) + flt(self.returned_unused_amount)
		if flt(self.total_amount) <= 0:
			frappe.throw(frappe._("Total Amount must be greater than zero."))
		self.validate_book()
		self.validate_online_payment()
		self.set_accounting_details()
		self.validate_accounting_details()

	def on_submit(self):
		if flt(self.cash_amount):
			journal_entry = create_collection_journal_entry(
				self,
				source_type="Donation Book Collection",
				donation_type=self.get_book_donation_type(),
				amount=self.cash_amount,
				posting_date=self.collection_date,
				remarks=self.get_accounting_remarks(),
				received_from=self.get_received_from(),
			)
			self.db_set("journal_entry", journal_entry, update_modified=False)
		self.db_set("status", "Submitted", update_modified=False)
		sync_donation_book_leaves(self.book)

	def on_cancel(self):
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.cancel()
		self.db_set("status", "Cancelled", update_modified=False)
		sync_donation_book_leaves(self.book)

	def set_defaults(self):
		if not self.company:
			self.company = get_default_company()
		if not self.collection_date:
			self.collection_date = today()

	def validate_book(self):
		book = frappe.db.get_value(
			"Book",
			self.book,
			["name", "book_type", "status", "issued_to_employee"],
			as_dict=True,
		)
		if not book:
			frappe.throw(frappe._("Book {0} was not found.").format(self.book))
		if book.book_type != "Donation Book":
			frappe.throw(frappe._("Donation Book Collection can only be used for Donation Books."))
		if book.status not in ("Issued", "Returned", "Closed"):
			frappe.throw(frappe._("Book must be Issued, Returned, or Closed before collection."))
		if not self.employee:
			self.employee = book.issued_to_employee

	def validate_online_payment(self):
		if not flt(self.online_amount):
			return
		if not self.donation_order:
			frappe.throw(frappe._("Linked Donation Order is required when Online Amount is entered."))
		order = frappe.db.get_value(
			"Donation Order",
			self.donation_order,
			["docstatus", "donation_book", "donation_amount"],
			as_dict=True,
		)
		if not order:
			frappe.throw(frappe._("Donation Order {0} was not found.").format(self.donation_order))
		if order.docstatus != 1:
			frappe.throw(frappe._("Linked Donation Order must be submitted."))
		if order.donation_book and order.donation_book != self.book:
			frappe.throw(frappe._("Linked Donation Order belongs to a different Donation Book."))

	def set_accounting_details(self):
		if not flt(self.cash_amount):
			return
		set_collection_accounting_details(self, "Donation Book Collection", self.get_book_donation_type())

	def validate_accounting_details(self):
		if not flt(self.cash_amount):
			return
		validate_collection_accounting_details(
			self,
			"Donation Book Collection",
			self.get_book_donation_type(),
			self.cash_amount,
		)

	def get_book_donation_type(self):
		return frappe.db.get_value("Book", self.book, "coupon_type") or "Donation Book"

	def get_accounting_remarks(self):
		return "Donation Book Collection: {0} | Book: {1} | Receipt: {2}".format(
			self.name,
			self.book,
			self.manual_receipt_number or "",
		)

	def get_received_from(self):
		return "Donation Book Collection {0} ({1})".format(self.name, self.book)
