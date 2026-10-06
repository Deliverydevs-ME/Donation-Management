# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, today


class DonationBookCollection(Document):
	def validate(self):
		self.validate_book()
		self.validate_book_serial_no()
		self.validate_assignment_details()
		if not self.status:
			self.status = "Draft"

	def before_submit(self):
		self.validate_assignment_details(require_rows=True)

	def on_submit(self):
		self.collection_date = today()
		self.status = "Submitted"
		self.db_set(
			{"collection_date": self.collection_date, "status": self.status},
			update_modified=False,
		)

	def on_cancel(self):
		# This document is a reconciliation record only. Donation Orders own their
		# Journal Entries, so cancelling this record must never affect accounting.
		self.db_set("status", "Cancelled", update_modified=False)

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

	def validate_assignment_details(self, require_rows=False):
		if not self.book_assignment_details:
			if require_rows:
				frappe.throw(frappe._("Fetch at least one submitted Donation Book Leaf before submitting."))
			return

		assigned_serials = {row.book_serial_no for row in self.get_assigned_serials() if row.book_serial_no}
		fetched_rows = get_book_assignment_details(self.book, self.book_serial_no)
		fetched_receipts = {(row["book_serial_no"], row["receipt_number"]) for row in fetched_rows}
		seen = set()
		for row in self.get("book_assignment_details", []):
			key = (row.book_serial_no, row.receipt_number)
			if row.book_serial_no and assigned_serials and row.book_serial_no not in assigned_serials:
				frappe.throw(frappe._("Book Serial No {0} is not part of Book Assignment {1}.").format(row.book_serial_no, self.book))
			if key in seen:
				frappe.throw(frappe._("Receipt {0} is repeated in Book Assignment Details.").format(row.receipt_number))
			if key not in fetched_receipts:
				frappe.throw(
					frappe._("Receipt {0} is not a submitted Donation Book Leaf with a submitted Donation Order.").format(
						row.receipt_number
					)
				)
			seen.add(key)

		if seen != fetched_receipts:
			frappe.throw(frappe._("Receipt details have changed. Fetch Submitted Receipts again before saving."))

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
def get_book_assignment_details(book, book_serial_no=None):
	"""Return submitted Donation Book Leaves linked to submitted Donation Orders."""
	if not book:
		return []

	assignment = frappe.get_doc("Book Assignment", book)
	assignment.check_permission("read")
	conditions = [
		"leaf.book = %(book)s",
		"leaf.docstatus = 1",
		"leaf.status = 'Used'",
		"ifnull(leaf.donation_order, '') != ''",
		"order_doc.docstatus = 1",
	]
	values = {"book": book}
	if book_serial_no:
		conditions.append("leaf.book_serial_no = %(book_serial_no)s")
		values["book_serial_no"] = book_serial_no

	leaves = frappe.db.sql(
		"""
		select
			leaf.book_serial_no,
			leaf.receipt_number,
			leaf.manual_receipt_date,
			leaf.payment_mode,
			leaf.amount,
			leaf.donation_order,
			leaf.journal_entry,
			leaf.status
		from `tabDonation Book Leaf` leaf
		inner join `tabDonation Order` order_doc on order_doc.name = leaf.donation_order
		where {conditions}
		order by leaf.book_serial_no asc, leaf.receipt_number asc
		""".format(conditions=" and ".join(conditions)),
		values,
		as_dict=True,
	)
	return [
		{
			"book_serial_no": leaf.book_serial_no,
			"receipt_number": leaf.receipt_number,
			"receipt_date": leaf.manual_receipt_date,
			"mode_of_payment": leaf.payment_mode,
			"amount": leaf.amount or 0,
			"donation_order": leaf.donation_order,
			"journal_entry": leaf.journal_entry,
			"status": leaf.status,
		}
		for leaf in leaves
	]


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
