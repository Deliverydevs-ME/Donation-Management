# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.api import get_default_company


class TestBoxCollection(FrappeTestCase):
	def make_donation_box(self, donation_head="Zakat"):
		box = frappe.get_doc(
			{
				"doctype": "Donation Box",
				"box_number": f"TEST-{frappe.generate_hash(length=8)}",
				"donation_head": donation_head,
			}
		)
		box.insert()
		box.submit()
		return box

	def make_donation_location(self):
		location_type = frappe.db.get_value("Location Type", {"location": "Office"}, "name")
		if not location_type:
			location_type = frappe.get_doc({"doctype": "Location Type", "location": "Office"}).insert().name

		location = frappe.get_doc(
			{
				"doctype": "Donation Location",
				"location_name": f"TEST-LOC-{frappe.generate_hash(length=8)}",
				"location_type": location_type,
				"shophouse_name": "Test Shop",
				"address": "Test Address",
			}
		)
		location.insert()
		return location.name

	def get_box_collection(self, box):
		return frappe.get_doc("Box Collection", {"box_number": box.name})

	def make_mohasil_employee(self, first_name):
		if not frappe.db.exists("Designation", "Mohasil"):
			frappe.get_doc({"doctype": "Designation", "designation_name": "Mohasil"}).insert()

		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first_name,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2026-01-01",
				"company": get_default_company(),
				"status": "Active",
				"designation": "Mohasil",
				"custom_cnic": frappe.generate_hash(length=13).upper().replace("-", "1")[:13],
			}
		)
		employee.insert(ignore_permissions=True)
		return employee.name

	def ensure_box_collection_mapping(self, donation_head="Zakat"):
		company = get_default_company()
		if frappe.db.exists(
			"Donation Source Account Mapping",
			{"company": company, "source_type": "Box Collection", "donation_type": donation_head},
		):
			return

		income_account = frappe.db.get_value(
			"Account",
			{"company": company, "root_type": "Income", "is_group": 0},
			"name",
		)
		if not income_account:
			self.skipTest("No income account is available for Box Collection mapping.")

		frappe.get_doc(
			{
				"doctype": "Donation Source Account Mapping",
				"company": company,
				"source_type": "Box Collection",
				"donation_type": donation_head,
				"credit_account": income_account,
			}
		).insert(ignore_permissions=True)

	def test_shape_derives_from_donation_head(self):
		box = self.make_donation_box("Zakat")
		self.assertEqual(box.box_shape, "Square")

	def test_submit_donation_box_creates_submitted_collection(self):
		box = self.make_donation_box("Atiya")
		box_collection = self.get_box_collection(box)

		self.assertEqual(box_collection.docstatus, 1)
		self.assertEqual(box_collection.status, "Available")
		self.assertEqual(box_collection.donation_head, "Atiya")
		self.assertEqual(box_collection.box_shape, box.box_shape)

	def test_duplicate_box_collection_is_blocked(self):
		box = self.make_donation_box("Sadqa")

		duplicate = frappe.get_doc(
			{
				"doctype": "Box Collection",
				"box_number": box.name,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			duplicate.insert()

	def test_collection_before_issuance_is_blocked(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)

		with self.assertRaises(frappe.ValidationError):
			box_collection.set_collection_date(
				collection_office=self.make_mohasil_employee("Collector"),
				collected_amount=100,
				denominations={100: 1},
			)

	def test_issuance_while_issued_is_blocked(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)
		donation_location = self.make_donation_location()
		dispatcher = self.make_mohasil_employee("Dispatcher")
		box_collection.set_issuance_date(
			donation_location=donation_location,
			location_type="Office",
			location_name="Test Shop",
			donor_location="Test Address",
			deployment_officer=dispatcher,
			approval_reference="TEST-APPROVAL",
			approved_by=frappe.session.user,
		)
		box_collection.reload()

		with self.assertRaises(frappe.ValidationError):
			box_collection.set_issuance_date(
				location_type="Office",
				location_name="Another Shop",
				donor_location="Another Address",
				deployment_officer=dispatcher,
			)

	def test_denomination_total_mismatch_is_blocked(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)
		donation_location = self.make_donation_location()
		dispatcher = self.make_mohasil_employee("Dispatcher")
		collector = self.make_mohasil_employee("Collector")
		box_collection.set_issuance_date(
			donation_location=donation_location,
			location_type="Office",
			location_name="Test Shop",
			donor_location="Test Address",
			deployment_officer=dispatcher,
			approval_reference="TEST-APPROVAL",
			approved_by=frappe.session.user,
		)
		box_collection.reload()

		with self.assertRaises(frappe.ValidationError):
			box_collection.set_collection_date(
				collection_office=collector,
				collected_amount=150,
				denominations={100: 1},
			)

	def test_successful_collection_logs_amount_and_denominations(self):
		self.ensure_box_collection_mapping()
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)
		donation_location = self.make_donation_location()
		dispatcher = self.make_mohasil_employee("Dispatcher")
		collector = self.make_mohasil_employee("Collector")
		box_collection.set_issuance_date(
			donation_location=donation_location,
			location_type="Office",
			location_name="Test Shop",
			donor_location="Test Address",
			deployment_officer=dispatcher,
			approval_reference="TEST-APPROVAL",
			approved_by=frappe.session.user,
		)
		box_collection.reload()
		box_collection.set_collection_date(
			collection_office=collector,
			collected_amount=150,
			denominations={100: 1, 50: 1},
		)
		box_collection.reload()

		self.assertEqual(box_collection.status, "Collected")
		self.assertEqual(box_collection.collected_amount, 150)

		collection_log_name = frappe.db.get_value(
			"Box Collection Log",
			{
				"box_collection": box_collection.name,
				"action": "Collection",
			},
			"name",
			order_by="creation desc",
		)
		collection_log = frappe.get_doc("Box Collection Log", collection_log_name)
		self.assertEqual(collection_log.collected_amount, 150)
		self.assertEqual(sum(row.amount for row in collection_log.cash_denominations), 150)
