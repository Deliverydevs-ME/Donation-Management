# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, today

from donation_management.donation_management.api import (
	create_collection_journal_entry,
	get_default_company,
	set_collection_accounting_details,
	validate_collection_accounting_details,
)
from donation_management.donation_management.doctype.donor.donor import validate_mohasil_employee


COUPON_COLORS = {
	"Zakat": "Green",
	"Atiya": "Blue",
	"Fitra": "Purple",
	"Fidya": "Orange",
}

DENOMINATIONS = (10, 20, 50, 100, 500, 1000, 5000)
COUPON_VALUES = (10, 50, 100, 500, 1000, 5000)
FINANCE_MANAGER_ROLE = "Finance Manager"
BOOK_TYPE_COUPON = "Coupon Book"
BOOK_TYPE_DONATION = "Donation Book"


class Book(Document):
	def validate(self):
		self.set_defaults()
		self.validate_book_type()
		self.set_book_serial_numbers()
		self.validate_status_transition()
		self.validate_issue_permission()
		if self.is_coupon_book():
			self.clear_donation_book_fields()
			self.validate_book_stock_details()
			self.validate_coupon_book_details()
			self.set_coupon_type_from_item()
			self.validate_coupon_type()
			self.validate_coupon_value()
			self.set_coupon_color()
			self.set_coupon_employee_details()
			self.set_volunteer_area()
			self.set_used_pages_from_coupons()
			self.set_remaining_pages()
			self.validate_page_counts()
			self.validate_book_serial_no()
			self.set_collected_amount_from_coupons()
			self.set_accounting_details()
			self.validate_cash_denominations()
			self.validate_accounting_details()
		else:
			self.clear_coupon_fields()
			self.validate_book_stock_details()
			self.validate_book_serial_no()
			self.validate_donation_book_details()
			self.validate_cash_denominations()
		self.validate_assigned_books()

	def on_update(self):
		if self.is_donation_book():
			sync_donation_book_leaves(self.name)
		if self.is_coupon_book():
			self.create_journal_entry_for_return()

	def set_defaults(self):
		if not self.book_type:
			self.book_type = BOOK_TYPE_COUPON
		if not self.start_date:
			self.start_date = today()
		if not self.company:
			self.company = get_default_company()

	def is_coupon_book(self):
		return self.book_type == BOOK_TYPE_COUPON

	def is_donation_book(self):
		return self.book_type == BOOK_TYPE_DONATION

	def validate_book_type(self):
		if self.book_type not in (BOOK_TYPE_COUPON, BOOK_TYPE_DONATION):
			frappe.throw(frappe._("Book Type must be Coupon Book or Donation Book."))

	def set_book_serial_numbers(self):
		if self.is_donation_book() and self.assigned_books:
			self.book_serial_numbers = ", ".join(
				row.book_serial_no for row in self.assigned_books if row.book_serial_no
			)
		else:
			self.book_serial_numbers = self.book_serial_no

	def validate_coupon_type(self):
		if self.coupon_type not in COUPON_COLORS:
			frappe.throw(frappe._("Coupon Type must be Zakat, Atiya, Fitra, or Fidya."))

	def validate_book_stock_details(self):
		if not self.item:
			frappe.throw(frappe._("Item is required for Book."))
		if not self.warehouse:
			frappe.throw(frappe._("Warehouse is required for Book."))
		if self.is_coupon_book() and not self.book_serial_no:
			frappe.throw(frappe._("Book Serial No is required for Book."))
		if self.is_donation_book() and not (self.assigned_books or self.book_serial_no):
			frappe.throw(frappe._("At least one Book Serial No is required in Assigned Books."))
		if not self.issued_to_employee:
			frappe.throw(frappe._("Issued To Employee is required for Book."))

		item = frappe.db.get_value(
			"Item",
			self.item,
			["disabled", "is_stock_item", "has_serial_no"],
			as_dict=True,
		)
		if not item:
			frappe.throw(frappe._("Item {0} was not found.").format(self.item))
		if cint(item.disabled):
			frappe.throw(frappe._("Item {0} is disabled.").format(self.item))
		if not cint(item.is_stock_item) or not cint(item.has_serial_no):
			frappe.throw(frappe._("Book Item {0} must be a stock Item with serial numbers enabled.").format(self.item))

		employee = frappe.db.get_value("Employee", self.issued_to_employee, ["status"], as_dict=True)
		if not employee:
			frappe.throw(frappe._("Issued To Employee {0} was not found.").format(self.issued_to_employee))
		if employee.status and employee.status != "Active":
			frappe.throw(frappe._("Issued To Employee {0} must be active.").format(self.issued_to_employee))

	def validate_coupon_book_details(self):
		if not is_coupon_item(self.item):
			frappe.throw(frappe._("Only coupon-related Items can be selected for Coupon Book."))

	def validate_coupon_value(self):
		if cint(self.coupon_value) not in COUPON_VALUES:
			frappe.throw(frappe._("Coupon Value must be 10, 50, 100, 500, 1000, or 5000."))

	def set_coupon_color(self):
		self.coupon_color = COUPON_COLORS.get(self.coupon_type)

	def set_coupon_type_from_item(self):
		self.coupon_type = get_coupon_type_from_item(self.item)
		item_coupon_value = get_coupon_value_from_item(self.item)
		if item_coupon_value:
			self.coupon_value = str(item_coupon_value)
		if not self.coupon_type:
			frappe.throw(
				frappe._(
					"Could not identify Coupon Type from Item {0}. Item name, item code, or item group must contain Zakat, Atiya, Fitra, or Fidya."
				).format(self.item)
			)

	def set_volunteer_area(self):
		self.volunteer_area = get_volunteer_area(self.volunteer_name)

	def set_coupon_employee_details(self):
		self.volunteer_name = self.issued_to_employee

	def set_used_pages_from_coupons(self):
		if self.is_new():
			return

		self.used_pages = get_book_used_pages(self.name)

	def set_remaining_pages(self):
		self.remaining_pages = cint(self.total_pages) - cint(self.used_pages)

	def set_collected_amount_from_coupons(self):
		if self.status not in ("Returned", "Closed") or self.is_new():
			return

		self.collected_amount = get_book_collected_amount(self.name)

	def validate_status_transition(self):
		previous_status = self.get_previous_status()
		status = self.status or ""

		if not status:
			return

		if status not in ("Issued", "Returned", "Closed"):
			frappe.throw(frappe._("Status must be Issued, Returned, or Closed."))

		allowed_transitions = {
			None: ("Issued",),
			"": ("Issued",),
			"Issued": ("Returned",),
			"Returned": ("Closed",),
			"Closed": (),
		}

		if previous_status == status:
			return

		if status not in allowed_transitions.get(previous_status, ()):
			frappe.throw(
				frappe._("Book status cannot be changed from {0} to {1}.").format(
					previous_status or frappe._("Blank"),
					status,
				)
			)

	def validate_page_counts(self):
		if cint(self.total_pages) < 0:
			frappe.throw(frappe._("Total Pages cannot be negative."))
		if cint(self.total_pages) <= 0:
			frappe.throw(frappe._("Total Pages must be greater than zero."))
		if cint(self.used_pages) < 0:
			frappe.throw(frappe._("Used Pages cannot be negative."))
		if cint(self.used_pages) > cint(self.total_pages):
			frappe.throw(frappe._("Used Pages cannot exceed Total Pages."))

	def clear_coupon_fields(self):
		self.coupon_type = None
		self.coupon_value = None
		self.coupon_color = None
		self.volunteer_name = None
		self.volunteer_area = None
		self.total_pages = 0
		self.used_pages = 0
		self.remaining_pages = 0
		self.mode_of_payment = None
		self.mode_of_payment_type = None
		self.debit_account = None
		self.credit_account = None
		self.accounting_cost_center = None
		self.journal_entry = None
		self.accounting_status = "Not Posted"

	def clear_donation_book_fields(self):
		self.mohasil = None
		self.from_receipt_no = None
		self.to_receipt_no = None
		self.used_receipts = 0
		self.remaining_receipts = 0
		self.set("assigned_books", [])

	def validate_donation_book_details(self):
		validate_mohasil_employee(self.issued_to_employee, "Issued To Employee")

		if not is_donation_book_item(self.item):
			frappe.throw(frappe._("Only Donation Book Items can be selected for Donation Book."))

		if self.assigned_books:
			total_used_receipts = 0
			total_remaining_receipts = 0
			for row in self.assigned_books:
				self.validate_assigned_book_receipt_range(row)
				row.used_receipts = get_donation_book_used_receipts(
					self.name,
					from_receipt_no=row.from_receipt_no,
					to_receipt_no=row.to_receipt_no,
				) if not self.is_new() else cint(row.used_receipts)
				row.remaining_receipts = max(
					get_receipt_range_count(row.from_receipt_no, row.to_receipt_no) - cint(row.used_receipts),
					0,
				)
				total_used_receipts += cint(row.used_receipts)
				total_remaining_receipts += cint(row.remaining_receipts)

			self.used_receipts = total_used_receipts
			self.remaining_receipts = total_remaining_receipts
			return

		if not self.from_receipt_no or not self.to_receipt_no:
			frappe.throw(frappe._("From Receipt No and To Receipt No are required for Donation Book."))

		from_receipt_no = get_receipt_number_int(self.from_receipt_no, "From Receipt No")
		to_receipt_no = get_receipt_number_int(self.to_receipt_no, "To Receipt No")
		if from_receipt_no > to_receipt_no:
			frappe.throw(frappe._("From Receipt No cannot be greater than To Receipt No."))

		if not self.is_new():
			self.used_receipts = get_donation_book_used_receipts(self.name)
		else:
			self.used_receipts = cint(self.used_receipts)
		self.remaining_receipts = max(get_receipt_range_count(self.from_receipt_no, self.to_receipt_no) - self.used_receipts, 0)

	def validate_assigned_book_receipt_range(self, row):
		if not row.from_receipt_no or not row.to_receipt_no:
			frappe.throw(frappe._("From Receipt No and To Receipt No are required in Assigned Books row {0}.").format(row.idx))

		from_receipt_no = get_receipt_number_int(row.from_receipt_no, "From Receipt No")
		to_receipt_no = get_receipt_number_int(row.to_receipt_no, "To Receipt No")
		if from_receipt_no > to_receipt_no:
			frappe.throw(frappe._("From Receipt No cannot be greater than To Receipt No in Assigned Books row {0}.").format(row.idx))

	def validate_assigned_books(self):
		if not self.is_donation_book():
			self.set("assigned_books", [])
			return

		if not self.assigned_books:
			if self.book_serial_no:
				return
			frappe.throw(frappe._("At least one row is required in Assigned Books."))

		if self.book_serial_no:
			self.book_serial_no = None

		if not self.assigned_books:
			return

		if not self.issued_to_employee:
			frappe.throw(frappe._("Issued To Employee is required before assigning multiple books."))

		seen_serials = set()
		for row in self.assigned_books:
			if not row.book_serial_no:
				frappe.throw(frappe._("Book Serial No is required in Assigned Books row {0}.").format(row.idx))
			if row.book_serial_no in seen_serials:
				frappe.throw(
					frappe._("Book Serial No {0} is selected more than once in Assigned Books.").format(
						row.book_serial_no
					)
				)
			seen_serials.add(row.book_serial_no)

			self.validate_assigned_book_serial_no(row)
			self.validate_book_serial_not_assigned_elsewhere(row.book_serial_no)

	def validate_assigned_book_serial_no(self, row):
		serial_no = frappe.db.get_value(
			"Serial No",
			row.book_serial_no,
			["item_code", "warehouse"],
			as_dict=True,
		)
		if not serial_no:
			frappe.throw(frappe._("Book Serial No {0} was not found.").format(row.book_serial_no))
		if serial_no.item_code != self.item:
			frappe.throw(
				frappe._("Book Serial No {0} belongs to Item {1}, not {2}.").format(
					row.book_serial_no,
					serial_no.item_code,
					self.item,
				)
			)

		if not self.stock_entry and serial_no.warehouse != self.warehouse:
			frappe.throw(
				frappe._("Book Serial No {0} is not available in Warehouse {1}.").format(
					row.book_serial_no,
					self.warehouse,
				)
			)

		existing_book = frappe.db.exists(
			"Book",
			{
				"book_serial_no": row.book_serial_no,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)
		if existing_book:
			frappe.throw(
				frappe._("Book Serial No {0} is already linked with Book {1}.").format(
					row.book_serial_no,
					existing_book,
				)
			)

		row.item = serial_no.item_code
		row.warehouse = self.warehouse
		row.status = self.status

	def validate_book_serial_not_assigned_elsewhere(self, book_serial_no):
		existing = frappe.db.sql(
			"""
			select detail.parent
			from `tabBook Assignment Detail` detail
			inner join `tabBook` parent
				on parent.name = detail.parent
			where detail.book_serial_no = %(book_serial_no)s
				and parent.name != %(current_book)s
				and parent.docstatus != 2
			limit 1
			""",
			{
				"book_serial_no": book_serial_no,
				"current_book": self.name,
			},
		)
		if existing:
			frappe.throw(
				frappe._("Book Serial No {0} is already assigned in Book {1}.").format(
					book_serial_no,
					existing[0][0],
				)
			)

	def validate_book_serial_no(self):
		if not self.book_serial_no:
			return

		serial_no = frappe.db.get_value(
			"Serial No",
			self.book_serial_no,
			["item_code", "warehouse"],
			as_dict=True,
		)
		if not serial_no:
			frappe.throw(frappe._("Book Serial No {0} was not found.").format(self.book_serial_no))
		if serial_no.item_code != self.item:
			frappe.throw(
				frappe._("Book Serial No {0} belongs to Item {1}, not {2}.").format(
					self.book_serial_no,
					serial_no.item_code,
					self.item,
				)
			)

		if not self.stock_entry and serial_no.warehouse != self.warehouse:
			frappe.throw(
				frappe._("Book Serial No {0} is not available in Warehouse {1}.").format(
					self.book_serial_no,
					self.warehouse,
				)
			)

		existing_book = frappe.db.exists(
			"Book",
			{
				"book_serial_no": self.book_serial_no,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)
		if existing_book:
			frappe.throw(
				frappe._("Book Serial No {0} is already linked with Book {1}.").format(
					self.book_serial_no,
					existing_book,
				)
			)

		self.validate_book_serial_not_assigned_elsewhere(self.book_serial_no)

	def validate_cash_denominations(self):
		if self.status in ("Returned", "Closed"):
			if flt(self.collected_amount) <= 0:
				frappe.throw(frappe._("Total Amount Collected is required when Book is returned."))
			if not self.cash_denominations:
				frappe.throw(frappe._("Cash Denominations are required when Book is returned."))

		if not self.cash_denominations and flt(self.collected_amount) <= 0:
			return

		denomination_total = 0
		has_note_count = False
		for row in self.cash_denominations:
			denomination = cint(row.denomination)
			if denomination not in DENOMINATIONS:
				frappe.throw(frappe._("Invalid denomination {0}.").format(row.denomination))

			if cint(row.note_count) < 0:
				frappe.throw(frappe._("Note count cannot be negative for denomination {0}.").format(row.denomination))

			row.amount = denomination * cint(row.note_count)
			denomination_total += flt(row.amount)
			if cint(row.note_count):
				has_note_count = True

		if flt(self.collected_amount) > 0 and not has_note_count:
			frappe.throw(frappe._("At least one denomination count is required."))

		if flt(self.collected_amount) != flt(denomination_total):
			frappe.throw(frappe._("Cash denomination total must match Total Amount Collected."))

	def set_accounting_details(self):
		if not self.is_coupon_book():
			return

		if self.status not in ("Returned", "Closed"):
			return

		set_collection_accounting_details(self, "Book", self.coupon_type)

	def validate_accounting_details(self):
		if not self.is_coupon_book():
			return

		if self.status not in ("Returned", "Closed"):
			return

		validate_collection_accounting_details(
			self,
			"Book",
			self.coupon_type,
			self.collected_amount,
		)

	def validate_issue_permission(self):
		if self.status != "Issued" or self.get_previous_status() == "Issued":
			return

		if FINANCE_MANAGER_ROLE not in frappe.get_roles():
			frappe.throw(frappe._("Only Finance Manager can issue a Book."))

	def create_journal_entry_for_return(self):
		if not self.is_coupon_book():
			return

		if self.status != "Returned":
			return

		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			return

		create_collection_journal_entry(
			self,
			source_type="Book",
			donation_type=self.coupon_type,
			amount=self.collected_amount,
			posting_date=today(),
			remarks=self.get_collection_accounting_remarks(),
			received_from=self.get_collection_received_from(),
		)

	def get_previous_status(self):
		previous_doc = self.get_doc_before_save()
		return previous_doc.status if previous_doc else None

	def get_collection_accounting_remarks(self):
		return "Book: {0} | Coupon Type: {1} | Warehouse: {2} | Volunteer: {3}".format(
			self.name,
			self.coupon_type,
			self.warehouse,
			self.volunteer_name or "",
		)

	def get_collection_received_from(self):
		return "Book {0} ({1})".format(self.name, self.coupon_type)


@frappe.whitelist()
def issue_book(book):
	if FINANCE_MANAGER_ROLE not in frappe.get_roles():
		frappe.throw(frappe._("Only Finance Manager can issue a Book."))

	doc = frappe.get_doc("Book", book)
	if doc.status:
		frappe.throw(frappe._("Only unissued Books can be issued."))
	if doc.stock_entry:
		frappe.throw(frappe._("Book {0} is already linked with Stock Entry {1}.").format(doc.name, doc.stock_entry))

	doc.validate_book_stock_details()
	if doc.is_donation_book():
		doc.validate_assigned_books()
	else:
		doc.validate_book_serial_no()
	stock_entry = create_book_issue_stock_entry(doc)
	doc.stock_entry = stock_entry.name
	doc.status = "Issued"
	doc.save()
	return doc.as_dict()


def create_book_issue_stock_entry(doc):
	items = get_book_issue_items(doc)
	serial_numbers = ", ".join(item["serial_no"] for item in items)
	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"company": doc.company or get_default_company(),
			"stock_entry_type": "Material Issue",
			"purpose": "Material Issue",
			"from_warehouse": doc.warehouse,
			"posting_date": today(),
			"remarks": "Book Issue: {0} | Type: {1} | Serial No: {2} | Issued To: {3}".format(
				doc.name,
				doc.book_type,
				serial_numbers,
				doc.issued_to_employee,
			),
			"items": items,
		}
	)
	stock_entry.flags.ignore_permissions = True
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
	return stock_entry


