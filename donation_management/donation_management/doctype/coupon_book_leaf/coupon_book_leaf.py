# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class CouponBookLeaf(Document):
	def before_insert(self):
		if not self.flags.from_book_assignment_generation:
			frappe.throw(frappe._("Coupon Book Leaves are generated automatically from Book Assignment."))

	def validate(self):
		self.set_coupon_value_from_assignment()
		self.validate_parent_assignment_state()
		self.validate_locked_state()
		self.validate_coupon_entry_link()
		self.validate_unique_leaf()

	def set_coupon_value_from_assignment(self):
		if self.coupon_value or not self.book:
			return

		filters = {
			"parent": self.book,
			"parenttype": "Book Assignment",
			"parentfield": "assigned_books",
			"book_type": "Coupon Book",
		}
		if self.book_serial_no:
			filters["book_serial_no"] = self.book_serial_no

		coupon_value = frappe.db.get_value("Book Assignment Detail", filters, "coupon_value")
		if not coupon_value:
			coupon_value = frappe.db.get_value("Book Assignment", self.book, "coupon_value")
		self.coupon_value = cint(coupon_value)

	def before_submit(self):
		self.validate_parent_assignment_state()
		if self.status == "Discarded":
			frappe.throw(frappe._("A discarded Coupon Book Leaf cannot be submitted."))
		if not self.coupon_entry:
			frappe.throw(frappe._("Coupon Entry is required before submitting a Coupon Book Leaf."))

	def before_cancel(self):
		if self.status == "Discarded":
			return

	def on_cancel(self):
		self.db_set(
			{
				"status": "Discarded",
				"accounting_status": "Cancelled",
			},
			update_modified=False,
		)

	def validate_parent_assignment_state(self):
		if not self.book:
			return

		assignment = frappe.db.get_value("Book Assignment", self.book, "docstatus")
		if assignment == 2:
			frappe.throw(
				frappe._(
					"Coupon Book Leaf {0} belongs to cancelled Book Assignment {1} and cannot be edited or submitted."
				).format(self.name or self.receipt_number, self.book)
			)

	def validate_locked_state(self):
		if self.status != "Discarded" or self.is_new():
			return

		previous = self.get_doc_before_save()
		if previous and previous.status == "Discarded":
			frappe.throw(frappe._("Discarded Coupon Book Leaves cannot be edited."))

	def validate_coupon_entry_link(self):
		if not self.coupon_entry:
			return

		entry = frappe.db.get_value(
			"Coupon Entry",
			self.coupon_entry,
			[
				"book",
				"book_serial_no",
				"docstatus",
				"journal_entry",
				"amount",
				"coupon_value",
				"number_of_pages",
				"accounting_status",
			],
			as_dict=True,
		)
		if not entry:
			frappe.throw(frappe._("Coupon Entry {0} was not found.").format(self.coupon_entry))
		if entry.docstatus == 2 and self.status != "Discarded":
			frappe.throw(frappe._("Cancelled Coupon Entries can only have discarded leaves."))
		if entry.book != self.book or (entry.book_serial_no and entry.book_serial_no != self.book_serial_no):
			frappe.throw(frappe._("Coupon Book Leaf must belong to the selected Coupon Entry Book."))

		if entry.docstatus == 1:
			self.journal_entry = entry.journal_entry
			self.accounting_status = entry.accounting_status
			self.coupon_value = cint(entry.coupon_value)
			self.amount = flt(entry.amount) / max(cint(entry.number_of_pages), 1) if entry.get("number_of_pages") else 0
			self.status = "Used"

	def validate_unique_leaf(self):
		if not self.book or not self.receipt_number:
			return

		existing = frappe.db.sql(
			"""
			select name
			from `tabCoupon Book Leaf`
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
				frappe._("Coupon Receipt Number {0} already exists for Book {1}.").format(
					self.receipt_number,
					self.book,
				)
			)


def sync_coupon_book_leaves(book):
	"""Create one pending leaf for every receipt in each assigned Coupon Book range."""
	if not book or not frappe.db.exists("Book Assignment", book):
		return

	book_doc = frappe.get_doc("Book Assignment", book)
	ranges = get_coupon_book_leaf_ranges(book_doc)
	for receipt_range in ranges:
		from donation_management.donation_management.doctype.book_assignment.book_assignment import (
			format_receipt_number,
			get_receipt_number_int,
		)

		from_number = get_receipt_number_int(receipt_range["from_receipt_no"], "From Receipt No")
		to_number = get_receipt_number_int(receipt_range["to_receipt_no"], "To Receipt No")
		for receipt_number in range(from_number, to_number + 1):
			upsert_coupon_book_leaf(
				book_doc,
				receipt_range.get("book_serial_no"),
				format_receipt_number(receipt_range.get("receipt_format"), receipt_number),
				receipt_range.get("coupon_value"),
			)


def get_coupon_book_leaf_ranges(book_doc):
	ranges = []
	if book_doc.assigned_books:
		for row in book_doc.assigned_books:
			if row.book_type == "Coupon Book" and row.from_receipt_no and row.to_receipt_no:
				ranges.append(
					{
						"book_serial_no": row.book_serial_no,
						"receipt_format": row.receipt_format,
						"from_receipt_no": row.from_receipt_no,
						"to_receipt_no": row.to_receipt_no,
						"coupon_value": row.coupon_value,
					}
				)
	elif book_doc.book_type == "Coupon Book" and book_doc.from_receipt_no and book_doc.to_receipt_no:
		ranges.append(
			{
				"book_serial_no": book_doc.book_serial_no,
				"receipt_format": getattr(book_doc, "receipt_format", None),
				"from_receipt_no": book_doc.from_receipt_no,
				"to_receipt_no": book_doc.to_receipt_no,
				"coupon_value": getattr(book_doc, "coupon_value", None),
			}
		)
	return ranges


def upsert_coupon_book_leaf(book_doc, book_serial_no, receipt_number, coupon_value=None):
	existing = frappe.db.exists(
		"Coupon Book Leaf",
		{
			"book": book_doc.name,
			"book_serial_no": book_serial_no,
			"receipt_number": receipt_number,
		},
	)
	if existing:
		if coupon_value not in (None, "") and cint(coupon_value) > 0:
			frappe.db.set_value(
				"Coupon Book Leaf",
				existing,
				"coupon_value",
				cint(coupon_value),
				update_modified=False,
			)
		return existing

	leaf = frappe.get_doc(
		{
			"doctype": "Coupon Book Leaf",
			"book": book_doc.name,
			"book_serial_no": book_serial_no,
			"receipt_number": receipt_number,
			"coupon_value": cint(coupon_value),
			"status": "Pending",
		}
	)
	leaf.flags.from_book_assignment_generation = True
	leaf.insert(ignore_permissions=True)
	return leaf.name


def allocate_coupon_entry_leaves(coupon_entry):
	"""Bind the first unused receipt leaves in ascending range order to an entry."""
	from donation_management.donation_management.doctype.book_assignment.book_assignment import (
		format_receipt_number,
		get_receipt_number_int,
	)

	# A Coupon Entry can be submitted against an assignment created before Leaf
	# generation was introduced. Ensure its receipt range exists before binding.
	sync_coupon_book_leaves(coupon_entry.book)
	range_details = get_coupon_entry_range(coupon_entry)
	from_number = get_receipt_number_int(range_details.from_receipt_no, "From Receipt No")
	to_number = get_receipt_number_int(range_details.to_receipt_no, "To Receipt No")
	receipts = [
		format_receipt_number(range_details.receipt_format, number)
		for number in range(from_number, to_number + 1)
	]
	existing_used = frappe.get_all(
		"Coupon Book Leaf",
		filters={"coupon_entry": coupon_entry.name, "status": "Used"},
		pluck="receipt_number",
		ignore_permissions=True,
	)
	remaining_page_count = max(cint(coupon_entry.number_of_pages) - len(existing_used), 0)
	if not remaining_page_count:
		return
	leaves = [
		frappe.db.get_value(
			"Coupon Book Leaf",
			{
				"book": coupon_entry.book,
				"book_serial_no": coupon_entry.book_serial_no,
				"receipt_number": receipt,
			},
			"name",
		)
		for receipt in receipts
	]
	pending = [
		name for name in leaves if name and frappe.db.get_value("Coupon Book Leaf", name, "status") == "Pending"
	]
	# Legacy leaf records may already be submitted as Used but have no Coupon
	# Entry link. They are safe to repair only within this entry's receipt range.
	used_without_entry = []
	for name in leaves:
		if not name:
			continue
		leaf_data = frappe.db.get_value("Coupon Book Leaf", name, ["status", "coupon_entry"], as_dict=True)
		if leaf_data and leaf_data.status == "Used" and not leaf_data.coupon_entry:
			used_without_entry.append(name)
	available = pending + used_without_entry
	if len(available) < remaining_page_count:
		frappe.throw(
			frappe._(
				"Only {0} unused Coupon Book Leaf page(s) are available in range {1} to {2}."
			).format(len(available), range_details.from_receipt_no, range_details.to_receipt_no)
		)

	per_leaf_amount = flt(coupon_entry.amount) / max(cint(coupon_entry.number_of_pages), 1)
	for leaf_name in available[:remaining_page_count]:
		leaf = frappe.get_doc("Coupon Book Leaf", leaf_name)
		leaf.coupon_entry = coupon_entry.name
		leaf.coupon_value = cint(coupon_entry.coupon_value)
		leaf.status = "Used"
		leaf.amount = per_leaf_amount
		leaf.journal_entry = coupon_entry.journal_entry
		leaf.accounting_status = coupon_entry.accounting_status
		if leaf.docstatus == 1:
			leaf.flags.ignore_validate_update_after_submit = True
			leaf.save(ignore_permissions=True)
		else:
			leaf.save(ignore_permissions=True)
			leaf.submit()


def get_coupon_entry_range(coupon_entry):
	row = frappe.db.get_value(
		"Book Assignment Detail",
		{
			"parent": coupon_entry.book,
			"parenttype": "Book Assignment",
			"parentfield": "assigned_books",
			"book_serial_no": coupon_entry.book_serial_no,
			"book_type": "Coupon Book",
		},
		["receipt_format", "from_receipt_no", "to_receipt_no", "coupon_value"],
		as_dict=True,
	)
	if not row:
		row = frappe.db.get_value(
			"Book Assignment",
			coupon_entry.book,
			["receipt_format", "from_receipt_no", "to_receipt_no", "coupon_value"],
			as_dict=True,
		)
	if not row or not row.from_receipt_no or not row.to_receipt_no:
		frappe.throw(frappe._("Receipt range is missing for Book {0}.").format(coupon_entry.book))
	return row


def cancel_leaves_for_coupon_entry(coupon_entry, journal_entry=None):
	leaves = frappe.get_all(
		"Coupon Book Leaf",
		filters={"coupon_entry": coupon_entry},
		fields=["name", "receipt_number"],
		ignore_permissions=True,
	)
	cancelled_receipts = []
	for row in leaves:
		leaf = frappe.get_doc("Coupon Book Leaf", row.name)
		if leaf.docstatus == 1:
			leaf.flags.ignore_validate_update_after_submit = True
			leaf.flags.ignore_permissions = True
			leaf.cancel()
		else:
			leaf.db_set(
				{"status": "Discarded", "accounting_status": "Cancelled"},
				update_modified=False,
			)
		if journal_entry:
			frappe.db.set_value("Coupon Book Leaf", row.name, "journal_entry", journal_entry, update_modified=False)
		if row.receipt_number:
			cancelled_receipts.append(row.receipt_number)

	return cancelled_receipts


def cancel_leaves_for_book_assignment(book):
	if not book or not frappe.db.table_exists("Coupon Book Leaf"):
		return

	for leaf_name in frappe.get_all(
		"Coupon Book Leaf",
		filters={"book": book, "docstatus": ["!=", 2]},
		pluck="name",
		ignore_permissions=True,
	):
		leaf = frappe.get_doc("Coupon Book Leaf", leaf_name)
		if leaf.docstatus == 1:
			leaf.flags.ignore_validate_update_after_submit = True
			leaf.flags.ignore_permissions = True
			leaf.cancel()
		else:
			leaf.db_set(
				{"status": "Discarded", "accounting_status": "Cancelled"},
				update_modified=False,
			)
