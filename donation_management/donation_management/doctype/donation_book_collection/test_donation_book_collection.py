# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors

import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_book_collection.donation_book_collection import (
	DonationBookCollection,
	get_book_assignment_details,
	get_donation_book_assignments,
	get_donation_book_serials,
)


def unwrap_search_method(method):
	while hasattr(method, "__wrapped__"):
		method = method.__wrapped__
	return method


class TestDonationBookCollection(FrappeTestCase):
	def test_collection_layout_has_no_amount_or_collection_accounting_fields(self):
		path = Path(__file__).with_name("donation_book_collection.json")
		metadata = json.loads(path.read_text())
		fieldnames = {field.get("fieldname") for field in metadata["fields"]}
		self.assertFalse(
			fieldnames.intersection(
				{
					"manual_receipt_number",
					"manual_receipt_date",
					"cash_amount",
					"online_amount",
					"donation_order",
					"returned_unused_amount",
					"mode_of_payment",
					"debit_account",
					"credit_account",
					"journal_entry",
				}
			)
		)
		self.assertEqual(metadata["field_order"].index("accounting_section") + 1, metadata["field_order"].index("accounting_cost_center"))
		self.assertEqual(metadata["field_order"].index("accounting_cost_center") + 1, metadata["field_order"].index("status"))
		detail_table = next(field for field in metadata["fields"] if field.get("fieldname") == "book_assignment_details")
		self.assertEqual(detail_table.get("read_only"), 1)

	def test_collection_detail_grid_references_order_journal_entry(self):
		path = Path(__file__).parents[1] / "donation_book_collection_detail" / "donation_book_collection_detail.json"
		metadata = json.loads(path.read_text())
		fieldnames = {field.get("fieldname") for field in metadata["fields"]}
		self.assertIn("journal_entry", fieldnames)
		self.assertNotIn("debit_account", fieldnames)
		self.assertNotIn("credit_account", fieldnames)

	def test_collection_details_are_limited_to_submitted_leaves_and_orders(self):
		assignment = frappe._dict(check_permission=lambda permission: None)
		leaves = [
			frappe._dict(
				book_serial_no="DB-001",
				receipt_number="REC-001",
				manual_receipt_date="2026-10-06",
				payment_mode="Cash",
				amount=500,
				donation_order="DO-00001",
				journal_entry="ACC-JV-00001",
				status="Used",
			)
		]
		with patch.object(frappe, "get_doc", return_value=assignment), patch.object(
			frappe.db, "sql", return_value=leaves
		) as sql:
			rows = get_book_assignment_details("BK-00001", "DB-001")

		self.assertEqual(rows[0]["donation_order"], "DO-00001")
		self.assertEqual(rows[0]["journal_entry"], "ACC-JV-00001")
		self.assertEqual(rows[0]["amount"], 500)
		query, values = sql.call_args.args
		self.assertIn("leaf.docstatus = 1", query)
		self.assertIn("leaf.status = 'Used'", query)
		self.assertIn("order_doc.docstatus = 1", query)
		self.assertEqual(values, {"book": "BK-00001", "book_serial_no": "DB-001"})

	def test_collection_uses_explicit_fetch_action(self):
		path = Path(__file__).with_name("donation_book_collection.js")
		script = path.read_text()
		self.assertIn('__("Fetch Submitted Receipts")', script)
		self.assertNotIn("populate_book_assignment_details", script)

	def test_save_populates_empty_collection_details_without_fetching_in_browser(self):
		collection = DonationBookCollection(
			{
				"doctype": "Donation Book Collection",
				"book": "BK-00001",
				"book_serial_no": "DB-001",
			}
		)
		fetched_rows = [
			{
				"book_serial_no": "DB-001",
				"receipt_number": "REC-001",
				"amount": 500,
				"donation_order": "DO-00001",
			}
		]

		with patch(
			"donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_book_assignment_details",
			return_value=fetched_rows,
		) as get_details:
			collection.populate_assignment_details_if_empty()

		get_details.assert_called_once_with("BK-00001", "DB-001")
		self.assertEqual(collection.book_assignment_details[0].receipt_number, "REC-001")

	def test_save_does_not_replace_details_fetched_in_browser(self):
		collection = DonationBookCollection(
			{
				"doctype": "Donation Book Collection",
				"book": "BK-00001",
				"book_assignment_details": [{"receipt_number": "REC-001"}],
			}
		)

		with patch(
			"donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_book_assignment_details"
		) as get_details:
			collection.populate_assignment_details_if_empty()

		get_details.assert_not_called()

	def test_collection_submission_requires_fetched_rows(self):
		collection = DonationBookCollection({"doctype": "Donation Book Collection"})
		with self.assertRaisesRegex(frappe.ValidationError, "Fetch at least one submitted Donation Book Leaf"):
			collection.before_submit()

	def test_collection_requires_book_serial_no(self):
		collection = DonationBookCollection({"doctype": "Donation Book Collection", "book": "BK-00001"})
		with self.assertRaisesRegex(frappe.ValidationError, "Select a Book Serial No"):
			collection.validate_book_serial_no()

	def test_collection_submission_sets_date_without_creating_accounting(self):
		collection = DonationBookCollection({"doctype": "Donation Book Collection", "status": "Draft"})
		with patch(
			"donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.today",
			return_value="2026-10-06",
		), patch.object(collection, "db_set") as db_set:
			collection.on_submit()

		self.assertEqual(collection.collection_date, "2026-10-06")
		self.assertEqual(collection.status, "Submitted")
		db_set.assert_called_once_with(
			{"collection_date": "2026-10-06", "status": "Submitted"}, update_modified=False
		)

	def test_collection_cancellation_only_changes_collection_status(self):
		collection = DonationBookCollection({"doctype": "Donation Book Collection"})
		with patch.object(collection, "db_set") as db_set:
			collection.on_cancel()

		db_set.assert_called_once_with("status", "Cancelled", update_modified=False)

	def test_book_query_is_restricted_to_donation_book_assignments(self):
		query_method = unwrap_search_method(get_donation_book_assignments)

		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			query_method("Book Assignment", "", "name", 0, 20, {})

		query, values = sql.call_args.args
		self.assertIn("book.book_type = %(donation_book_type)s", query)
		self.assertIn("detail.book_type = %(donation_book_type)s", query)
		self.assertNotIn("book.book_type = 'Coupon Book'", query)
		self.assertEqual(values["donation_book_type"], "Donation Book")

	def test_serial_query_returns_nothing_until_assignment_is_selected(self):
		query_method = unwrap_search_method(get_donation_book_serials)

		with patch.object(frappe.db, "sql") as sql:
			self.assertEqual(query_method("Serial No", "", "name", 0, 20, {}), [])
			sql.assert_not_called()

	def test_serial_query_is_restricted_to_selected_assignment_donation_rows(self):
		query_method = unwrap_search_method(get_donation_book_serials)

		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			query_method("Serial No", "DB", "name", 0, 20, {"book": "BK-0001"})

		query, values = sql.call_args.args
		self.assertIn("detail.parent = %(book)s", query)
		self.assertIn("detail.book_type = %(donation_book_type)s", query)
		self.assertEqual(values["book"], "BK-0001")

	def test_mohasil_layout_has_no_redundant_column_break(self):
		path = (
			Path(__file__).parents[1]
			/ "donation_order"
			/ "donation_order.json"
		)
		metadata = json.loads(path.read_text())
		self.assertNotIn("mohasil_column_break", metadata["field_order"])
		self.assertNotIn(
			"mohasil_column_break",
			{field.get("fieldname") for field in metadata["fields"]},
		)
