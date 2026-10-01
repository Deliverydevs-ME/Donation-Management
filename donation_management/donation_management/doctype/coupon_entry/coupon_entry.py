# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, getdate, today
from frappe.desk.reportview import get_match_cond

from donation_management.donation_management.api import (
	create_collection_journal_entry,
	get_default_company,
	set_collection_accounting_details,
	validate_collection_accounting_details,
)
from donation_management.donation_management.validations import validate_unique_field


COUPON_COLORS = {
	"Zakat": "Green",
	"Sadqa": "Blue",
	"Atiya": "Blue",
	"Fitra": "Purple",
	"Fidya": "Orange",
}

COUPON_SERIES = "COP-.####"


class CouponEntry(Document):
	def before_insert(self):
		self.set_coupon_number()

	def validate(self):
		book = self.set_coupon_book_details()
		self.validate_number_of_pages()
		self.validate_book_page_available()
		self.set_coupon_color()
		self.set_accounting_details(book)
		if not self.coupon_number:
			self.set_coupon_number()
		validate_unique_field(self, "coupon_number", "Coupon Number")

	def before_submit(self):
		self.validate_collection_accounting()

	def on_update(self):
		previous_doc = self.get_doc_before_save()
		if previous_doc and previous_doc.book:
			sync_book_page_counts(previous_doc.book, book_serial_no=previous_doc.book_serial_no)

		self.sync_book_pages()

	def on_submit(self):
		self.create_journal_entry()
		self.allocate_coupon_book_leaves()
		self.sync_book_pages()

	def on_cancel(self):
		self.cancel_linked_journal_entry()
		from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
			cancel_leaves_for_coupon_entry,
		)

		cancel_leaves_for_coupon_entry(self.name, self.journal_entry)
		self.sync_book_pages()

	def on_trash(self):
		if self.book:
			sync_book_page_counts(self.book, exclude_coupon=self.name, book_serial_no=self.book_serial_no)

	def set_coupon_book_details(self):
		if not self.book:
			frappe.throw(frappe._("Book is required."))

		book = _get_coupon_book_details(self.book, self.book_serial_no)

		if self.is_new() and book.status != "Issued":
			frappe.throw(frappe._("Book {0} must be Issued before creating a Coupon.").format(self.book))

		if not self.is_new() and book.status not in ("Issued", "Returned", "Closed"):
			frappe.throw(frappe._("Book {0} must be Issued, Returned, or Closed.").format(self.book))

		self.coupon_color = book.coupon_color
		self.coupon_type = book.coupon_type
		self.coupon_value = cint(book.coupon_value)
		self.amount = cint(self.number_of_pages or 1) * cint(book.coupon_value)
		self.volunteer_name = book.volunteer_name
		self.area = book.volunteer_area
		self.warehouse = book.warehouse
		self.receipt_format = book.receipt_format
		self.from_receipt_no = book.from_receipt_no
		self.to_receipt_no = book.to_receipt_no
		if not self.company:
			self.company = get_default_company()

		return book

	def validate_number_of_pages(self):
		if self.number_of_pages in (None, ""):
			self.number_of_pages = 1

		if cint(self.number_of_pages) <= 0:
			frappe.throw(frappe._("Number of Pages must be greater than zero. Enter a positive number."))

	def validate_book_page_available(self):
		if not self.book:
			return

		book_type = frappe.db.get_value("Book Assignment", self.book, "book_type")
		book = frappe.db.get_value("Book Assignment", self.book, ["total_pages", "remaining_pages"], as_dict=True)
		if not book:
			return

		is_existing_coupon = not self.is_new() and frappe.db.exists(
			"Coupon Entry",
			{
				"name": self.name,
				"book": self.book,
			},
		)
		if frappe.db.exists(
			"Book Assignment Detail",
			{
				"parent": self.book,
				"parenttype": "Book Assignment",
				"parentfield": "assigned_books",
				"book_type": "Coupon Book",
			},
		) or book_type == "Mixed":
			book = frappe.db.get_value(
				"Book Assignment Detail",
				{"parent": self.book, "book_serial_no": self.book_serial_no, "book_type": "Coupon Book"},
				["total_pages", "remaining_pages"],
				as_dict=True,
			)
			if not book:
				return

		used_coupon_pages = get_used_coupon_pages(
			self.book,
			exclude_coupon=self.name if is_existing_coupon else None,
			book_serial_no=self.book_serial_no,
		)

		if used_coupon_pages + cint(self.number_of_pages) > cint(book.total_pages):
			frappe.throw(
				frappe._(
					"Only {0} unused page(s) are available for Book {1}. You entered {2}. Please enter a number within the available pages."
				).format(
					max(cint(book.total_pages) - used_coupon_pages, 0),
					self.book,
					cint(self.number_of_pages),
				)
			)

	def sync_book_pages(self):
		if not self.book:
			return

		sync_book_page_counts(self.book, book_serial_no=self.book_serial_no)

	def set_coupon_color(self):
		coupon_type = self.get_coupon_type()
		self.coupon_color = COUPON_COLORS.get(coupon_type)

	def set_accounting_details(self, book=None):
		if not book:
			book = _get_coupon_book_details(self.book, self.book_serial_no)
		set_collection_accounting_details(self, "Coupon Entry", book.coupon_type)

	def validate_collection_accounting(self):
		validate_collection_accounting_details(self, "Coupon Entry", self.coupon_type, self.amount)

	def create_journal_entry(self):
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			return self.journal_entry

		return create_collection_journal_entry(
			self,
			source_type="Coupon Entry",
			donation_type=self.coupon_type,
			amount=self.amount,
			posting_date=self.posting_date or today(),
			remarks=self.get_accounting_remarks(),
			received_from=self.get_received_from(),
		)

	def cancel_linked_journal_entry(self):
		if not self.journal_entry or not frappe.db.exists("Journal Entry", self.journal_entry):
			return

		entry = frappe.get_doc("Journal Entry", self.journal_entry)
		if entry.docstatus == 1:
			entry.cancel()
		frappe.db.set_value(self.doctype, self.name, "accounting_status", "Cancelled", update_modified=False)
		self.accounting_status = "Cancelled"

	def allocate_coupon_book_leaves(self):
		from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
			allocate_coupon_entry_leaves,
		)

		allocate_coupon_entry_leaves(self)

	def get_accounting_remarks(self):
		return "Coupon Entry: {0} | Coupon Type: {1} | Book: {2}".format(
			self.name,
			self.coupon_type,
			self.book,
		)

	def get_received_from(self):
		return self.donor_name or self.volunteer_name or self.book

	def set_coupon_number(self):
		self.coupon_number = make_autoname(COUPON_SERIES)

	def get_coupon_type(self):
		if not self.book:
			frappe.throw(frappe._("Book is required before generating Coupon Number."))

		coupon_type = _get_coupon_book_details(self.book, self.book_serial_no).coupon_type
		if coupon_type not in COUPON_COLORS:
			frappe.throw(frappe._("Coupon Type must be Zakat, Sadqa, Atiya, Fitra, or Fidya."))

		return coupon_type