def get_book_issue_items(doc):
	if doc.is_donation_book() and doc.assigned_books:
		return [
			{
				"item_code": row.item or doc.item,
				"s_warehouse": row.warehouse or doc.warehouse,
				"qty": 1,
				"use_serial_batch_fields": 1,
				"serial_no": row.book_serial_no,
			}
			for row in doc.assigned_books
		]

	return [
		{
			"item_code": doc.item,
			"s_warehouse": doc.warehouse,
			"qty": 1,
			"use_serial_batch_fields": 1,
			"serial_no": doc.book_serial_no,
		}
	]


@frappe.whitelist()
def get_volunteer_area(volunteer_name=None):
	if not volunteer_name:
		return None

	employee_meta = frappe.get_meta("Employee")
	for fieldname in ("area", "custom_area", "branch"):
		if employee_meta.has_field(fieldname):
			return frappe.db.get_value("Employee", volunteer_name, fieldname)

	return None


@frappe.whitelist()
def return_book(
	book,
	collected_amount=None,
	used_pages=None,
	denominations=None,
	mode_of_payment=None,
	debit_account=None,
	credit_account=None,
):
	doc = frappe.get_doc("Book", book)
	if doc.status != "Issued":
		frappe.throw(frappe._("Only issued Books can be returned."))
	if not doc.is_coupon_book():
		frappe.throw(frappe._("Use Return Donation Book for Donation Book records."))

	used_pages = cint(used_pages)
	if used_pages <= 0:
		frappe.throw(frappe._("Used Pages must be greater than zero when returning a Book."))

	if used_pages > cint(doc.total_pages):
		frappe.throw(frappe._("Used Pages cannot exceed Total Pages."))

	if cint(doc.coupon_value) not in COUPON_VALUES:
		frappe.throw(frappe._("Coupon Value must be 10, 50, 100, 500, 1000, or 5000 before returning a Book."))

	calculated_collected_amount = flt(used_pages * cint(doc.coupon_value))
	if collected_amount is not None and flt(collected_amount) != calculated_collected_amount:
		frappe.throw(frappe._("Total Amount Collected must equal Used Pages multiplied by Coupon Value."))

	denominations = frappe.parse_json(denominations) or []
	doc.set("cash_denominations", [])
	for row in denominations:
		if cint(row.get("note_count")):
			doc.append(
				"cash_denominations",
				{
					"denomination": cint(row.get("denomination")),
					"note_count": cint(row.get("note_count")),
				},
			)

	generate_return_coupons(doc, used_pages)

	doc.used_pages = used_pages
	doc.remaining_pages = cint(doc.total_pages) - used_pages
	doc.collected_amount = calculated_collected_amount
	doc.mode_of_payment = mode_of_payment or doc.mode_of_payment
	doc.debit_account = debit_account or doc.debit_account
	doc.credit_account = credit_account or doc.credit_account
	doc.status = "Returned"
	doc.save()
	return doc.as_dict()


