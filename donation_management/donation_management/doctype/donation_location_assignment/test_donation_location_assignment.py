# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch


class TestDonationLocationAssignment(FrappeTestCase):
	def test_duplicate_assignment_same_employee_location_and_dates_throws(self):
		assignment = frappe.get_doc(
			{
				"doctype": "Donation Location Assignment",
				"name": "DLA-TEST-NEW",
				"employee": "HR-EMP-TEST",
				"donation_location": "TEST LOCATION",
				"start_date": "2026-08-01",
				"end_date": "2026-08-31",
			}
		)

		with patch("frappe.db.sql", return_value=[frappe._dict({"name": "DLA-TEST-EXISTING"})]) as db_sql:
			with self.assertRaisesRegex(frappe.ValidationError, "already exists"):
				assignment.validate_duplicate_assignment()

		query = next(
			call.args[0]
			for call in db_sql.call_args_list
			if "tabDonation Location Assignment" in call.args[0]
		)
		self.assertIn("donation_location = %(donation_location)s", query)
		self.assertIn("start_date = %(start_date)s", query)

	def test_same_employee_same_dates_different_location_throws(self):
		assignment = frappe.get_doc(
			{
				"doctype": "Donation Location Assignment",
				"name": "DLA-TEST-NEW",
				"employee": "HR-EMP-TEST",
				"donation_location": "NEW LOCATION",
				"start_date": "2026-08-01",
				"end_date": "2026-08-31",
			}
		)

		with patch(
			"frappe.db.sql",
			return_value=[
				frappe._dict(
					{
						"name": "DLA-TEST-EXISTING",
						"donation_location": "OLD LOCATION",
					}
				)
			],
		) as db_sql:
			with self.assertRaisesRegex(frappe.ValidationError, "same Start Date"):
				assignment.validate_same_employee_same_dates()

		query = next(
			call.args[0]
			for call in db_sql.call_args_list
			if "tabDonation Location Assignment" in call.args[0]
		)
		self.assertIn("employee = %(employee)s", query)
		self.assertIn("start_date = %(start_date)s", query)
		self.assertNotIn("donation_location = %(donation_location)s", query)

	def test_overlap_validation_checks_draft_and_submitted_assignments(self):
		assignment = frappe.get_doc(
			{
				"doctype": "Donation Location Assignment",
				"name": "DLA-TEST-NEW",
				"employee": "HR-EMP-TEST",
				"donation_location": "TEST LOCATION",
				"start_date": "2026-08-01",
				"end_date": "2026-08-31",
			}
		)

		with patch(
			"frappe.db.sql",
			return_value=[
				frappe._dict(
					{
						"name": "DLA-TEST-EXISTING",
						"start_date": "2026-08-01",
						"end_date": "2026-08-31",
					}
				)
			],
		) as db_sql:
			with self.assertRaisesRegex(frappe.ValidationError, "overlapping"):
				assignment.validate_overlap()

		query = next(
			call.args[0]
			for call in db_sql.call_args_list
			if "tabDonation Location Assignment" in call.args[0]
		)
		self.assertIn("docstatus != 2", query)