# Keep Python imports from older app code working while the persisted DocType
# name is migrated to Coupon Entry.
Coupon = CouponEntry


def _get_coupon_book_details(book_name, book_serial_no=None, allow_missing_serial=False):
	book = frappe.db.get_value(
		"Book Assignment",
		book_name,
		[
			"coupon_type",
			"coupon_color",
			"coupon_value",
			"volunteer_name",
			"issued_to_employee",
			"volunteer_area",
			"warehouse",
			"status",
			"book_type",
			"remaining_pages",
			"receipt_format",
			"from_receipt_no",
			"to_receipt_no",
		],
		as_dict=True,
	)
	if not book:
		frappe.throw(frappe._("Book {0} was not found.").format(book_name))

	if book.book_type not in ("Coupon Book", "Mixed"):
		frappe.throw(frappe._("Coupons can only be created against Coupon Book records."))

	has_coupon_rows = frappe.db.exists(
		"Book Assignment Detail",
		{
			"parent": book_name,
			"parenttype": "Book Assignment",
			"parentfield": "assigned_books",
			"book_type": "Coupon Book",
		},
	)
	if book.book_type == "Mixed" or has_coupon_rows:
		if not book_serial_no:
			if allow_missing_serial:
				book.requires_book_serial_no = 1
				return book
			frappe.throw(frappe._("Book Serial No is required for this Coupon Book Assignment."))

		row = frappe.db.get_value(
			"Book Assignment Detail",
			{
				"parent": book_name,
				"parenttype": "Book Assignment",
				"parentfield": "assigned_books",
				"book_serial_no": book_serial_no,
				"book_type": "Coupon Book",
			},
			[
				"book_type",
				"coupon_type",
				"coupon_value",
				"coupon_color",
				"warehouse",
				"total_pages",
				"remaining_pages",
				"receipt_format",
				"from_receipt_no",
				"to_receipt_no",
			],
			as_dict=True,
		)
		if not row:
			frappe.throw(frappe._("Book Serial No {0} is not a Coupon Book in this assignment.").format(book_serial_no))
		book.update(row)

	# Mixed assignments keep the issuing employee in issued_to_employee while
	# volunteer_name is hidden on the parent form. Coupons should still inherit
	# that employee from the selected Book Assignment.
	if not book.volunteer_name:
		book.volunteer_name = book.issued_to_employee

	return book