def generate_return_coupons(doc, used_pages):
	existing_coupon_pages = get_book_used_pages(doc.name)
	if existing_coupon_pages == used_pages:
		return

	if existing_coupon_pages > used_pages:
		frappe.throw(
			frappe._(
				"Book {0} already has {1} used pages. Please resolve them before returning the book with {2} used pages."
			).format(doc.name, existing_coupon_pages, used_pages)
		)

	for _counter in range(used_pages - existing_coupon_pages):
		coupon = frappe.get_doc(
			{
				"doctype": "Coupon",
				"book": doc.name,
				"number_of_pages": 1,
				"posting_date": today(),
				"amount": cint(doc.coupon_value),
			}
		)
		coupon.flags.from_coupon_book_return = True
		coupon.insert(ignore_permissions=True)


@frappe.whitelist()
def get_book_collected_amount(book):
	if not book:
		return 0

	return flt(
		frappe.db.get_value(
			"Coupon",
			{
				"book": book,
				"docstatus": ["!=", 2],
			},
			"sum(amount)",
		)
	)


def get_book_used_pages(book):
	if not book:
		return 0

	return cint(
		frappe.db.sql(
			"""
			select sum(ifnull(number_of_pages, 1))
			from `tabCoupon`
			where book = %(book)s
				and docstatus != 2
			""",
			{"book": book},
		)[0][0]
	)


