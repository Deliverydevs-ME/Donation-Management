# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


EMPLOYEE_RELATED_EXPENSE_CATEGORIES = ("Salary", "Allowances", "Employee Expenses")
EXPENSE_CATEGORIES = EMPLOYEE_RELATED_EXPENSE_CATEGORIES + ("Operational Expenses", "Other")


class MaktabExpense(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()
		if not self.expense_category:
			self.expense_category = "Operational Expenses"
		if self.expense_category not in EXPENSE_CATEGORIES:
			frappe.throw(frappe._("Expense Category must be one of {0}.").format(", ".join(EXPENSE_CATEGORIES)))
		if flt(self.amount) <= 0:
			frappe.throw(frappe._("Amount must be greater than zero."))
		if not frappe.db.exists("Ilaqi Maktab", self.ilaqi_maktab):
			frappe.throw(frappe._("Ilaqi Maktab {0} was not found.").format(self.ilaqi_maktab))
		self.validate_employee_assignment()

	def validate_employee_assignment(self):
		if self.expense_category not in EMPLOYEE_RELATED_EXPENSE_CATEGORIES:
			return

		if not self.employee:
			frappe.throw(
				frappe._("Employee is required when Expense Category is {0}.").format(self.expense_category)
			)

		if not frappe.db.exists("Employee", self.employee):
			frappe.throw(frappe._("Employee {0} was not found.").format(self.employee))

		posting_date = getdate(self.posting_date)
		assignments = frappe.get_all(
			"Maktab Employee Assignment",
			filters={
				"ilaqi_maktab": self.ilaqi_maktab,
				"employee": self.employee,
				"status": "Active",
				"start_date": ["<=", posting_date],
			},
			or_filters=[
				["end_date", "is", "not set"],
				["end_date", ">=", posting_date],
			],
			pluck="name",
			limit=1,
		)

		if assignments:
			return

		frappe.throw(
			frappe._("Employee {0} is not actively assigned to Ilaqi Maktab {1} on {2}.").format(
				self.employee, self.ilaqi_maktab, frappe.format(posting_date)
			)
		)
