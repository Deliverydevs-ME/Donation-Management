# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_book_leaf.donation_book_leaf import (
	DonationBookLeaf,
	cancel_leaf_for_donation_order,
	get_donor_donation_orders,
)
from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	get_mohasil_donation_book_leaves,
)


class TestDonationBookLeaf(FrappeTestCase):
	def test_leaf_is_submittable(self):
		path = Path(__file__).with_name("donation_book_leaf.json")
		metadata = json.loads(path.read_text())
		self.assertEqual(metadata.get("is_submittable"), 1)

	def test_leaf_with_order_and_journal_cannot_be_cancelled_directly(self):
		leaf = DonationBookLeaf(
			{
				"doctype": "Donation Book Leaf",
				"donation_order": "DO-TEST",
				"journal_entry": "ACC-JV-TEST",
				"status": "Used",
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "cannot be cancelled directly"):
			leaf.before_cancel()

	def test_leaf_can_be_cancelled_by_its_own_donation_order(self):
		leaf = DonationBookLeaf(
			{
				"doctype": "Donation Book Leaf",
				"donation_order": "DO-TEST",
				"journal_entry": "ACC-JV-TEST",
				"status": "Used",
			}
		)
		leaf.flags.from_donation_order_cancellation = True

		leaf.before_cancel()

	def test_order_cancellation_cancels_leaf_before_clearing_accounting_links(self):
		leaf = frappe._dict(name="DBL-TEST", docstatus=1)
		leaf_doc = frappe._dict(flags=frappe._dict(), cancel=MagicMock())

		with patch.object(frappe.db, "table_exists", return_value=True), patch.object(
			frappe, "get_all", return_value=[leaf]
		), patch.object(frappe, "get_doc", return_value=leaf_doc), patch.object(
			frappe.db, "set_value"
		) as set_value:
			cancel_leaf_for_donation_order("DO-TEST")

		self.assertTrue(leaf_doc.flags.from_donation_order_cancellation)
		self.assertTrue(leaf_doc.flags.ignore_permissions)
		leaf_doc.cancel.assert_called_once()
		set_value.assert_called_once_with(
			"Donation Book Leaf",
			"DBL-TEST",
			{"status": "Cancelled", "journal_entry": None, "accounting_status": "Cancelled"},
			update_modified=False,
		)

	def test_donor_order_query_requires_donor(self):
		with patch.object(frappe, "get_all") as get_all:
			self.assertEqual(get_donor_donation_orders("Donation Order", "", "name", 0, 20, {}), [])
			get_all.assert_not_called()

	def test_donor_order_query_filters_to_leaf_book_serial_and_receipt(self):
		query_method = get_donor_donation_orders
		while hasattr(query_method, "__wrapped__"):
			query_method = query_method.__wrapped__

		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			query_method(
				"Donation Order",
				"",
				"name",
				0,
				20,
				{
					"donor": "DN-0001",
					"book": "BK-0001",
					"book_serial_no": "DB-001",
					"receipt_number": "DBZ-001",
				},
			)

		query, values = sql.call_args.args
		self.assertIn("order_doc.name as label", query)
		self.assertNotIn("concat(coalesce(order_doc.donor_name", query)
		self.assertIn("order_doc.donation_book = %(book)s", query)
		self.assertIn("order_doc.donation_book_serial_no = %(book_serial_no)s", query)
		self.assertIn("tabDonation Order Purpose Detail", query)
		self.assertEqual(values["receipt_number"], "DBZ-001")

	def test_mohasil_leaf_query_requires_selected_book_or_serial(self):
		query_method = get_mohasil_donation_book_leaves
		while hasattr(query_method, "__wrapped__"):
			query_method = query_method.__wrapped__

		with patch.object(frappe.db, "sql") as sql:
			self.assertEqual(
				query_method("Donation Book Leaf", "", "name", 0, 20, {"mohasil": "HR-EMP-0001"}),
				[],
			)
			sql.assert_not_called()

	def test_mohasil_leaf_query_filters_to_selected_book_and_serial(self):
		query_method = get_mohasil_donation_book_leaves
		while hasattr(query_method, "__wrapped__"):
			query_method = query_method.__wrapped__

		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			query_method(
				"Donation Book Leaf",
				"",
				"name",
				0,
				20,
				{"mohasil": "HR-EMP-0001", "book": "BK-0001", "book_serial_no": "DB-001"},
			)

		query, values = sql.call_args.args
		self.assertIn("book.name = %(book)s", query)
		self.assertIn("detail.book_serial_no = %(book_serial_no)s", query)
		self.assertEqual(values["book"], "BK-0001")
		self.assertEqual(values["book_serial_no"], "DB-001")