@frappe.whitelist()
def close_book(book):
	doc = frappe.get_doc("Book", book)
	if doc.status != "Returned":
		frappe.throw(frappe._("Only returned Books can be closed."))
	if doc.is_donation_book():
		update_donation_book_receipt_usage(doc.name)
		doc.reload()
		validate_donation_book_order_total_matches_return(doc)

	doc.status = "Closed"
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def return_donation_book(book, collected_amount=None, denominations=None, book_collections=None):
	doc = frappe.get_doc("Book", book)
	if not doc.is_donation_book():
		frappe.throw(frappe._("Only Donation Book records can be returned with this action."))
	if doc.status != "Issued":
		frappe.throw(frappe._("Only issued Donation Books can be returned."))

	if book_collections:
		collected_amount = set_donation_book_return_collections(doc, book_collections)
		denominations = get_total_denominations_from_return_collections(book_collections)
	else:
		collected_amount = flt(collected_amount)

	if collected_amount <= 0:
		frappe.throw(frappe._("Total Amount Collected is required when returning a Donation Book."))

	set_cash_denominations(doc, denominations)
	doc.collected_amount = collected_amount
	doc.status = "Returned"
	doc.save()
	return doc.as_dict()


def set_cash_denominations(doc, denominations):
	denominations = frappe.parse_json(denominations) or []
	doc.set("cash_denominations", [])
	for row in denominations:
		if cint(row.get("note_count")):
			doc.append(
				"cash_denominations",
				{
					"denomination": cint(row.get("denomination")),
					"note_count": cint(row.get("note_count")),
				},
			)


