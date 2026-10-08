# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from pathlib import Path

import frappe
from unittest.mock import Mock, patch
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	BookAssignment,
	cancel_book_issue_stock_entry,
	create_book_issue_stock_entry,
	format_receipt_number,
	get_book_return_details,
	get_book_item_details,
	get_book_items,
	get_coupon_book_total_pages,
	get_book_stock_qty,
	get_donation_book_used_receipts,
	get_receipt_range_count,
	has_unsubmitted_donation_book_leaves,
	reopen_donation_book,
	receipt_number_in_range,
	receipt_series_prefix,
	restore_unused_book_stock,
	return_book,
)


class TestBookAssignment(FrappeTestCase):
	def test_book_assignment_cancels_its_submitted_coupon_entries(self):
		assignment = BookAssignment({"doctype": "Book Assignment", "name": "BK-TEST"})
		coupon = frappe._dict(flags=frappe._dict(), cancel=Mock())

		with patch.object(frappe, "get_all", return_value=["COP-TEST"]), patch.object(
			frappe, "get_doc", return_value=coupon
		):
			assignment.cancel_linked_coupon_entries()

		self.assertTrue(coupon.flags.ignore_permissions)
		coupon.cancel.assert_called_once_with()

	def test_book_assignment_cancellation_sets_cancelled_status(self):
		assignment = BookAssignment(
			{"doctype": "Book Assignment", "name": "BK-TEST", "status": "Issued"}
		)
		assignment.cancel_linked_coupon_entries = Mock()
		assignment.db_set = Mock()

		with patch(
			"donation_management.donation_management.doctype.donation_book_leaf.donation_book_leaf.cancel_leaves_for_book_assignment"
		), patch(
			"donation_management.donation_management.doctype.coupon_book_leaf.coupon_book_leaf.cancel_leaves_for_book_assignment"
		):
			assignment.on_cancel()

		self.assertEqual(assignment.status, "Cancelled")
		assignment.db_set.assert_called_once_with("status", "Cancelled", update_modified=False)

	def test_assigned_book_stock_is_confirmed_after_item_or_warehouse_selection(self):
		script = Path(__file__).with_name("book_assignment.js").read_text()

		self.assertIn("show_assigned_book_stock(cdt, cdn)", script)
		self.assertIn("show_assigned_book_stock_alert", script)
		self.assertIn('message: __("Available stock: {0}", [stock])', script)
		self.assertIn('indicator: "green"', script)
		self.assertNotIn("available_stock", script)
		self.assertNotIn("assigned_book_stock_refresh_interval", script)

	def test_book_assignment_form_uses_server_side_cancellation_cascade(self):
		script = Path(__file__).with_name("book_assignment.js").read_text()

		self.assertIn('"Coupon Entry"', script)
		self.assertIn('"Coupon Book Leaf"', script)
		self.assertIn('"Donation Book Leaf"', script)
		self.assertIn('"Stock Entry"', script)

	def test_issuing_book_creates_stock_ledger_entry(self):
		doc = frappe._dict(
			{
				"name": "BK-TEST",
				"company": "JTQ",
				"start_date": "2026-10-08",
				"issued_to_employee": "EMP-TEST",
				"stock_entry": None,
				"assigned_books": [
					frappe._dict(
						{
							"item": "Sadqa Coupon Book",
							"warehouse": "Stores - JTQ",
							"book_serial_no": "SCB-0001",
						}
					)
				],
				"item": None,
				"warehouse": None,
				"book_serial_no": None,
			}
		)
		stock_entry = Mock()
		stock_entry.name = "MAT-STE-TEST"
		stock_entry.items = []

		with patch.object(frappe.db, "get_value", return_value=None), patch.object(
			frappe.db, "set_value"
		) as set_value, patch(
			"erpnext.stock.doctype.stock_entry.stock_entry_utils.make_stock_entry",
			return_value=stock_entry,
		) as make_stock_entry:
			self.assertEqual(create_book_issue_stock_entry(doc), "MAT-STE-TEST")

		make_stock_entry.assert_called_once_with(
			item_code="Sadqa Coupon Book",
			qty=1,
			company="JTQ",
			from_warehouse="Stores - JTQ",
			serial_no=["SCB-0001"],
			posting_date="2026-10-08",
			purpose="Material Issue",
			do_not_save=True,
		)
		stock_entry.insert.assert_called_once_with(ignore_permissions=True)
		stock_entry.submit.assert_called_once_with()
		set_value.assert_called_once_with(
			"Book Assignment", "BK-TEST", "stock_entry", "MAT-STE-TEST", update_modified=False
		)

	def test_return_with_unused_pages_reverses_issue_stock_entry(self):
		doc = frappe._dict(is_exhausted=lambda: False)
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.cancel_book_issue_stock_entry"
		) as cancel_stock_entry:
			restore_unused_book_stock(doc)

		cancel_stock_entry.assert_called_once_with(doc)

	def test_return_with_no_remaining_pages_keeps_issue_stock_entry(self):
		doc = frappe._dict(is_exhausted=lambda: True)
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.cancel_book_issue_stock_entry"
		) as cancel_stock_entry:
			restore_unused_book_stock(doc)

		cancel_stock_entry.assert_not_called()

	def test_return_can_cancel_parent_owned_stock_entry(self):
		doc = frappe._dict(stock_entry="MAT-STE-TEST")
		stock_entry = frappe._dict(flags=frappe._dict())
		stock_entry.cancel = Mock()

		with patch.object(frappe.db, "get_value", return_value=1), patch.object(
			frappe, "get_doc", return_value=stock_entry
		):
			cancel_book_issue_stock_entry(doc)

		self.assertTrue(stock_entry.flags.ignore_permissions)
		self.assertTrue(stock_entry.flags.ignore_links)
		stock_entry.cancel.assert_called_once_with()

	def test_submittable_doctypes_use_business_status_indicators_in_list_view(self):
		doctype_root = Path(__file__).resolve().parents[1]
		doctypes = (
			"Book Assignment",
			"Book Page Adjustment",
			"Coupon Book Leaf",
			"Coupon Entry",
			"Donation Book Collection",
			"Donation Book Leaf",
			"Donation Box",
			"Donation Cash Handover",
			"Donation Closing",
			"Donation Instrument Event",
			"Donation Location Assignment",
			"Donation Order",
		)

		for doctype in doctypes:
			folder = frappe.scrub(doctype)
			script = doctype_root / folder / f"{folder}_list.js"
			self.assertTrue(script.exists(), f"{doctype} needs a list-view status indicator")
			self.assertIn("get_indicator(doc)", script.read_text())

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
			"donation_management.donation_management.doctype.book_assignment.book_assignment.create_book_issue_stock_entry"
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
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_book_total_pages",
			return_value=10,
		):
			details = get_book_return_details("BA-00001")

		self.assertEqual(details["used_pages"], 3)
		self.assertEqual(details["coupon_value"], 100)
		self.assertEqual(details["total_amount"], 300)
		self.assertEqual(details["total_pages"], 10)

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
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_book_total_pages",
			return_value=2,
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
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_book_total_pages",
			return_value=3,
		):
			details = get_book_return_details("BA-00003")

		self.assertEqual(details["coupon_value"], 10)
		self.assertEqual(details["used_pages"], 3)
		self.assertEqual(details["total_amount"], 120)

	def test_coupon_total_pages_use_assigned_coupon_book_rows(self):
		rows = [frappe._dict(total_pages=4), frappe._dict(total_pages=6)]
		with patch.object(frappe, "get_all", return_value=rows), patch.object(frappe.db, "get_value") as get_value:
			self.assertEqual(get_coupon_book_total_pages("BA-00003"), 10)

		get_value.assert_not_called()

	def test_coupon_total_pages_fall_back_to_legacy_parent_field(self):
		with patch.object(frappe, "get_all", return_value=[]), patch.object(frappe.db, "get_value", return_value=8):
			self.assertEqual(get_coupon_book_total_pages("BA-00003"), 8)

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
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_book_total_pages",
			return_value=10,
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
		self.assertEqual(doc.remaining_pages, 7)

	def test_return_book_allows_an_empty_cash_denomination_breakdown(self):
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
			set=lambda fieldname, value: setattr(doc, fieldname, value),
			append=lambda fieldname, value: None,
			save=lambda: None,
		)
		doc.as_dict = lambda: doc

		with patch.object(frappe, "get_doc", return_value=doc), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_for_book",
			return_value=100,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_book_total_pages",
			return_value=10,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_used_pages",
			return_value=3,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			return_value=300,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.generate_return_coupons"
		), patch.object(frappe, "parse_json", return_value=[]), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.today",
			return_value="2026-10-05",
		):
			return_book("BA-00003", collected_amount=300, used_pages=3, denominations=[])

		self.assertEqual(doc.collected_amount, 300)

	def test_return_book_uses_assigned_coupon_total_when_parent_total_is_zero(self):
		doc = frappe._dict(
			status="Issued",
			total_pages=0,
			coupon_value=0,
			is_coupon_book=lambda: True,
			name="BA-00004",
			mode_of_payment=None,
			debit_account=None,
			credit_account=None,
			flags=frappe._dict(),
		)
		doc.set = lambda fieldname, value: setattr(doc, fieldname, value)
		doc.save = lambda: None
		doc.as_dict = lambda: doc

		with patch.object(frappe, "get_doc", return_value=doc), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_value_for_book",
			return_value=100,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_coupon_book_total_pages",
			return_value=5,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_used_pages",
			return_value=3,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			return_value=300,
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.generate_return_coupons"
		), patch.object(frappe, "parse_json", return_value=[]), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.today",
			return_value="2026-10-06",
		):
			return_book("BA-00004", collected_amount=300, used_pages=3, denominations=[], denomination_total=300)

		self.assertEqual(doc.status, "Returned")
		self.assertEqual(doc.remaining_pages, 2)

	def test_available_stock_uses_book_assignment_lifecycle(self):
		with patch.object(frappe.db, "sql", return_value=[(12,)]) as sql:
			self.assertEqual(get_book_stock_qty("Donation Book", "Stores - J"), 12)

		query, filters = sql.call_args.args
		self.assertIn("book.status in ('Issued', 'Closed')", query)
		self.assertIn("book.status = 'Returned'", query)
		self.assertIn("detail.remaining_pages", query)
		self.assertIn("detail.remaining_receipts", query)
		self.assertEqual(filters, {"item": "Donation Book", "warehouse": "Stores - J"})

	def test_available_stock_is_zero_without_item_or_warehouse(self):
		with patch.object(frappe.db, "sql") as sql:
			self.assertEqual(get_book_stock_qty("", "Stores - J"), 0)
			self.assertEqual(get_book_stock_qty("Donation Book", ""), 0)

		sql.assert_not_called()

	def test_draft_donation_orders_do_not_consume_book_receipts(self):
		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			self.assertEqual(get_donation_book_used_receipts("BK-TEST"), 0)

		query = sql.call_args.args[0]
		self.assertIn("parent.docstatus = 1", query)
