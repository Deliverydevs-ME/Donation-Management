"""Allocate generated Coupon Book Leafs for already submitted Coupon Entries."""

import frappe


def execute():
	from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
		allocate_coupon_entry_leaves,
	)

	for entry_name in frappe.get_all("Coupon Entry", filters={"docstatus": 1}, pluck="name", limit_page_length=0):
		allocate_coupon_entry_leaves(frappe.get_doc("Coupon Entry", entry_name))