def set_donation_book_return_collections(doc, book_collections):
	book_collections = frappe.parse_json(book_collections) or []
	if not book_collections:
		frappe.throw(frappe._("Book return collection details are required."))

	assigned_serials = {
		row.book_serial_no
		for row in doc.assigned_books
		if row.book_serial_no
	}
	if not assigned_serials:
		frappe.throw(frappe._("Assigned Books are required before returning a Donation Book."))

	seen_serials = set()
	total_collected_amount = 0
	doc.set("return_collections", [])

	for collection in book_collections:
		book_serial_no = collection.get("book_serial_no")
		if not book_serial_no:
			frappe.throw(frappe._("Book Serial No is required in return collection details."))
		if book_serial_no not in assigned_serials:
			frappe.throw(
				frappe._("Book Serial No {0} is not assigned to Book {1}.").format(
					book_serial_no,
					doc.name,
				)
			)
		if book_serial_no in seen_serials:
			frappe.throw(frappe._("Book Serial No {0} is repeated in return collection details.").format(book_serial_no))
		seen_serials.add(book_serial_no)

		collected_amount = flt(collection.get("collected_amount"))
		denomination_total = get_denomination_total(collection)
		if collected_amount <= 0:
			frappe.throw(
				frappe._("Collected Amount must be greater than zero for Book Serial No {0}.").format(
					book_serial_no,
				)
			)
		if flt(collected_amount, 2) != flt(denomination_total, 2):
			frappe.throw(
				frappe._("Cash denomination total must match Collected Amount for Book Serial No {0}.").format(
					book_serial_no,
				)
			)

		row = {
			"book_serial_no": book_serial_no,
			"collected_amount": collected_amount,
			"denomination_total": denomination_total,
		}
		for denomination in DENOMINATIONS:
			note_count = cint(collection.get(f"denomination_{denomination}"))
			if note_count < 0:
				frappe.throw(frappe._("Note count cannot be negative for denomination {0}.").format(denomination))
			row[f"denomination_{denomination}"] = note_count

		doc.append("return_collections", row)
		total_collected_amount += collected_amount

	return total_collected_amount


def get_total_denominations_from_return_collections(book_collections):
	book_collections = frappe.parse_json(book_collections) or []
	totals = {denomination: 0 for denomination in DENOMINATIONS}
	for collection in book_collections:
		for denomination in DENOMINATIONS:
			totals[denomination] += cint(collection.get(f"denomination_{denomination}"))

	return [
		{
			"denomination": denomination,
			"note_count": note_count,
		}
		for denomination, note_count in totals.items()
	]


def get_denomination_total(collection):
	return sum(
		denomination * cint(collection.get(f"denomination_{denomination}"))
		for denomination in DENOMINATIONS
	)


def get_receipt_range_count(from_receipt_no, to_receipt_no):
	return max(
		get_receipt_number_int(to_receipt_no, "To Receipt No")
		- get_receipt_number_int(from_receipt_no, "From Receipt No")
		+ 1,
		0,
	)


def get_receipt_number_int(receipt_no, label):
	receipt_no = str(receipt_no or "").strip()
	if receipt_no.startswith("-"):
		frappe.throw(frappe._("{0} cannot be negative.").format(frappe._(label)))
	if not receipt_no or not receipt_no.isdigit():
		frappe.throw(frappe._("{0} must contain digits only.").format(frappe._(label)))
	return cint(receipt_no)


def receipt_number_in_range(receipt_no, from_receipt_no, to_receipt_no):
	receipt_no = get_receipt_number_int(receipt_no, "Manual Receipt Number")
	from_receipt_no = get_receipt_number_int(from_receipt_no, "From Receipt No")
	to_receipt_no = get_receipt_number_int(to_receipt_no, "To Receipt No")
	return from_receipt_no <= receipt_no <= to_receipt_no


