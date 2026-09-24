# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.api import get_default_company
from donation_management.donation_management.report.ilaqi_maktab_financial_summary.ilaqi_maktab_financial_summary import (
	execute as execute_financial_summary,
)


class TestMaktabExpense(FrappeTestCase):
	def make_ilaqi_maktab(self, name_suffix=None):
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"TEST-MAKTAB-EXP-{name_suffix or frappe.generate_hash(length=8)}",
				"head_count": 5,
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

	def make_assignment(self, maktab, employee, start_date="2026-09-01", end_date="2026-09-30"):
		assignment = frappe.get_doc(
			{
				"doctype": "Maktab Employee Assignment",
				"ilaqi_maktab": maktab.name,
				"employee": employee,
				"start_date": start_date,
				"end_date": end_date,
				"salary_cost": 1000,
				"status": "Active",
			}
		)
		assignment.insert()
		return assignment

	def make_expense(
		self,
		maktab,
		category="Operational Expenses",
		amount=100,
		employee=None,
		posting_date="2026-09-15",
		submit=False,
	):
		expense = frappe.get_doc(
			{
				"doctype": "Maktab Expense",
				"ilaqi_maktab": maktab.name,
				"posting_date": posting_date,
				"expense_category": category,
				"employee": employee,
				"expense_type": f"{category} Test",
				"amount": amount,
			}
		)
		expense.insert()
		if submit:
			expense.submit()
		return expense

	def test_employee_related_expense_requires_employee(self):
		maktab = self.make_ilaqi_maktab()

		with self.assertRaises(frappe.ValidationError):
			self.make_expense(maktab, category="Salary")

	def test_employee_related_expense_requires_active_assignment_on_posting_date(self):
		maktab = self.make_ilaqi_maktab()
		employee = self.make_employee("Maktab Expense Assignment")
		self.make_assignment(maktab, employee)

		self.make_expense(maktab, category="Allowances", employee=employee, posting_date="2026-09-15")

		with self.assertRaises(frappe.ValidationError):
			self.make_expense(maktab, category="Allowances", employee=employee, posting_date="2026-10-01")

	def test_employee_related_expense_cannot_use_assignment_from_another_maktab(self):
		assigned_maktab = self.make_ilaqi_maktab("ASSIGNED")
		other_maktab = self.make_ilaqi_maktab("OTHER")
		employee = self.make_employee("Maktab Expense Other")
		self.make_assignment(assigned_maktab, employee)

		with self.assertRaises(frappe.ValidationError):
			self.make_expense(other_maktab, category="Employee Expenses", employee=employee)

	def test_operational_expense_does_not_require_employee(self):
		maktab = self.make_ilaqi_maktab()
		expense = self.make_expense(maktab, category="Operational Expenses")

		self.assertEqual(expense.expense_category, "Operational Expenses")
		self.assertFalse(expense.employee)

	def test_financial_summary_tracks_expense_categories(self):
		maktab = self.make_ilaqi_maktab()
		employee = self.make_employee("Maktab Expense Summary")
		self.make_assignment(maktab, employee)

		self.make_expense(maktab, category="Salary", amount=100, employee=employee, submit=True)
		self.make_expense(maktab, category="Allowances", amount=20, employee=employee, submit=True)
		self.make_expense(maktab, category="Employee Expenses", amount=30, employee=employee, submit=True)
		self.make_expense(maktab, category="Operational Expenses", amount=40, submit=True)
		self.make_expense(maktab, category="Other", amount=10, submit=True)

		columns, rows = execute_financial_summary({})
		row = next(row for row in rows if row.ilaqi_maktab == maktab.name)

		self.assertEqual(row.salary_amount, 100)
		self.assertEqual(row.allowance_amount, 20)
		self.assertEqual(row.employee_expense_amount, 30)
		self.assertEqual(row.operational_expense_amount, 40)
		self.assertEqual(row.other_expense_amount, 10)
		self.assertEqual(row.expense_amount, 200)
