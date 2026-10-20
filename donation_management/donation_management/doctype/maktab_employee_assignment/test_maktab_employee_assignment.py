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

	def make_assignment(self, maktab, employees):
		assignment = frappe.get_doc(
			{
				"doctype": "Maktab Employee Assignment",
				"ilaqi_maktab": maktab.name,
				"assigned_employees": employees,
			}
		)
		assignment.insert()
		return assignment

	def test_active_assignments_cannot_exceed_head_count(self):
		maktab = self.make_ilaqi_maktab(head_count=1)
		self.make_assignment(
			maktab,
			[{"employee": self.make_employee("Maktab Capacity One"), "start_date": "2026-01-01"}],
		)

		with self.assertRaises(frappe.ValidationError):
			self.make_assignment(
				maktab,
				[{"employee": self.make_employee("Maktab Capacity Two"), "start_date": "2026-01-01"}],
			)

	def test_head_count_cannot_be_reduced_below_active_assignments(self):
		maktab = self.make_ilaqi_maktab(head_count=2)
		self.make_assignment(
			maktab,
			[
				{"employee": self.make_employee("Maktab Capacity Three"), "start_date": "2026-01-01"},
				{"employee": self.make_employee("Maktab Capacity Four"), "start_date": "2026-01-01"},
			],
		)

		maktab.head_count = 1
		with self.assertRaises(frappe.ValidationError):
			maktab.save()

	def test_multiple_employees_keep_their_own_salary_and_dates(self):
		maktab = self.make_ilaqi_maktab(head_count=2)
		first_employee = self.make_employee("Maktab Grid One")
		second_employee = self.make_employee("Maktab Grid Two")

		assignment = self.make_assignment(
			maktab,
			[
				{
					"employee": first_employee,
					"salary_cost": 1000,
					"start_date": "2026-01-01",
					"end_date": "2026-06-30",
					"status": "Active",
				},
				{
					"employee": second_employee,
					"salary_cost": 1500,
					"start_date": "2026-02-01",
					"status": "Inactive",
				},
			],
		)

		self.assertEqual(len(assignment.assigned_employees), 2)
		self.assertEqual(assignment.assigned_employees[0].salary_cost, 1000)
		self.assertEqual(assignment.assigned_employees[1].status, "Inactive")

	def test_employee_cannot_be_added_twice_in_one_grid(self):
		maktab = self.make_ilaqi_maktab(head_count=2)
		employee = self.make_employee("Maktab Duplicate Grid")

		with self.assertRaises(frappe.ValidationError):
			self.make_assignment(
				maktab,
				[
					{"employee": employee, "start_date": "2026-01-01"},
					{"employee": employee, "start_date": "2026-02-01"},
				],
			)
