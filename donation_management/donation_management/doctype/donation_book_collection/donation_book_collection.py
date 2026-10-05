# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, today

from donation_management.donation_management.api import (
	create_collection_journal_entry,
	get_default_company,
	set_collection_accounting_details,
	validate_collection_accounting_details,
)
from donation_management.donation_management.doctype.book_assignment.book_assignment import sync_donation_book_leaves


class DonationBookCollection(Document):
	def validate(self):
		self.set_defaults()
		self.validate_book()
		self.validate_book_serial_no()
		self.populate_assignment_details()
		self.validate_assignment_details()
		self.total_amount = flt(self.cash_amount) + flt(self.online_amount) + flt(self.returned_unused_amount)
		if flt(self.total_amount) <= 0:
			frappe.throw(frappe._("Total Amount must be greater than zero."))
		self.validate_online_payment()
		self.set_accounting_details()
		self.validate_accounting_details()

	def on_submit(self):
		self.collection_date = today()
		self.db_set("collection_date", self.collection_date, update_modified=False)
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
		if self.manual_receipt_number and not self.manual_receipt_date:
			frappe.throw(frappe._("Manual Receipt Date is required when Manual Receipt Number is entered."))

	def get_assigned_serials(self):
		return frappe.get_all(
			"Book Assignment Detail",
			filters={
				"parent": self.book,
				"parenttype": "Book Assignment",
				"parentfield": "assigned_books",
			},
			fields=["book_serial_no", "book_type", "from_receipt_no", "to_receipt_no"],
			order_by="idx asc",
		)

	def populate_assignment_details(self):
		if self.get("book_assignment_details") or not self.book:
			return

		serial_filter = {"book": self.book}
		if self.book_serial_no:
			serial_filter["book_serial_no"] = self.book_serial_no

		leaves = frappe.get_all(
			"Donation Book Leaf",
			filters=serial_filter,
			fields=["book_serial_no", "receipt_number", "manual_receipt_date", "payment_mode", "status"],
			order_by="book_serial_no asc, receipt_number asc",
		)
		order_map = self.get_donation_order_map()
		for leaf in leaves:
			order = order_map.get((leaf.book_serial_no, leaf.receipt_number)) or order_map.get(
				(None, leaf.receipt_number), {}
			)
			self.append(
				"book_assignment_details",
				{
					"book_serial_no": leaf.book_serial_no,
					"receipt_number": leaf.receipt_number,
					"receipt_date": leaf.manual_receipt_date,
					"mode_of_payment": leaf.payment_mode,
					"amount": order.get("amount") or 0,
					"donation_order": order.get("name"),
					"debit_account": order.get("debit_account"),
					"credit_account": order.get("credit_account"),
					"status": leaf.status,
				}
			)

	def get_donation_order_map(self):
		if not self.book:
			return {}
		rows = frappe.db.sql(
			"""
			select parent.name, parent.donation_book_serial_no as book_serial_no,
				parent.manual_receipt_date, parent.mode_of_payment,
				parent.debit_account, parent.credit_account,
				parent.donation_amount as amount, detail.manual_receipt_number as receipt_number
			from `tabDonation Order` parent
			inner join `tabDonation Order Purpose Detail` detail on detail.parent = parent.name
			where parent.donation_book = %(book)s and parent.docstatus != 2
			union all
			select parent.name, parent.donation_book_serial_no as book_serial_no,
				parent.manual_receipt_date, parent.mode_of_payment,
				parent.debit_account, parent.credit_account,
				parent.donation_amount as amount, parent.manual_receipt_number as receipt_number
			from `tabDonation Order` parent
			where parent.donation_book = %(book)s and parent.docstatus != 2
			""",
			{"book": self.book},
			as_dict=True,
		)
		return {(row.book_serial_no, row.receipt_number): row for row in rows if row.receipt_number}

	def validate_assignment_details(self):
		assigned_serials = {row.book_serial_no for row in self.get_assigned_serials() if row.book_serial_no}
		seen = set()
		for row in self.get("book_assignment_details", []):
			key = (row.book_serial_no, row.receipt_number)
			if row.book_serial_no and assigned_serials and row.book_serial_no not in assigned_serials:
				frappe.throw(frappe._("Book Serial No {0} is not part of Book Assignment {1}.").format(row.book_serial_no, self.book))
			if key in seen:
				frappe.throw(frappe._("Receipt {0} is repeated in Book Assignment Details.").format(row.receipt_number))
			seen.add(key)

	def validate_book(self):
		book = frappe.db.get_value(
			"Book Assignment",
			self.book,
			["name", "book_type", "status", "issued_to_employee"],
			as_dict=True,
		)
		if not book:
			frappe.throw(frappe._("Book {0} was not found.").format(self.book))
		has_donation_row = frappe.db.exists(
			"Book Assignment Detail",
			{
				"parent": self.book,
				"parenttype": "Book Assignment",
				"parentfield": "assigned_books",
				"book_type": "Donation Book",
			},
		)
		if book.book_type not in ("Donation Book", "Mixed") and not has_donation_row:
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

	def validate_book_serial_no(self):
		if not self.book_serial_no:
			return

		serial_is_donation_book = frappe.db.exists(
			"Book Assignment Detail",
			{
				"parent": self.book,
				"parenttype": "Book Assignment",
				"parentfield": "assigned_books",
				"book_type": "Donation Book",
				"book_serial_no": self.book_serial_no,
			},
		)
		if not serial_is_donation_book:
			frappe.throw(
				frappe._("Book Serial No {0} is not a Donation Book serial in Book Assignment {1}.").format(
					self.book_serial_no, self.book
				)
			)

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
		return frappe.db.get_value("Book Assignment", self.book, "coupon_type") or "Donation Book"

	def get_accounting_remarks(self):
		return "Donation Book Collection: {0} | Book: {1} | Receipt: {2}".format(
			self.name,
			self.book,
			self.manual_receipt_number or "",
		)

	def get_received_from(self):
		return "Donation Book Collection {0} ({1})".format(self.name, self.book)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_donation_book_assignments(doctype, txt, searchfield, start, page_len, filters=None):
	"""Return only assignments that contain at least one Donation Book row."""
	search = "%{}%".format(txt or "")
	return frappe.db.sql(
		"""
		select book.name,
			concat(book.name, ifnull(concat(' - ', nullif(book.book_serial_numbers, '')), ''))
		from `tabBook Assignment` book
		where book.docstatus != 2
			and book.status in %(statuses)s
			and (
				book.book_type = %(donation_book_type)s
				or exists (
					select detail.name
					from `tabBook Assignment Detail` detail
					where detail.parent = book.name
						and detail.parenttype = 'Book Assignment'
						and detail.parentfield = 'assigned_books'
						and detail.book_type = %(donation_book_type)s
				)
			)
			and (
				book.name like %(search)s
				or ifnull(book.book_serial_numbers, '') like %(search)s
				or exists (
					select detail.name
					from `tabBook Assignment Detail` detail
					where detail.parent = book.name
						and detail.parenttype = 'Book Assignment'
						and detail.parentfield = 'assigned_books'
						and detail.book_type = %(donation_book_type)s
						and (detail.book_serial_no like %(search)s or detail.item like %(search)s)
				)
			)
		order by book.modified desc
		limit %(start)s, %(page_len)s
		""",
		{
			"donation_book_type": "Donation Book",
			"statuses": ("Issued", "Returned", "Closed"),
			"search": search,
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_donation_book_serials(doctype, txt, searchfield, start, page_len, filters=None):
	"""Return donation serials only after a Book Assignment is selected."""
	filters = frappe._dict(filters or {})
	if not filters.get("book"):
		return []

	return frappe.db.sql(
		"""
		select detail.book_serial_no,
			concat(detail.book_serial_no, ' - ', book.name)
		from `tabBook Assignment Detail` detail
		inner join `tabBook Assignment` book on book.name = detail.parent
		where detail.parent = %(book)s
			and detail.parenttype = 'Book Assignment'
			and detail.parentfield = 'assigned_books'
			and detail.book_type = %(donation_book_type)s
			and ifnull(detail.book_serial_no, '') != ''
			and book.docstatus != 2
			and book.status in %(statuses)s
			and detail.book_serial_no like %(search)s
		order by detail.book_serial_no
		limit %(start)s, %(page_len)s
		""",
		{
			"book": filters.get("book"),
			"donation_book_type": "Donation Book",
			"statuses": ("Issued", "Returned", "Closed"),
			"search": "%{}%".format(txt or ""),
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


@frappe.whitelist()
def reopen_collection(collection, reason):
	if not reason:
		frappe.throw(frappe._("Reopen Reason is required."))

	doc = frappe.get_doc("Donation Book Collection", collection)
	doc.check_permission("write")
	if doc.status != "Submitted":
		frappe.throw(frappe._("Only Submitted Donation Book Collections can be reopened."))

	doc.flags.ignore_validate_update_after_submit = True
	doc.status = "Reopened"
	doc.reopen_reason = reason
	doc.reopened_by = frappe.session.user
	doc.reopened_on = now_datetime()
	doc.reopen_count = cint(doc.reopen_count) + 1
	doc.approved_by = frappe.session.user
	doc.save()
	return doc.as_dict()
