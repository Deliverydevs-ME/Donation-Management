import json
from pathlib import Path
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
	CouponBookLeaf,
	get_coupon_book_leaf_ranges,
	upsert_coupon_book_leaf,
)


class TestCouponBookLeaf(FrappeTestCase):
	def test_coupon_book_leaf_is_submittable(self):
		meta = frappe.get_meta("Coupon Book Leaf")
		self.assertTrue(meta.is_submittable)
		self.assertEqual(meta.get_field("status").options, "Pending\nUsed\nDiscarded")

	def test_coupon_book_leaf_cannot_be_created_manually(self):
		metadata = json.loads(Path(__file__).with_name("coupon_book_leaf.json").read_text())
		self.assertFalse(any(permission.get("create") for permission in metadata["permissions"]))
		self.assertIn("clear_primary_action", Path(__file__).with_name("coupon_book_leaf_list.js").read_text())

		leaf = CouponBookLeaf({"doctype": "Coupon Book Leaf"})
		with self.assertRaisesRegex(frappe.ValidationError, "generated automatically"):
			leaf.before_insert()

		leaf.flags.from_book_assignment_generation = True
		leaf.before_insert()

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
					coupon_value=100,
				),
			],
		)
		ranges = get_coupon_book_leaf_ranges(book)
		self.assertEqual(len(ranges), 1)
		self.assertEqual(ranges[0]["book_serial_no"], "CB-01")
		self.assertEqual(ranges[0]["coupon_value"], 100)

	def test_generated_leaf_stores_coupon_value(self):
		leaf = Mock()
		book = frappe._dict(name="BA-00001")
		with patch.object(frappe.db, "exists", return_value=None), patch.object(
			frappe, "get_doc", return_value=leaf
		) as get_doc:
			upsert_coupon_book_leaf(book, "CB-01", "CP-001", 100)

		get_doc.assert_called_once_with(
			{
				"doctype": "Coupon Book Leaf",
				"book": "BA-00001",
				"book_serial_no": "CB-01",
				"receipt_number": "CP-001",
				"coupon_value": 100,
				"status": "Pending",
			}
		)
		self.assertTrue(leaf.flags.from_book_assignment_generation)
		leaf.insert.assert_called_once_with(ignore_permissions=True)

	def test_coupon_entry_cancellation_returns_receipt_numbers(self):
		from donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf import (
			cancel_leaves_for_coupon_entry,
		)

		leaf = Mock(docstatus=0, receipt_number="CP-001")
		with patch.object(
			frappe,
			"get_all",
			return_value=[frappe._dict(name="CBL-00001", receipt_number="CP-001")],
		), patch.object(frappe, "get_doc", return_value=leaf):
			cancelled_receipts = cancel_leaves_for_coupon_entry("COP-0001")

		self.assertEqual(cancelled_receipts, ["CP-001"])
		leaf.db_set.assert_called_once_with(
			{"status": "Discarded", "accounting_status": "Cancelled"},
			update_modified=False,
		)
