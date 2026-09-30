import frappe

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	refresh_donation_book_leaf_usage,
)


def execute():
	if not frappe.db.table_exists("Donation Book Leaf"):
		return

	for book in frappe.get_all("Book Assignment", pluck="name"):
		refresh_donation_book_leaf_usage(book)
