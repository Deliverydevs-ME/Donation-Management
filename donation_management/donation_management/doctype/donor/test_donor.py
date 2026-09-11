# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donor.donor import get_donor_tree_title


class TestDonor(FrappeTestCase):
	def test_donor_tree_title_shows_family_relationship(self):
		donor = frappe._dict(
			{
				"name": "DONOR-2026-00001",
				"customer_name": "Shakoor Ahmed",
				"family_relationship": "Son",
			}
		)

		self.assertEqual(get_donor_tree_title(donor), "Shakoor Ahmed - Son")

	def test_donor_tree_title_falls_back_to_name(self):
		donor = frappe._dict({"name": "DONOR-2026-00001", "customer_name": "", "family_relationship": ""})

		self.assertEqual(get_donor_tree_title(donor), "DONOR-2026-00001")

	def test_information_request_audit_sets_requesting_user_and_date(self):
		donor = frappe.get_doc(
			{
				"doctype": "Donor",
				"customer_name": "Audit Test Donor",
				"customer_type": "Walk-in",
				"donor_information_request_status": "Requested",
			}
		)

		donor.set_donor_information_request_audit()

		self.assertEqual(donor.requesting_user, frappe.session.user)
		self.assertTrue(donor.request_date)
