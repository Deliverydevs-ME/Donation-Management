# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_page_adjustment.book_page_adjustment import (
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
