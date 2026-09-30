import frappe


def execute():
	from donation_management.donation_management.doctype.book_assignment.book_assignment import (
		BOOK_TYPE_DONATION,
		update_donation_book_receipt_usage,
	)

	for book in frappe.get_all("Book Assignment", filters={"book_type": ["in", [BOOK_TYPE_DONATION, "Mixed"]]}, pluck="name"):
		update_donation_book_receipt_usage(book)
