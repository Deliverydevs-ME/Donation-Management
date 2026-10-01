# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	BookAssignment,
	format_receipt_number,
	get_book_item_details,
	get_book_items,
	get_receipt_range_count,
	receipt_number_in_range,
	receipt_series_prefix,
)


class TestBookAssignment(FrappeTestCase):
	def test_receipt_ranges_are_inclusive(self):
		self.assertEqual(get_receipt_range_count("100", "100"), 1)
		self.assertEqual(get_receipt_range_count("100", "105"), 6)
		self.assertTrue(receipt_number_in_range("105", "100", "105"))
		self.assertFalse(receipt_number_in_range("106", "100", "105"))
		self.assertEqual(get_receipt_range_count("REC-.0001", "REC-.0003"), 3)
		self.assertTrue(receipt_number_in_range("REC-0003", "REC-.0001", "REC-.0003"))
		self.assertEqual(format_receipt_number("REC-.####", 7), "REC-0007")
		self.assertEqual(format_receipt_number("DON-###-A", 7), "DON-007-A")
		self.assertEqual(receipt_series_prefix("REC-.0001"), "REC-")
		self.assertTrue(receipt_number_in_range("REC-0003", "REC-0001", "REC-0100"))
		self.assertFalse(receipt_number_in_range("INV-0003", "REC-0001", "REC-0100"))

	def test_mixed_assignment_is_exhausted_only_when_all_rows_are_used(self):
		book = BookAssignment(
			{
				"doctype": "Book Assignment",
				"book_type": "Mixed",
				"assigned_books": [
					frappe._dict(book_type="Coupon Book", remaining_pages=0),
					frappe._dict(book_type="Donation Book", remaining_receipts=1),
				],
			}
		)
		self.assertFalse(book.is_exhausted())
		book.assigned_books[1].remaining_receipts = 0
		self.assertTrue(book.is_exhausted())

	def test_mixed_item_query_includes_coupon_and_donation_items(self):
		with patch.object(frappe.db, "exists", return_value=True), patch.object(
			frappe.db, "sql", return_value=[]
		) as sql:
			get_book_items("Item", "", "name", 0, 20, {"book_type": "Mixed"})

		query = next(call.args[0] for call in sql.call_args_list if "tabItem" in call.args[0])
		self.assertIn("Coupon", query)
		self.assertIn("Donation Book", query)

	def test_coupon_item_details_return_type_and_configured_value(self):
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.is_coupon_item",
			return_value=True,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_type_from_item",
			return_value="Sadqa",
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_from_item",
			return_value=100,
		):
			details = get_book_item_details("Sadqa Coupon Book")

		self.assertEqual(details["book_type"], "Coupon Book")
		self.assertEqual(details["coupon_type"], "Sadqa")
		self.assertEqual(details["coupon_value"], 100)
