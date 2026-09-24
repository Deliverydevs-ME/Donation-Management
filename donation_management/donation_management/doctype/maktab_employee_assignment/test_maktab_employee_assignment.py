# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.api import get_default_company


class TestMaktabEmployeeAssignment(FrappeTestCase):
	def make_ilaqi_maktab(self, head_count=1):
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"TEST-MAKTAB-{frappe.generate_hash(length=8)}",
				"head_count": head_count,
				"status": "Active",
			}
		)
		maktab.insert()
		return maktab

	def make_employee(self, first_name):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first_name,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2026-01-01",
				"company": get_default_company(),
				"status": "Active",
				"custom_cnic": frappe.generate_hash(length=13).upper().replace("-", "1")[:13],
			}
		)
		employee.insert(ignore_permissions=True)
		return employee.name

	def make_assignment(self, maktab, employee, status="Active"):
		assignment = frappe.get_doc(
			{
				"doctype": "Maktab Employee Assignment",
				"ilaqi_maktab": maktab.name,
				"employee": employee,
				"start_date": "2026-01-01",
				"status": status,
			}
		)
		assignment.insert()
		return assignment

	def test_active_assignments_cannot_exceed_head_count(self):
		maktab = self.make_ilaqi_maktab(head_count=1)
		self.make_assignment(maktab, self.make_employee("Maktab Capacity One"))

		with self.assertRaises(frappe.ValidationError):
			self.make_assignment(maktab, self.make_employee("Maktab Capacity Two"))

	def test_head_count_cannot_be_reduced_below_active_assignments(self):
		maktab = self.make_ilaqi_maktab(head_count=2)
		self.make_assignment(maktab, self.make_employee("Maktab Capacity Three"))
		self.make_assignment(maktab, self.make_employee("Maktab Capacity Four"))

		maktab.head_count = 1
		with self.assertRaises(frappe.ValidationError):
			maktab.save()