def get_donation_book_used_receipts(
	book,
	exclude_order=None,
	from_receipt_no=None,
	to_receipt_no=None,
	donation_book_serial_no=None,
):
	if not book:
		return 0

	values = {"book": book}
	exclude_condition = ""
	if exclude_order:
		exclude_condition = "and parent.name != %(exclude_order)s"
		values["exclude_order"] = exclude_order
	serial_condition = ""
	if donation_book_serial_no:
		serial_condition = "and parent.donation_book_serial_no = %(donation_book_serial_no)s"
		values["donation_book_serial_no"] = donation_book_serial_no

	receipt_rows = frappe.db.sql(
		"""
		select distinct receipt_number
		from (
			select detail.manual_receipt_number as receipt_number
			from `tabDonation Order` parent
			inner join `tabDonation Order Purpose Detail` detail
				on detail.parent = parent.name
			where parent.donation_book = %(book)s
				and parent.docstatus != 2
				and ifnull(detail.manual_receipt_number, '') != ''
				{exclude_condition}
				{serial_condition}
			union
			select parent.manual_receipt_number as receipt_number
			from `tabDonation Order` parent
			where parent.donation_book = %(book)s
				and parent.docstatus != 2
				and ifnull(parent.manual_receipt_number, '') != ''
				{exclude_condition}
				{serial_condition}
		) receipts
		""".format(
			exclude_condition=exclude_condition,
			serial_condition=serial_condition,
		),
		values,
	)

	if from_receipt_no is None or to_receipt_no is None:
		return cint(len(receipt_rows))

	return cint(
		sum(
			1
			for row in receipt_rows
			if receipt_number_in_range(row[0], from_receipt_no, to_receipt_no)
		)
	)


def get_donation_book_order_total(book, exclude_order=None, donation_book_serial_no=None):
	if not book:
		return 0

	conditions = ["donation_book = %(book)s", "docstatus != 2"]
	values = {"book": book}
	if exclude_order:
		conditions.append("name != %(exclude_order)s")
		values["exclude_order"] = exclude_order
	if donation_book_serial_no:
		conditions.append("donation_book_serial_no = %(donation_book_serial_no)s")
		values["donation_book_serial_no"] = donation_book_serial_no

	return flt(
		frappe.db.sql(
			"""
			select sum(ifnull(donation_amount, 0))
			from `tabDonation Order`
			where {conditions}
			""".format(conditions=" and ".join(conditions)),
			values,
		)[0][0]
	)


def update_donation_book_receipt_usage(book):
	if not book or not frappe.db.exists("Book", book):
		return

	book_values = frappe.db.get_value(
		"Book",
		book,
		["book_type", "from_receipt_no", "to_receipt_no"],
		as_dict=True,
	)
	if not book_values or book_values.book_type != BOOK_TYPE_DONATION:
		return

	assigned_rows = frappe.get_all(
		"Book Assignment Detail",
		filters={
			"parent": book,
			"parenttype": "Book",
			"parentfield": "assigned_books",
		},
		fields=["name", "book_serial_no", "from_receipt_no", "to_receipt_no"],
	)
	total_receipts = 0
	if assigned_rows:
		for row in assigned_rows:
			row_total_receipts = get_receipt_range_count(row.from_receipt_no, row.to_receipt_no)
			row_used_receipts = get_donation_book_used_receipts(
				book,
				from_receipt_no=row.from_receipt_no,
				to_receipt_no=row.to_receipt_no,
				donation_book_serial_no=row.book_serial_no,
			)
			row_remaining_receipts = max(row_total_receipts - row_used_receipts, 0)
			frappe.db.set_value(
				"Book Assignment Detail",
				row.name,
				{
					"used_receipts": row_used_receipts,
					"remaining_receipts": row_remaining_receipts,
				},
				update_modified=False,
			)
			total_receipts += row_total_receipts
	else:
		total_receipts = get_receipt_range_count(book_values.from_receipt_no, book_values.to_receipt_no)

	used_receipts = get_donation_book_used_receipts(book)
	remaining_receipts = max(total_receipts - used_receipts, 0)
	frappe.db.set_value(
		"Book",
		book,
		{
			"used_receipts": used_receipts,
			"remaining_receipts": remaining_receipts,
		},
		update_modified=False,
	)
	sync_donation_book_leaves(book)


def sync_donation_book_leaves(book):
	if not book or not frappe.db.exists("Book", book):
		return

	book_doc = frappe.get_doc("Book", book)
	if not book_doc.is_donation_book():
		return

	for receipt_range in get_donation_book_leaf_ranges(book_doc):
		for receipt_number in range(
			get_receipt_number_int(receipt_range["from_receipt_no"], "From Receipt No"),
			get_receipt_number_int(receipt_range["to_receipt_no"], "To Receipt No") + 1,
		):
			upsert_donation_book_leaf(book_doc, receipt_range.get("book_serial_no"), str(receipt_number))

	refresh_donation_book_leaf_usage(book)


def get_donation_book_leaf_ranges(book_doc):
	ranges = []
	if book_doc.assigned_books:
		for row in book_doc.assigned_books:
			if row.from_receipt_no and row.to_receipt_no:
				ranges.append(
					{
						"book_serial_no": row.book_serial_no,
						"from_receipt_no": row.from_receipt_no,
						"to_receipt_no": row.to_receipt_no,
					}
				)
	elif book_doc.from_receipt_no and book_doc.to_receipt_no:
		ranges.append(
			{
				"book_serial_no": book_doc.book_serial_no,
				"from_receipt_no": book_doc.from_receipt_no,
				"to_receipt_no": book_doc.to_receipt_no,
			}
		)
	return ranges


def upsert_donation_book_leaf(book_doc, book_serial_no, receipt_number):
	existing = frappe.db.exists(
		"Donation Book Leaf",
		{
			"book": book_doc.name,
			"book_serial_no": book_serial_no,
			"receipt_number": receipt_number,
		},
	)
	if existing:
		return existing

	leaf = frappe.get_doc(
		{
			"doctype": "Donation Book Leaf",
			"book": book_doc.name,
			"book_serial_no": book_serial_no,
			"receipt_number": receipt_number,
			"status": "Pending",
		}
	)
	leaf.insert(ignore_permissions=True)
	return leaf.name


