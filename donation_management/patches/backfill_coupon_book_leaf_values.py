"""Backfill Coupon Value on existing Coupon Book Leafs."""

import frappe


def execute():
	if not frappe.db.table_exists("Coupon Book Leaf"):
		return

	for leaf in frappe.get_all(
		"Coupon Book Leaf",
		fields=["name", "book", "book_serial_no", "coupon_value"],
		limit_page_length=0,
	):
		if leaf.coupon_value:
			continue
		if not leaf.book:
			continue

		filters = {
			"parent": leaf.book,
			"parenttype": "Book Assignment",
			"parentfield": "assigned_books",
			"book_type": "Coupon Book",
		}
		if leaf.book_serial_no:
			filters["book_serial_no"] = leaf.book_serial_no

		coupon_value = frappe.db.get_value("Book Assignment Detail", filters, "coupon_value")
		if not coupon_value:
			coupon_value = frappe.db.get_value("Book Assignment", leaf.book, "coupon_value")
		if coupon_value:
			frappe.db.set_value(
				"Coupon Book Leaf",
				leaf.name,
				"coupon_value",
				coupon_value,
				update_modified=False,
			)
