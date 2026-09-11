# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_order.donation_order import (
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
