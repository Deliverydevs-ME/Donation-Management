"""Create pending Coupon Book Leafs for already submitted assignments."""

import frappe


def execute():
	from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
		sync_coupon_book_leaves,
	)

	for book in frappe.get_all(
		"Book Assignment",
		filters={"docstatus": 1, "book_type": ["in", ["Coupon Book", "Mixed"]]},
		pluck="name",
		limit_page_length=0,
	):
		sync_coupon_book_leaves(book)
