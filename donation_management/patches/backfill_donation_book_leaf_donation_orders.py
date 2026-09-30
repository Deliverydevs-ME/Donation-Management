import frappe


def execute():
	if not frappe.db.table_exists("Donation Book Leaf") or not frappe.db.table_exists("Donation Order"):
		return

	if not frappe.get_meta("Donation Book Leaf").has_field("donation_order"):
		return

	from donation_management.donation_management.doctype.book_assignment.book_assignment import (
		sync_donation_book_leaves,
	)

	for book in frappe.get_all(
		"Book Assignment",
		filters={"book_type": ["in", ["Donation Book", "Mixed"]]},
		pluck="name",
	):
		sync_donation_book_leaves(book)