@frappe.whitelist()
def get_coupon_book_details(book, book_serial_no=None):
	return _get_coupon_book_details(book, book_serial_no, allow_missing_serial=True)


def get_used_coupon_pages(book, exclude_coupon=None, book_serial_no=None):
	# A cancelled Coupon Entry has discarded physical pages. Keep it in the
	# consumed count so cancellation never makes those pages available again.
	conditions = ["book = %(book)s"]
	params = {"book": book}
	if exclude_coupon:
		conditions.append("name != %(exclude_coupon)s")
		params["exclude_coupon"] = exclude_coupon
	if book_serial_no:
		conditions.append("book_serial_no = %(book_serial_no)s")
		params["book_serial_no"] = book_serial_no

	return cint(
		frappe.db.sql(
			f"""
			select sum(ifnull(number_of_pages, 1))
			from `tabCoupon Entry`
			where {" and ".join(conditions)}
			""",
			params,
		)[0][0]
	)


def sync_book_page_counts(book, exclude_coupon=None, book_serial_no=None):
	book_type = frappe.db.get_value("Book Assignment", book, "book_type")
	has_coupon_rows = frappe.db.exists(
		"Book Assignment Detail",
		{
			"parent": book,
			"parenttype": "Book Assignment",
			"parentfield": "assigned_books",
			"book_type": "Coupon Book",
		},
	)
	if book_type == "Mixed" or has_coupon_rows:
		if not book_serial_no:
			return
		row = frappe.db.get_value(
			"Book Assignment Detail",
			{"parent": book, "book_serial_no": book_serial_no, "book_type": "Coupon Book"},
			["name", "total_pages"],
			as_dict=True,
		)
		if not row:
			return
		total_pages = row.total_pages
		used_pages = get_used_coupon_pages(book, exclude_coupon=exclude_coupon, book_serial_no=book_serial_no)
		frappe.db.set_value(
			"Book Assignment Detail",
			row.name,
			{"used_pages": used_pages, "remaining_pages": max(cint(total_pages) - used_pages, 0)},
			update_modified=False,
		)
		return

	total_pages = frappe.db.get_value("Book Assignment", book, "total_pages")
	if total_pages is None:
		return

	used_pages = get_used_coupon_pages(book, exclude_coupon=exclude_coupon)
	remaining_pages = max(cint(total_pages) - used_pages, 0)
	frappe.db.set_value(
		"Book Assignment",
		book,
		{
			"used_pages": used_pages,
			"remaining_pages": remaining_pages,
		},
		update_modified=False,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_books(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		select
			name,
			coupon_type,
			warehouse,
			remaining_pages
		from `tabBook Assignment`
		where
			docstatus < 2
			and status = 'Issued'
			and (
				(book_type = 'Coupon Book' and ifnull(remaining_pages, 0) > 0)
				or exists (
					select detail.name from `tabBook Assignment Detail` detail
					where detail.parent = `tabBook Assignment`.name and detail.parenttype = 'Book Assignment'
					and detail.book_type = 'Coupon Book' and ifnull(detail.remaining_pages, 0) > 0
				)
			)
			and (
				name like %(txt)s
				or coupon_type like %(txt)s
				or warehouse like %(txt)s
			)
			{match_cond}
		order by modified desc
		limit %(page_len)s offset %(start)s
		""".format(match_cond=get_match_cond("Book Assignment")),
		{
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_coupon_serials(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})
	if not filters.get("book"):
		return []
	return frappe.db.sql(
		"""
		select book_serial_no, book_serial_no
		from `tabBook Assignment Detail`
		where parent = %(book)s and parenttype = 'Book Assignment'
			and book_type = 'Coupon Book' and ifnull(remaining_pages, 0) > 0
			and book_serial_no like %(txt)s
		order by idx limit %(start)s, %(page_len)s
		""",
		{"book": filters.book, "txt": f"%{txt}%", "start": start, "page_len": page_len},
	)
