# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDonationBox(FrappeTestCase):
	def test_workflow_approval_fields_are_removed_and_care_of_donor_is_restricted(self):
		box_meta = frappe.get_meta("Donation Box")
		self.assertIsNone(box_meta.get_field("first_issuance_approved_by"))
		self.assertIsNone(box_meta.get_field("location_change_approved_by"))

		location_meta = frappe.get_meta("Donation Box Location")
		self.assertEqual(location_meta.get_field("care_of_donor").options, "Donor")
