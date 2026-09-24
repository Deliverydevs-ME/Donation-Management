import frappe


def execute():
	if not frappe.db.has_column("Maktab Expense", "expense_category"):
		return

	frappe.db.sql(
		"""
		update `tabMaktab Expense`
		set expense_category = 'Operational Expenses'
		where ifnull(expense_category, '') = ''
		"""
	)