def refresh_donation_book_leaf_usage(book):
	if not frappe.db.table_exists("Donation Book Leaf"):
		return

	frappe.db.sql(
		"""
		update `tabDonation Book Leaf`
		set status = 'Pending',
			donor = null,
			donation_order = null,
			payment_mode = null,
			manual_receipt_date = null,
			journal_entry = null,
			accounting_status = null
		where book = %s
		""",
		book,
	)

	used_rows = frappe.db.sql(
		"""
		select
			parent.name as donation_order,
			parent.donor_name as donor,
			parent.mode_of_payment as payment_mode,
			parent.manual_receipt_date,
			parent.journal_entry,
			parent.accounting_status,
			parent.donation_book_serial_no as book_serial_no,
			detail.manual_receipt_number as receipt_number
		from `tabDonation Order` parent
		inner join `tabDonation Order Purpose Detail` detail
			on detail.parent = parent.name
		where parent.donation_book = %(book)s
			and parent.docstatus != 2
			and ifnull(detail.manual_receipt_number, '') != ''
		union
		select
			parent.name as donation_order,
			parent.donor_name as donor,
			parent.mode_of_payment as payment_mode,
			parent.manual_receipt_date,
			parent.journal_entry,
			parent.accounting_status,
			parent.donation_book_serial_no as book_serial_no,
			parent.manual_receipt_number as receipt_number
		from `tabDonation Order` parent
		where parent.donation_book = %(book)s
			and parent.docstatus != 2
			and ifnull(parent.manual_receipt_number, '') != ''
		""",
		{"book": book},
		as_dict=True,
	)
	for row in used_rows:
		frappe.db.set_value(
			"Donation Book Leaf",
			{
				"book": book,
				"book_serial_no": row.book_serial_no,
				"receipt_number": row.receipt_number,
			},
			{
				"status": "Used",
				"donor": row.donor,
				"donation_order": row.donation_order,
				"payment_mode": row.payment_mode,
				"manual_receipt_date": row.manual_receipt_date,
				"journal_entry": row.journal_entry,
				"accounting_status": row.accounting_status,
			},
			update_modified=False,
		)


def validate_donation_book_order_total_matches_return(doc):
	order_total = get_donation_book_order_total(doc.name)
	if flt(order_total, 2) != flt(doc.collected_amount, 2):
		frappe.throw(
			frappe._(
				"Donation Book {0} cannot be closed because Donation Orders total {1}, but returned amount is {2}."
			).format(
				doc.name,
				frappe.format_value(order_total, {"fieldtype": "Currency"}),
				frappe.format_value(doc.collected_amount, {"fieldtype": "Currency"}),
			)
		)


def get_coupon_type_from_item(item):
	if not item:
		return None

	item_values = frappe.db.get_value("Item", item, ["item_code", "item_name", "item_group"], as_dict=True)
	if not item_values:
		return None

	search_text = " ".join(
		filter(None, [item, item_values.item_code, item_values.item_name, item_values.item_group])
	).lower()
	for coupon_type in COUPON_COLORS:
		if coupon_type.lower() in search_text:
			return coupon_type

	return None


def get_coupon_value_from_item(item):
	if not item or not frappe.get_meta("Item").has_field("custom_donation_coupon_value"):
		return None

	return frappe.db.get_value("Item", item, "custom_donation_coupon_value")


def is_coupon_item(item):
	if not item:
		return False

	item_values = frappe.db.get_value(
		"Item",
		item,
		["disabled", "item_code", "item_name", "item_group"],
		as_dict=True,
	)
	if not item_values or cint(item_values.disabled):
		return False

	search_text = " ".join(
		filter(None, [item, item_values.item_code, item_values.item_name, item_values.item_group])
	).lower()
	return "coupon" in search_text or get_coupon_type_from_item(item) in COUPON_COLORS


