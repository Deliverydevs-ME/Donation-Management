# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	get_coupon_type_from_item,
)
from donation_management.donation_management.doctype.coupon.coupon import Coupon, COUPON_SERIES


class TestCoupon(FrappeTestCase):
	def test_coupon_is_submittable_and_uses_short_series(self):
		self.assertTrue(frappe.get_meta("Coupon").is_submittable)
		self.assertEqual(COUPON_SERIES, "COP-.####")

	def test_zero_and_negative_pages_are_rejected(self):
		for pages in (0, -1):
			coupon = Coupon({"doctype": "Coupon", "number_of_pages": pages})
			with self.assertRaisesRegex(frappe.ValidationError, "greater than zero"):
				coupon.validate_number_of_pages()

	def test_coupon_type_can_be_detected_from_selected_item_value(self):
		with patch.object(frappe.db, "get_value", return_value=None):
			self.assertEqual(get_coupon_type_from_item("Sadqa Coupon Book"), "Sadqa")
