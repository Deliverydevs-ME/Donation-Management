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
