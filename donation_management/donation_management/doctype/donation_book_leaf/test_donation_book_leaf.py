# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_book_leaf.donation_book_leaf import (
	DonationBookLeaf,
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
