# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors

import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_book_collection.donation_book_collection import (
	get_donation_book_assignments,
	get_donation_book_serials,
)


def unwrap_search_method(method):
	while hasattr(method, "__wrapped__"):
		method = method.__wrapped__
	return method


class TestDonationBookCollection(FrappeTestCase):
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
