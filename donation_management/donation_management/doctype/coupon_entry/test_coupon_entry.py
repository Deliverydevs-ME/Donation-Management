# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	get_coupon_type_from_item,
)
from donation_management.donation_management.doctype.coupon_entry.coupon_entry import (
	COUPON_SERIES,
	Coupon,
	_get_coupon_book_details,
	sync_coupon_entry_leaf_connections,
)


class TestCoupon(FrappeTestCase):
	def test_coupon_is_submittable_and_uses_short_series(self):
		self.assertTrue(frappe.get_meta("Coupon Entry").is_submittable)
		self.assertEqual(COUPON_SERIES, "COP-.####")
		self.assertTrue(all(permission.get("submit") for permission in frappe.get_meta("Coupon Entry").permissions))
		self.assertTrue(all(permission.get("cancel") for permission in frappe.get_meta("Coupon Entry").permissions))

	def test_connections_use_existing_target_fields(self):
		dashboard = frappe.get_meta("Coupon Entry").get_dashboard_data()
		self.assertEqual(dashboard.internal_links["Book Assignment"], "book")
		self.assertEqual(dashboard.internal_links["Journal Entry"], "journal_entry")
		self.assertEqual(dashboard.non_standard_fieldnames["Coupon Book Leaf"], "coupon_entry")
		self.assertTrue(
			any("Coupon Book Leaf" in transaction["items"] for transaction in dashboard.transactions)
		)
		self.assertTrue(frappe.get_meta("Coupon Entry").has_field("book"))
		self.assertTrue(frappe.get_meta("Coupon Entry").has_field("journal_entry"))
		self.assertTrue(frappe.get_meta("Coupon Book Leaf").has_field("coupon_entry"))

	def test_zero_and_negative_pages_are_rejected(self):
		for pages in (0, -1):
			coupon = Coupon({"doctype": "Coupon Entry", "number_of_pages": pages})
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

	def test_parent_assignment_lookup_does_not_require_child_receipt_columns(self):
		parent = frappe._dict(book_type="Mixed", status="Issued", remaining_pages=0)
		with patch.object(frappe.db, "get_value", return_value=parent) as get_value, patch.object(
			frappe.db, "exists", return_value=True
		) as exists:
			book = _get_coupon_book_details("BK-00000001", allow_missing_serial=True)

		fields = get_value.call_args.args[2]
		self.assertNotIn("receipt_format", fields)
		self.assertNotIn("from_receipt_no", fields)
		self.assertNotIn("to_receipt_no", fields)
		self.assertEqual(book.requires_book_serial_no, 1)
		exists.assert_called_once()

	def test_leaf_allocation_synchronizes_the_book_receipt_range_first(self):
		leaf_source = (
			Path(__file__).resolve().parent.parent / "coupon_book_leaf" / "coupon_book_leaf.py"
		).read_text()
		allocation_start = leaf_source.index("def allocate_coupon_entry_leaves")
		allocation_source = leaf_source[allocation_start : leaf_source.index("def get_coupon_entry_range", allocation_start)]

		self.assertIn("sync_coupon_book_leaves(coupon_entry.book)", allocation_source)

	def test_submitted_coupon_repairs_missing_leaf_connections(self):
		entry = frappe._dict(name="COP-TEST", docstatus=1, book="BK-TEST", number_of_pages=2)
		with patch.object(frappe.db, "exists", return_value=True), patch.object(
			frappe, "get_doc", return_value=entry
		), patch.object(frappe.db, "count", side_effect=[0, 2]), patch(
			"donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf.allocate_coupon_entry_leaves"
		) as allocate:
			self.assertEqual(sync_coupon_entry_leaf_connections("COP-TEST"), 2)

		allocate.assert_called_once_with(entry)

	def test_coupon_form_refreshes_connections_after_leaf_repair(self):
		script = Path(__file__).with_name("coupon_entry.js").read_text()

		self.assertIn("sync_coupon_entry_leaf_connections", script)
		self.assertIn("frm.dashboard.refresh()", script)
