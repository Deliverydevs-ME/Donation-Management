# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from pathlib import Path

import frappe
from unittest.mock import Mock, patch
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	BookAssignment,
	account_matches_coupon_type,
	cancel_book_issue_stock_entry,
	clear_cancelled_book_stock_entry_link,
	create_book_assignment_issue_log,
	create_book_issue_stock_entry,
	format_receipt_number,
	get_book_return_details,
	get_book_item_details,
	get_book_items,
	get_coupon_book_total_pages,
	get_book_stock_qty,
	get_donation_book_reopen_eligibility,
	get_donation_book_used_receipts,
	get_receipt_range_count,
	has_unsubmitted_donation_book_leaves,
	reopen_donation_book,
	receipt_number_in_range,
	receipt_series_prefix,
	restore_unused_book_stock,
	return_book,
	validate_coupon_book_return_collections,
	validate_return_collection_denominations,
	validate_receipt_number_matches_format,
)


class TestBookAssignment(FrappeTestCase):
	def test_defaults_do_not_require_a_company_field(self):
		assignment = BookAssignment(
			{
				"doctype": "Book Assignment",
				"book_type": "Mixed",
				"status": "Draft",
			}
		)

		assignment.set_defaults()

		self.assertEqual(assignment.book_type, "Mixed")

	def test_coupon_income_account_must_match_the_exact_coupon_type(self):
		with patch.object(
			frappe.db,
			"get_value",
			return_value=frappe._dict(name="Sadqa Income - JTQ", account_name="Sadqa Income"),
		):
			self.assertTrue(account_matches_coupon_type("Sadqa Income - JTQ", "Sadqa"))
			self.assertFalse(account_matches_coupon_type("Sadqa Income - JTQ", "Zakat"))

	def test_coupon_income_account_validation_does_not_require_parent_receipt_fields(self):
		assignment = BookAssignment(
			{
				"doctype": "Book Assignment",
				"book_type": "Coupon Book",
			}
		)
		row = frappe._dict(
			idx=1,
			credit_account="Hifz-ul-Quran - Zakat - JTQ",
			coupon_type="Zakat",
		)

		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.validate_account_for_company"
		) as validate_account, patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.account_matches_coupon_type",
			return_value=True,
		):
			assignment.validate_coupon_income_account(row)

		validate_account.assert_called_once()

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

	def test_return_dialog_uses_generic_title_and_editable_individual_totals(self):
		script = Path(__file__).with_name("book_assignment.js").read_text()

		self.assertIn('title: __("Return Books")', script)
		self.assertNotIn('title: __("Return Donation Book")', script)
		self.assertIn("denomination_total_${index}", script)
		self.assertIn("book_collections: has_individual_books ? book_collections : null", script)

	def test_purchase_receipt_is_not_a_book_assignment_connection(self):
		dashboard = Path(__file__).with_name("book_assignment_dashboard.py").read_text()
		connections_patch = Path(__file__).resolve().parents[3] / "patches" / "ensure_book_assignment_connections.py"

		self.assertNotIn('"Purchase Receipt"', dashboard)
		self.assertNotIn('ensure_purchase_source_link("Purchase Receipt"', connections_patch.read_text())

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

	def test_reopen_clears_only_a_cancelled_stock_entry_link(self):
		doc = frappe._dict(stock_entry="MAT-STE-TEST")
		with patch.object(frappe.db, "get_value", return_value=2):
			clear_cancelled_book_stock_entry_link(doc)
		self.assertIsNone(doc.stock_entry)

		doc.stock_entry = "MAT-STE-ACTIVE"
		with patch.object(frappe.db, "get_value", return_value=1):
			clear_cancelled_book_stock_entry_link(doc)
		self.assertEqual(doc.stock_entry, "MAT-STE-ACTIVE")

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
		with patch.object(frappe.db, "count", return_value=1) as count, patch.object(
			frappe.db, "sql", return_value=[(0,)]
		):
			self.assertTrue(has_unsubmitted_donation_book_leaves("BK-00001"))

		count.assert_called_once_with(
			"Donation Book Leaf",
			{
				"book": "BK-00001",
				"docstatus": ["!=", 2],
				"status": ["not in", ("Used", "Cancelled")],
			},
		)

	def test_donation_book_reopen_requires_collection_of_used_leaves(self):
		with patch.object(frappe.db, "count", return_value=2), patch.object(
			frappe.db, "sql", return_value=[(3,)]
		):
			eligibility = get_donation_book_reopen_eligibility("BK-00001")

		self.assertEqual(eligibility.remaining_leaf_count, 2)
		self.assertEqual(eligibility.uncollected_leaf_count, 3)
		self.assertFalse(eligibility.can_reopen)

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
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_donation_book_reopen_eligibility",
			return_value=frappe._dict(remaining_leaf_count=1, uncollected_leaf_count=0, can_reopen=True),
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.validate_donation_book_order_total_matches_return"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.sync_donation_book_leaves"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.create_book_issue_stock_entry"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.create_book_assignment_issue_log"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.set_reissued_employee"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.now_datetime",
			return_value="2026-10-06 12:00:00",
		):
			reopen_donation_book(doc, "Continue collecting receipts", "EMP-NEW")

		self.assertEqual(doc.status, "Issued")
		self.assertIsNone(doc.return_date)
		self.assertEqual(doc.reopen_count, 1)

	def test_reopen_dialog_selects_the_employee_receiving_the_book(self):
		script = Path(__file__).with_name("book_assignment.js").read_text()

		self.assertIn('fieldname: "issued_to_employee"', script)
		self.assertIn("issued_to_employee: values.issued_to_employee", script)
		self.assertIn('frm.doc.status === "Returned"', script)

	def test_issue_log_records_assignment_employee_history(self):
		doc = frappe._dict(
			name="BK-TEST",
			issued_to_employee="EMP-NEW",
			reopen_reason="Assign the remaining pages to a new volunteer",
		)
		log = Mock()

		with patch.object(frappe, "get_doc", return_value=log) as get_doc, patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.now_datetime",
			return_value="2026-10-08 12:00:00",
		):
			create_book_assignment_issue_log(doc, "Reissued", "EMP-OLD")

		get_doc.assert_called_once_with(
			{
				"doctype": "Book Assignment Issue Log",
				"book_assignment": "BK-TEST",
				"action": "Reissued",
				"action_date": "2026-10-08 12:00:00",
				"employee": "EMP-NEW",
				"previous_employee": "EMP-OLD",
				"reopen_reason": "Assign the remaining pages to a new volunteer",
				"recorded_by": frappe.session.user,
			}
		)
		log.insert.assert_called_once_with(ignore_permissions=True)

	def test_donation_book_cannot_reopen_after_all_leaves_are_submitted(self):
		doc = frappe._dict(name="BK-00001", status="Returned")
		doc.reload = lambda: None
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.update_donation_book_receipt_usage"
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_donation_book_reopen_eligibility",
			return_value=frappe._dict(remaining_leaf_count=0, uncollected_leaf_count=0, can_reopen=False),
		), self.assertRaisesRegex(frappe.ValidationError, "no unused Donation Book Leaves"):
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

	def test_receipt_numbers_must_match_the_format_width_and_prefix(self):
		with self.assertRaisesRegex(frappe.ValidationError, "exactly 3 digits"):
			validate_receipt_number_matches_format("###", "10000", "To Receipt No", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "exactly 3 digits"):
			validate_receipt_number_matches_format("ABC-.###", "ABC-1000", "To Receipt No", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "exactly 3 digits"):
			validate_receipt_number_matches_format("###", "01", "From Receipt No", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "must match Receipt Format"):
			validate_receipt_number_matches_format("ABC-.###", "XYZ-001", "From Receipt No", 1)

		validate_receipt_number_matches_format("ABC-.###", "ABC-001", "From Receipt No", 1)

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

	def test_return_details_are_split_by_coupon_book_serial(self):
		rows = [
			frappe._dict(book_serial_no="CB-001", coupon_value="50", total_pages=10),
			frappe._dict(book_serial_no="CB-002", coupon_value="100", total_pages=5),
		]
		with patch.object(frappe, "get_all", return_value=rows), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_assigned_coupon_used_pages",
			side_effect=lambda _book, serial: {"CB-001": 2, "CB-002": 3}[serial],
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			side_effect=lambda _book, serial=None: {"CB-001": 100, "CB-002": 300}[serial],
		):
			details = get_book_return_details("BA-00005")

		self.assertEqual(details["used_pages"], 5)
		self.assertEqual(details["total_amount"], 400)
		self.assertEqual(details["total_pages"], 15)
		self.assertEqual([row["book_serial_no"] for row in details["book_collections"]], ["CB-001", "CB-002"])

	def test_manual_denomination_total_is_allowed_without_note_counts(self):
		validate_return_collection_denominations(
			{"denomination_total": 300},
			300,
			"CB-001",
		)

	def test_manual_denomination_total_must_match_collected_amount(self):
		with self.assertRaises(frappe.ValidationError):
			validate_return_collection_denominations(
				{"denomination_total": 250},
				300,
				"CB-001",
			)

	def test_coupon_return_collections_are_validated_per_serial(self):
		doc = frappe._dict(
			name="BA-00005",
			assigned_books=[
				frappe._dict(book_type="Coupon Book", book_serial_no="CB-001", total_pages=10),
				frappe._dict(book_type="Coupon Book", book_serial_no="CB-002", total_pages=5),
			],
		)
		collections = [
			{"book_serial_no": "CB-001", "used_pages": 2, "collected_amount": 100, "denomination_total": 100},
			{"book_serial_no": "CB-002", "used_pages": 3, "collected_amount": 300, "denomination_total": 300},
		]
		with patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_assigned_coupon_used_pages",
			side_effect=lambda _book, serial: {"CB-001": 2, "CB-002": 3}[serial],
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.get_book_collected_amount",
			side_effect=lambda _book, serial=None: {"CB-001": 100, "CB-002": 300}[serial],
		):
			totals = validate_coupon_book_return_collections(doc, collections)

		self.assertEqual(totals.used_pages, 5)
		self.assertEqual(totals.collected_amount, 400)

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
			), patch(
				"donation_management.donation_management.doctype.book_assignment.book_assignment.create_book_assignment_issue_log"
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
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.create_book_assignment_issue_log"
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
		), patch(
			"donation_management.donation_management.doctype.book_assignment.book_assignment.create_book_assignment_issue_log"
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
