# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import json
from pathlib import Path

from frappe.tests.utils import FrappeTestCase
import frappe

from donation_management.donation_management.doctype.donor.donor import Donor


class TestDonorEsaalRelationships(FrappeTestCase):
	def make_donor(self, rows):
		return Donor(
			{
				"doctype": "Donor",
				"name": "DN-TEST",
				"esaal_e_sawab": rows,
			}
		)

	def test_islamic_relationship_limits(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_donor(
				[
					{"person_name": "Parent One", "relationship": "Father"},
					{"person_name": "Parent Two", "relationship": "Father"},
				]
			).validate_esaal_e_sawab_relationships()

		with self.assertRaises(frappe.ValidationError):
			self.make_donor(
				[
					{"person_name": "Mother {0}".format(index), "relationship": "Mother"}
					for index in range(1, 6)
				]
			).validate_esaal_e_sawab_relationships()

	def test_siblings_and_paternal_relations_are_unlimited(self):
		rows = [
			{"person_name": "DN-{0}".format(index), "relationship": "Brother"}
			for index in range(1, 8)
		]
		rows.extend(
			{"person_name": "DN-A{0}".format(index), "relationship": "Paternal Aunt"}
			for index in range(1, 8)
		)

		self.make_donor(rows).validate_esaal_e_sawab_relationships()

	def test_person_name_allows_donor_entered_text(self):
		self.make_donor([{"person_name": "Abdul Rahman", "relationship": "Brother"}]).validate_esaal_e_sawab_relationships()

	def test_relationship_field_is_free_text(self):
		path = Path(__file__).parents[1] / "esaal_e_sawab_detail" / "esaal_e_sawab_detail.json"
		metadata = json.loads(path.read_text())
		relationship = next(field for field in metadata["fields"] if field["fieldname"] == "relationship")
		person_name = next(field for field in metadata["fields"] if field["fieldname"] == "person_name")

		self.assertEqual(person_name["fieldtype"], "Data")
		self.assertNotIn("options", person_name)
		self.assertEqual(relationship["fieldtype"], "Data")
		self.assertNotIn("options", relationship)

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
