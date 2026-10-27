# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_page_adjustment.book_page_adjustment import (
	BookPageAdjustment,
	clear_cancelled_stock_entry_link,
	get_coupon_book_total_pages,
)


class TestBookPageAdjustment(FrappeTestCase):
	def test_coupon_book_rows_are_used_for_page_total(self):
		book_details = frappe._dict(book_type="Mixed", total_pages=0, book_serial_no=None)
		with patch.object(
			frappe,
			"get_all",
			return_value=[frappe._dict(book_serial_no="COUPON-01", total_pages=25)],
		):
			self.assertEqual(get_coupon_book_total_pages("BA-TEST", "COUPON-01", book_details), 25)

	def test_mixed_assignment_rejects_missing_coupon_serial(self):
		book_details = frappe._dict(book_type="Mixed", total_pages=0, book_serial_no=None)
		with patch.object(frappe, "get_all", return_value=[]):
			with self.assertRaisesRegex(frappe.ValidationError, "Coupon Book Serial No is required"):
				get_coupon_book_total_pages("BA-TEST", None, book_details)

	def test_affected_page_grid_returns_distinct_page_numbers(self):
		adjustment = BookPageAdjustment(
			{
				"doctype": "Book Page Adjustment",
				"affected_page_details": [
					{"page_no": 9},
					{"page_no": 10},
					{"page_no": 11},
				]
			}
		)

		self.assertEqual(adjustment.get_affected_page_numbers(), [9, 10, 11])

	def test_affected_page_grid_rejects_duplicate_page_numbers(self):
		adjustment = BookPageAdjustment(
			{
				"doctype": "Book Page Adjustment",
				"affected_page_details": [
					{"page_no": 9},
					{"page_no": 9},
				]
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "more than once"):
			adjustment.get_affected_page_numbers()

	def test_cancelled_stock_entry_link_is_cleared_before_adjustment(self):
		book = frappe._dict(stock_entry="MAT-STE-CANCELLED")
		with patch.object(frappe.db, "get_value", return_value=2):
			clear_cancelled_stock_entry_link(book)

		self.assertIsNone(book.stock_entry)

	def test_submitted_stock_entry_link_is_preserved_before_adjustment(self):
		book = frappe._dict(stock_entry="MAT-STE-SUBMITTED")
		with patch.object(frappe.db, "get_value", return_value=1):
			clear_cancelled_stock_entry_link(book)

		self.assertEqual(book.stock_entry, "MAT-STE-SUBMITTED")
