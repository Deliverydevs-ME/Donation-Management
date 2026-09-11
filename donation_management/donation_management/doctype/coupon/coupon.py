# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint
from frappe.desk.reportview import get_match_cond

from donation_management.donation_management.validations import validate_unique_field


COUPON_COLORS = {
	"Zakat": "Green",
	"Atiya": "Blue",
	"Fitra": "Purple",
	"Fidya": "Orange",
}

COUPON_SERIES = {
	"Zakat": "ZKT-.#####",
	"Atiya": "ATI-.#####",
	"Fitra": "FTR-.#####",
	"Fidya": "FDY-.#####",
}


class Coupon(Document):
	def before_insert(self):
		self.set_coupon_number()

	def validate(self):
		self.set_coupon_book_details()
		self.validate_number_of_pages()
		self.validate_book_page_available()
		self.set_coupon_color()
		if not self.coupon_number:
			self.set_coupon_number()
		validate_unique_field(self, "coupon_number", "Coupon Number")

	def on_update(self):
		previous_doc = self.get_doc_before_save()
		if previous_doc and previous_doc.book and previous_doc.book != self.book:
			sync_book_page_counts(previous_doc.book)

		self.sync_book_pages()

	def on_trash(self):
		if self.book:
			sync_book_page_counts(self.book, exclude_coupon=self.name)

	def set_coupon_book_details(self):
		if not self.book:
			frappe.throw(frappe._("Book is required."))

		book = frappe.db.get_value(
			"Book",
			self.book,
			[
				"coupon_type",
				"coupon_color",
				"coupon_value",
				"volunteer_name",
				"volunteer_area",
				"warehouse",
				"status",
				"book_type",
			],
			as_dict=True,
		)
		if not book:
			frappe.throw(frappe._("Book {0} was not found.").format(self.book))

		if book.book_type != "Coupon Book":
			frappe.throw(frappe._("Coupons can only be created against Coupon Book records."))

		if self.is_new() and book.status != "Issued":
			frappe.throw(frappe._("Book {0} must be Issued before creating a Coupon.").format(self.book))

		if not self.is_new() and book.status not in ("Issued", "Returned", "Closed"):
			frappe.throw(frappe._("Book {0} must be Issued, Returned, or Closed.").format(self.book))

		self.coupon_color = book.coupon_color
		self.amount = cint(self.number_of_pages or 1) * cint(book.coupon_value)
		self.volunteer_name = book.volunteer_name
		self.area = book.volunteer_area
		self.warehouse = book.warehouse

		return book

	def validate_number_of_pages(self):
		if not cint(self.number_of_pages):
			self.number_of_pages = 1

		if cint(self.number_of_pages) <= 0:
			frappe.throw(frappe._("Number of Pages must be greater than zero."))

	def validate_book_page_available(self):
		if not self.book:
			return

		book = frappe.db.get_value(
			"Book",
			self.book,
			["total_pages", "remaining_pages"],
			as_dict=True,
		)
		if not book:
			return

		is_existing_coupon = not self.is_new() and frappe.db.exists(
			"Coupon",
			{
				"name": self.name,
				"book": self.book,
			},
		)
		used_coupon_pages = get_used_coupon_pages(
			self.book,
			exclude_coupon=self.name if is_existing_coupon else None,
		)

		if used_coupon_pages + cint(self.number_of_pages) > cint(book.total_pages):
			frappe.throw(
				frappe._(
					"Only {0} pages are available for Book {1}. You entered {2} pages."
				).format(
					max(cint(book.total_pages) - used_coupon_pages, 0),
					self.book,
					cint(self.number_of_pages),
				)
			)

	def sync_book_pages(self):
		if not self.book:
			return

		sync_book_page_counts(self.book)

	def set_coupon_color(self):
		coupon_type = self.get_coupon_type()
		self.coupon_color = COUPON_COLORS.get(coupon_type)

	def set_coupon_number(self):
		coupon_type = self.get_coupon_type()
		self.coupon_number = make_autoname(COUPON_SERIES[coupon_type])

	def get_coupon_type(self):
		if not self.book:
			frappe.throw(frappe._("Book is required before generating Coupon Number."))

		coupon_type = frappe.db.get_value("Book", self.book, "coupon_type")
		if coupon_type not in COUPON_COLORS:
			frappe.throw(frappe._("Coupon Type must be Zakat, Atiya, Fitra, or Fidya."))

		return coupon_type


def get_used_coupon_pages(book, exclude_coupon=None):
	conditions = ["book = %(book)s", "docstatus != 2"]
	params = {"book": book}
	if exclude_coupon:
		conditions.append("name != %(exclude_coupon)s")
		params["exclude_coupon"] = exclude_coupon

	return cint(
		frappe.db.sql(
			f"""
			select sum(ifnull(number_of_pages, 1))
			from `tabCoupon`
			where {" and ".join(conditions)}
			""",
			params,
		)[0][0]
	)


def sync_book_page_counts(book, exclude_coupon=None):
	total_pages = frappe.db.get_value("Book", book, "total_pages")
	if total_pages is None:
		return

	used_pages = get_used_coupon_pages(book, exclude_coupon=exclude_coupon)
	remaining_pages = max(cint(total_pages) - used_pages, 0)
	frappe.db.set_value(
		"Book",
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
		from `tabBook`
		where
			docstatus < 2
			and book_type = 'Coupon Book'
			and status = 'Issued'
			and ifnull(remaining_pages, 0) > 0
			and (
				name like %(txt)s
				or coupon_type like %(txt)s
				or warehouse like %(txt)s
			)
			{match_cond}
		order by modified desc
		limit %(page_len)s offset %(start)s
		""".format(match_cond=get_match_cond("Book")),
		{
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)
