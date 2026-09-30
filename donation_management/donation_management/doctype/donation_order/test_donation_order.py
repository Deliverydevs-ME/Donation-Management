# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_order.donation_order import (
	DonationOrder,
	get_esaal_e_sawab_key,
)


class TestDonationOrder(FrappeTestCase):
	def test_esaal_e_sawab_key_normalizes_person_and_relationship(self):
		self.assertEqual(
			get_esaal_e_sawab_key("  Abdul   Rahman  ", " Father "),
			("abdul rahman", "father"),
		)

	def test_esaal_e_sawab_key_requires_person_name(self):
		self.assertIsNone(get_esaal_e_sawab_key("", "Father"))

	def test_esaal_selection_must_be_registered_under_selected_donor(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"donor_name": "DN-TEST",
				"donation_purpose": "Esaal e Sawab",
				"esaal_e_sawab": [
					{"person_name": "DN-UNREGISTERED", "relationship": "Brother"},
				],
			}
		)

		with patch.object(frappe, "get_all", return_value=[]):
			with self.assertRaisesRegex(frappe.ValidationError, "not registered"):
				order.validate_esaal_e_sawab_selection()
