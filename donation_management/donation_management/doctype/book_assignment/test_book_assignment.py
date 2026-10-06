# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	BookAssignment,
	format_receipt_number,
	get_book_return_details,
	get_book_item_details,
	get_book_items,
	get_book_stock_qty,
	get_donation_book_used_receipts,
	get_receipt_range_count,
	has_unsubmitted_donation_book_leaves,
	reopen_donation_book,
	receipt_number_in_range,
	receipt_series_prefix,
	return_book,
	sync_assigned_book_stock,
)


class TestBookAssignment(FrappeTestCase):
	def test_donation_book_is_reopenable_while_a_leaf_is_unsubmitted(self):
		with patch.object(frappe.db, "exists", return_value="DBL-00001") as exists:
			self.assertTrue(has_unsubmitted_donation_book_leaves("BK-00001"))

		exists.assert_called_once_with(
			"Donation Book Leaf",
			{"book": "BK-00001", "status": ["not in", ("Used", "Cancelled")]},
		)

	def test_reopening_donation_book_sets_issued_status(self):
		doc = frappe._dict(
			name="BK-00001",
			status="Returned",
			return_date="2026-10-05",
			reopen_count=0,
			flags=frappe._dict(),
		)
		doc.reload = lambda: None
		doc.save = lambda: None
		doc.as_dict = lambda: doc

		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.update_donation_book_receipt_usage"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.has_unsubmitted_donation_book_leaves",
			return_value=True,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.sync_donation_book_leaves"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.now_datetime",
			return_value="2026-10-06 12:00:00",
		):
			reopen_donation_book(doc, "Continue collecting receipts")

		self.assertEqual(doc.status, "Issued")
		self.assertIsNone(doc.return_date)
		self.assertEqual(doc.reopen_count, 1)

	def test_donation_book_cannot_reopen_after_all_leaves_are_submitted(self):
		doc = frappe._dict(name="BK-00001", status="Returned")
		doc.reload = lambda: None
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.update_donation_book_receipt_usage"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.has_unsubmitted_donation_book_leaves",
			return_value=False,
		), self.assertRaisesRegex(frappe.ValidationError, "all Donation Book Leaves are submitted"):
			reopen_donation_book(doc, "Continue collecting receipts")

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

	def test_saved_book_type_item_queries_remain_type_specific(self):
		for book_type, required_text, excluded_text in (
			("Coupon Book", "Coupon", "Donation Book"),
			("Donation Book", "Donation Book", "Coupon"),
		):
			with self.subTest(book_type=book_type), patch.object(frappe.db, "exists", return_value=True), patch.object(
				frappe.db, "sql", return_value=[]
			) as sql:
				get_book_items("Item", "", "name", 0, 20, {"book_type": book_type})

			query = next(call.args[0] for call in sql.call_args_list if "tabItem" in call.args[0])
			self.assertIn(required_text, query)
			self.assertNotIn(excluded_text, query)

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

	def test_return_details_use_submitted_pages_and_coupon_value(self):
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_for_book",
			return_value=100,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_used_pages",
			return_value=3,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			return_value=300,
		):
			details = get_book_return_details("BA-00001")

		self.assertEqual(details["used_pages"], 3)
		self.assertEqual(details["coupon_value"], 100)
		self.assertEqual(details["total_amount"], 300)

	def test_return_details_fall_back_to_coupon_row_value(self):
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_for_book",
			return_value=50,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_used_pages",
			return_value=2,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			return_value=100,
		):
			details = get_book_return_details("BA-00002")

		self.assertEqual(details["coupon_value"], 50)
		self.assertEqual(details["total_amount"], 100)

	def test_return_details_use_submitted_entry_amounts_not_one_coupon_value(self):
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_for_book",
			return_value=10,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_used_pages",
			return_value=3,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			return_value=120,
		):
			details = get_book_return_details("BA-00003")

		self.assertEqual(details["coupon_value"], 10)
		self.assertEqual(details["used_pages"], 3)
		self.assertEqual(details["total_amount"], 120)

	def test_return_book_uses_coupon_row_value_for_calculation(self):
		doc = frappe._dict(
			status="Issued",
			total_pages=10,
			coupon_value=0,
			is_coupon_book=lambda: True,
			name="BA-00003",
			mode_of_payment=None,
			debit_account=None,
			credit_account=None,
			flags=frappe._dict(),
		)
		doc.set = lambda fieldname, value: setattr(doc, fieldname, value)
		doc.save = lambda: None
		doc.as_dict = lambda: doc

		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_for_book",
			return_value=100,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_used_pages",
			return_value=3,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			return_value=300,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.generate_return_coupons"
			), patch.object(frappe, "get_doc", return_value=doc), patch.object(
				frappe, "parse_json", return_value=[]
			), patch(
				"donation_management.donation_management.doctype.book_assignment.book_assignment.today",
				return_value="2026-10-05",
			):
			return_book("BA-00003", collected_amount=300, used_pages=3, denominations=[], denomination_total=300)

		self.assertEqual(doc.coupon_value, 100)
		self.assertEqual(doc.collected_amount, 300)

	def test_submitted_assignment_persists_current_child_stock(self):
		rows = [
			frappe._dict(name="BAD-ROW-1", item="Donation Book", warehouse="Stores - J"),
		]
		with patch.object(frappe.db, "exists", return_value=True), patch.object(
			frappe, "get_all", return_value=rows
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_stock_qty",
			return_value=7,
		), patch.object(frappe.db, "set_value") as set_value:
			sync_assigned_book_stock("BA-00001")

		set_value.assert_called_once_with(
			"Book Assignment Detail",
			"BAD-ROW-1",
			"available_stock",
			7,
			update_modified=False,
		)

	def test_available_stock_reads_current_bin_quantity(self):
		with patch.object(frappe.db, "get_value", return_value=12.5) as get_value:
			self.assertEqual(get_book_stock_qty("Donation Book", "Stores - J"), 12.5)

		get_value.assert_called_once_with(
			"Bin",
			{"item_code": "Donation Book", "warehouse": "Stores - J"},
			"actual_qty",
		)

	def test_available_stock_is_zero_without_item_or_warehouse(self):
		with patch.object(frappe.db, "get_value") as get_value:
			self.assertEqual(get_book_stock_qty("", "Stores - J"), 0)
			self.assertEqual(get_book_stock_qty("Donation Book", ""), 0)

		get_value.assert_not_called()

	def test_draft_donation_orders_do_not_consume_book_receipts(self):
		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			self.assertEqual(get_donation_book_used_receipts("BK-TEST"), 0)

		query = sql.call_args.args[0]
		self.assertIn("parent.docstatus = 1", query)
