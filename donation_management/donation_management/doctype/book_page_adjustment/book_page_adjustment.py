# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class BookPageAdjustment(Document):
	def validate(self):
		self.validate_book()
		self.validate_affected_pages()

	def on_submit(self):
		if self.status == "Draft":
			self.status = "Pending Donation Manager"
			self.db_set("status", self.status, update_modified=False)

	def validate_book(self):
		if not self.book:
			return

		book_details = frappe.db.get_value("Book Assignment", self.book, ["book_type", "status"], as_dict=True)
		if not book_details or book_details.book_type not in ("Coupon Book", "Mixed"):
			frappe.throw(frappe._("Page adjustments can only be requested for Coupon Book records."))

		if book_details.status not in ("Issued", "Returned", "Closed"):
			frappe.throw(
				frappe._("Page adjustments can only be requested for Issued, Returned, or Closed coupon books.")
			)

	def validate_affected_pages(self):
		if cint(self.affected_pages) <= 0:
			frappe.throw(frappe._("Affected Pages must be greater than zero."))

		if not self.book:
			return

		book_details = frappe.db.get_value("Book Assignment", self.book, ["book_type", "total_pages", "book_serial_no"], as_dict=True)
		if not book_details:
			frappe.throw(frappe._("Book Assignment {0} was not found.").format(self.book))

		total_pages = get_coupon_book_total_pages(self.book, self.book_serial_no, book_details)
		if cint(self.affected_pages) > total_pages:
			frappe.throw(
				frappe._("Affected Pages ({0}) cannot exceed Total Pages ({1}).").format(
					self.affected_pages,
					total_pages,
				)
			)

	@frappe.whitelist()
	def approve_by_donation_manager(self):
		self.check_permission("write")
		if self.status != "Pending Donation Manager":
			frappe.throw(frappe._("Only requests pending Donation Manager approval can be approved at this stage."))

		self.status = "Pending Finance Manager"
		self.donation_manager = frappe.session.user
		self.donation_manager_approved_on = now_datetime()
		self.save(ignore_permissions=True)
		return self.status

	@frappe.whitelist()
	def reject_request(self):
		self.check_permission("write")
		if self.status not in ("Pending Donation Manager", "Pending Finance Manager"):
			frappe.throw(frappe._("Only pending requests can be rejected."))

		self.status = "Rejected"
		self.save(ignore_permissions=True)
		return self.status

	@frappe.whitelist()
	def approve_by_finance_manager(self):
		self.check_permission("write")
		if self.status != "Pending Finance Manager":
			frappe.throw(frappe._("Only requests pending Finance Manager approval can be approved at this stage."))

		self.status = "Approved"
		self.finance_manager = frappe.session.user
		self.finance_manager_approved_on = now_datetime()
		self.save(ignore_permissions=True)
		self.apply_adjustment_to_book()
		return self.status

	def apply_adjustment_to_book(self):
		book = frappe.get_doc("Book Assignment", self.book)
		affected = cint(self.affected_pages)
		if book.assigned_books:
			row = next(
				(row for row in book.assigned_books if row.book_serial_no == self.book_serial_no and row.book_type == "Coupon Book"),
				None,
			)
			if not row:
				frappe.throw(frappe._("Coupon Book Serial No {0} was not found in Book Assignment {1}.").format(self.book_serial_no, self.book))
			row.total_pages = max(cint(row.total_pages) - affected, cint(row.used_pages))
			row.remaining_pages = max(cint(row.total_pages) - cint(row.used_pages), 0)
			book.flags.ignore_validate = True
			book.save(ignore_permissions=True)
			return

		if self.adjustment_type == "Less Pages or Leaves":
			new_total = max(cint(book.total_pages) - affected, cint(book.used_pages))
			book.total_pages = new_total
		else:
			book.total_pages = max(cint(book.total_pages) - affected, cint(book.used_pages))

		book.remaining_pages = max(cint(book.total_pages) - cint(book.used_pages), 0)
		book.flags.ignore_validate = True
		book.save(ignore_permissions=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_coupon_book_serials(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})
	book = filters.get("book")
	if not book:
		return []

	book_details = frappe.db.get_value(
		"Book Assignment",
		book,
		["book_type", "book_serial_no", "status", "docstatus"],
		as_dict=True,
	)
	if not book_details or book_details.docstatus == 2 or book_details.status not in ("Issued", "Returned", "Closed"):
		return []

	search = f"%{txt}%"
	rows = frappe.db.sql(
		"""
		select detail.book_serial_no as serial_no
		from `tabBook Assignment Detail` detail
		where detail.parent = %(book)s
			and detail.parenttype = 'Book Assignment'
			and detail.parentfield = 'assigned_books'
			and detail.book_type = 'Coupon Book'
			and ifnull(detail.book_serial_no, '') != ''
			and detail.book_serial_no like %(search)s
		order by detail.book_serial_no
		limit %(start)s, %(page_len)s
		""",
		{"book": book, "search": search, "start": cint(start), "page_len": cint(page_len)},
		as_dict=True,
	)

	if rows:
		return [(row.serial_no, f"{row.serial_no} - {book}") for row in rows]

	if book_details.book_type == "Coupon Book" and book_details.book_serial_no:
		if not txt or txt.lower() in book_details.book_serial_no.lower() or txt.lower() in book.lower():
			return [(book_details.book_serial_no, f"{book_details.book_serial_no} - {book}")]
	return []


def get_coupon_book_total_pages(book, book_serial_no=None, book_details=None):
	book_details = book_details or frappe.db.get_value(
		"Book Assignment",
		book,
		["book_type", "total_pages", "book_serial_no"],
		as_dict=True,
	)
	if not book_details or book_details.book_type not in ("Coupon Book", "Mixed"):
		frappe.throw(frappe._("Page adjustments can only be requested for Coupon Book records."))

	rows = frappe.get_all(
		"Book Assignment Detail",
		filters={
			"parent": book,
			"parenttype": "Book Assignment",
			"parentfield": "assigned_books",
			"book_type": "Coupon Book",
		},
		fields=["book_serial_no", "total_pages"],
	)
	if rows:
		if not book_serial_no:
			frappe.throw(frappe._("Book Serial No is required for this Coupon Book Assignment."))
		row = next((row for row in rows if row.book_serial_no == book_serial_no), None)
		if not row:
			frappe.throw(frappe._("Coupon Book Serial No {0} was not found in this assignment.").format(book_serial_no))
		return cint(row.total_pages)

	if book_details.book_type == "Mixed":
		frappe.throw(frappe._("Coupon Book Serial No is required for a Mixed Book Assignment."))
	if book_serial_no and book_details.book_serial_no and book_serial_no != book_details.book_serial_no:
		frappe.throw(frappe._("Book Serial No {0} is not the Coupon Book serial for this assignment.").format(book_serial_no))
	return cint(book_details.total_pages)
