# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDonationPurpose(FrappeTestCase):
	def test_obsolete_fields_are_not_part_of_purpose_configuration(self):
		purpose_meta = frappe.get_meta("Donation Purpose")
		mapping_meta = frappe.get_meta("Donation Purpose Account Mapping")

		self.assertFalse(purpose_meta.has_field("requires_esaal_e_sawab"))
		self.assertFalse(mapping_meta.has_field("is_default"))

	def test_purpose_path_is_stored_but_hidden(self):
		self.assertTrue(frappe.get_meta("Donation Purpose").get_field("purpose_path").hidden)
		self.assertTrue(frappe.get_meta("Donation Order Purpose Detail").get_field("purpose_path").hidden)