def is_donation_book_item(item):
	if not item:
		return False

	item_values = frappe.db.get_value(
		"Item",
		item,
		["disabled", "item_code", "item_name", "item_group"],
		as_dict=True,
	)
	if not item_values or cint(item_values.disabled):
		return False

	search_text = " ".join(
		filter(None, [item, item_values.item_code, item_values.item_name, item_values.item_group])
	).lower()
	return "donation book" in search_text or "donationbook" in search_text


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_book_items(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})
	search = "%%%s%%" % txt
	book_type_condition = ""
	if filters.get("book_type") == BOOK_TYPE_COUPON:
		book_type_condition = """
			and (
				item.name like '%%Coupon%%'
				or item.item_code like '%%Coupon%%'
				or item.item_name like '%%Coupon%%'
				or item.item_group like '%%Coupon%%'
				or item.name like '%%Zakat%%'
				or item.item_code like '%%Zakat%%'
				or item.item_name like '%%Zakat%%'
				or item.item_group like '%%Zakat%%'
				or item.name like '%%Atiya%%'
				or item.item_code like '%%Atiya%%'
				or item.item_name like '%%Atiya%%'
				or item.item_group like '%%Atiya%%'
				or item.name like '%%Fitra%%'
				or item.item_code like '%%Fitra%%'
				or item.item_name like '%%Fitra%%'
				or item.item_group like '%%Fitra%%'
				or item.name like '%%Fidya%%'
				or item.item_code like '%%Fidya%%'
				or item.item_name like '%%Fidya%%'
				or item.item_group like '%%Fidya%%'
			)
		"""
	elif filters.get("book_type") == BOOK_TYPE_DONATION:
		book_type_condition = """
			and (
				item.name like '%%Donation Book%%'
				or item.item_code like '%%Donation Book%%'
				or item.item_name like '%%Donation Book%%'
				or item.item_group like '%%Donation Book%%'
				or item.name like '%%DonationBook%%'
				or item.item_code like '%%DonationBook%%'
				or item.item_name like '%%DonationBook%%'
				or item.item_group like '%%DonationBook%%'
			)
		"""

	return frappe.db.sql(
		"""
		select item.name, item.item_name, item.item_group
		from `tabItem` item
		where item.disabled = 0
			and item.is_stock_item = 1
			and item.has_serial_no = 1
			and (
				item.name like %(search)s
				or item.item_code like %(search)s
				or item.item_name like %(search)s
				or item.item_group like %(search)s
			)
			{book_type_condition}
		order by item.name
		limit %(start)s, %(page_len)s
		""".format(book_type_condition=book_type_condition),
		{
			"search": search,
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_book_serial_nos(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})
	if not filters.get("item") or not filters.get("warehouse"):
		return []

	search = "%%%s%%" % txt
	current_book = filters.get("book")
	selected_serials = filters.get("selected_serials") or []
	if isinstance(selected_serials, str):
		selected_serials = frappe.parse_json(selected_serials) or []
	selected_serials = tuple(serial for serial in selected_serials if serial)
	selected_serials_condition = ""
	if selected_serials:
		selected_serials_condition = "and serial.name not in %(selected_serials)s"

	return frappe.db.sql(
		"""
		select serial.name, serial.item_code, serial.warehouse
		from `tabSerial No` serial
		where serial.item_code = %(item)s
			and serial.warehouse = %(warehouse)s
			and serial.name like %(search)s
			{selected_serials_condition}
			and not exists (
				select book.name
				from `tabBook` book
				where book.book_serial_no = serial.name
					and book.docstatus != 2
					and (%(book)s is null or book.name != %(book)s)
			)
			and not exists (
				select detail.name
				from `tabBook Assignment Detail` detail
				inner join `tabBook` book
					on book.name = detail.parent
				where detail.book_serial_no = serial.name
					and book.docstatus != 2
					and (%(book)s is null or book.name != %(book)s)
			)
		order by serial.name
		limit %(start)s, %(page_len)s
		""".format(selected_serials_condition=selected_serials_condition),
		{
			"item": filters.get("item"),
			"warehouse": filters.get("warehouse"),
			"book": current_book,
			"selected_serials": selected_serials,
			"search": search,
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_mohasil_donation_books(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})
	if not filters.get("mohasil"):
		return []

	search = "%%%s%%" % txt
	return frappe.db.sql(
		"""
		select
			book.name,
			coalesce(nullif(book.book_serial_numbers, ''), serials.book_serial_numbers, book.name) as book_serial_numbers,
			book.status,
			book.warehouse,
			book.issued_to_employee
		from `tabBook` book
		left join (
			select parent, group_concat(book_serial_no order by idx separator ', ') as book_serial_numbers
			from `tabBook Assignment Detail`
			where ifnull(book_serial_no, '') != ''
			group by parent
		) serials
			on serials.parent = book.name
		where book.book_type = %(book_type)s
			and book.status = %(status)s
			and book.issued_to_employee = %(mohasil)s
			and (
				book.remaining_receipts > 0
				or exists (
					select detail.name
					from `tabBook Assignment Detail` detail
					where detail.parent = book.name
						and detail.parenttype = 'Book'
						and detail.parentfield = 'assigned_books'
						and detail.remaining_receipts > 0
				)
			)
			and (
				book.name like %(search)s
				or book.book_serial_numbers like %(search)s
				or serials.book_serial_numbers like %(search)s
				or book.item like %(search)s
				or book.warehouse like %(search)s
			)
		order by book.modified desc
		limit %(start)s, %(page_len)s
		""",
		{
			"book_type": BOOK_TYPE_DONATION,
			"status": "Returned",
			"mohasil": filters.get("mohasil"),
			"search": search,
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_mohasil_donation_book_serials(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})
	if not filters.get("mohasil"):
		return []

	search = "%%%s%%" % txt
	return frappe.db.sql(
		"""
		select
			detail.book_serial_no,
			book.name,
			book.status,
			detail.from_receipt_no,
			detail.to_receipt_no
		from `tabBook Assignment Detail` detail
		inner join `tabBook` book
			on book.name = detail.parent
		where book.book_type = %(book_type)s
			and book.status = %(status)s
			and book.issued_to_employee = %(mohasil)s
			and book.docstatus != 2
			and detail.parentfield = 'assigned_books'
			and ifnull(detail.book_serial_no, '') != ''
			and detail.remaining_receipts > 0
			and (
				detail.book_serial_no like %(search)s
				or book.name like %(search)s
				or detail.item like %(search)s
				or detail.warehouse like %(search)s
			)
		order by detail.book_serial_no
		limit %(start)s, %(page_len)s
		""",
		{
			"book_type": BOOK_TYPE_DONATION,
			"status": "Returned",
			"mohasil": filters.get("mohasil"),
			"search": search,
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


@frappe.whitelist()
def get_donation_book_for_serial(book_serial_no=None, mohasil=None):
	if not book_serial_no or not mohasil:
		return {}

	result = frappe.db.sql(
		"""
		select
			book.name,
			detail.from_receipt_no,
			detail.to_receipt_no,
			detail.remaining_receipts
		from `tabBook Assignment Detail` detail
		inner join `tabBook` book
			on book.name = detail.parent
		where detail.book_serial_no = %(book_serial_no)s
			and book.book_type = %(book_type)s
			and book.status = %(status)s
			and book.issued_to_employee = %(mohasil)s
			and book.docstatus != 2
			and detail.parentfield = 'assigned_books'
		limit 1
		""",
		{
			"book_serial_no": book_serial_no,
			"book_type": BOOK_TYPE_DONATION,
			"status": "Returned",
			"mohasil": mohasil,
		},
		as_dict=True,
	)
	return result[0] if result else {}


@frappe.whitelist()
def get_book_stock_qty(item=None, warehouse=None):
	if not item or not warehouse:
		return 0
	return flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "actual_qty") or 0)


@frappe.whitelist()
def get_coupon_type_for_item(item):
	coupon_type = get_coupon_type_from_item(item)
	if not coupon_type:
		frappe.throw(
			frappe._(
				"Could not identify Coupon Type from Item {0}. Item name, item code, or item group must contain Zakat, Atiya, Fitra, or Fidya."
			).format(item)
		)
	return coupon_type
