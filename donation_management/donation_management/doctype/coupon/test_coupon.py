# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	get_coupon_type_from_item,
)
from donation_management.donation_management.doctype.coupon.coupon import (
	COUPON_SERIES,
	Coupon,
	_get_coupon_book_details,
)


class TestCoupon(FrappeTestCase):
	def test_coupon_is_submittable_and_uses_short_series(self):
		self.assertTrue(frappe.get_meta("Coupon").is_submittable)
		self.assertEqual(COUPON_SERIES, "COP-.####")
		self.assertTrue(all(permission.get("submit") for permission in frappe.get_meta("Coupon").permissions))

	def test_zero_and_negative_pages_are_rejected(self):
		for pages in (0, -1):
			coupon = Coupon({"doctype": "Coupon", "number_of_pages": pages})
			with self.assertRaisesRegex(frappe.ValidationError, "greater than zero"):
				coupon.validate_number_of_pages()

	def test_coupon_type_can_be_detected_from_selected_item_value(self):
		with patch.object(frappe.db, "get_value", return_value=None):
			self.assertEqual(get_coupon_type_from_item("Sadqa Coupon Book"), "Sadqa")

	def test_coupon_assignment_uses_available_child_book_row(self):
		parent = frappe._dict(
			book_type="Coupon Book",
			status="Issued",
			remaining_pages=0,
			volunteer_name=None,
			issued_to_employee="HR-EMP-01094",
		)
		child = frappe._dict(
			book_type="Coupon Book",
			coupon_type="Sadqa",
			coupon_value="100",
			coupon_color="Blue",
			warehouse="Stores - J",
			total_pages=999,
			remaining_pages=999,
		)

		def get_value(doctype, name, fields, **kwargs):
			if doctype == "Book Assignment":
				return parent
			return child

		with patch.object(frappe.db, "get_value", side_effect=get_value), patch.object(
			frappe.db, "exists", return_value=True
		):
			book = _get_coupon_book_details("BK-00000001", "SC-01")

		self.assertEqual(book.remaining_pages, 999)
		self.assertEqual(book.coupon_type, "Sadqa")
		self.assertEqual(book.volunteer_name, "HR-EMP-01094")
