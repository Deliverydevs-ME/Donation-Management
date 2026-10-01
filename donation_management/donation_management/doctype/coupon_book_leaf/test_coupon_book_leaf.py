from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
	get_coupon_book_leaf_ranges,
)


class TestCouponBookLeaf(FrappeTestCase):
	def test_coupon_book_leaf_is_submittable(self):
		meta = frappe.get_meta("Coupon Book Leaf")
		self.assertTrue(meta.is_submittable)
		self.assertEqual(meta.get_field("status").options, "Pending\nUsed\nDiscarded")

	def test_coupon_book_ranges_only_include_coupon_rows(self):
		book = frappe._dict(
			book_type="Mixed",
			assigned_books=[
				frappe._dict(
					book_type="Donation Book",
					book_serial_no="DB-01",
					from_receipt_no="DB-001",
					to_receipt_no="DB-002",
				),
				frappe._dict(
					book_type="Coupon Book",
					book_serial_no="CB-01",
					receipt_format="CP-###",
					from_receipt_no="CP-001",
					to_receipt_no="CP-003",
				),
			],
		)
		ranges = get_coupon_book_leaf_ranges(book)
		self.assertEqual(len(ranges), 1)
		self.assertEqual(ranges[0]["book_serial_no"], "CB-01")
