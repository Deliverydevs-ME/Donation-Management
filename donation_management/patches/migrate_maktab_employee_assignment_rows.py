"""Move legacy one-employee assignments into the assigned-employee grid."""

import frappe


PARENT_DOCTYPE = "Maktab Employee Assignment"
CHILD_DOCTYPE = "Maktab Employee Assignment Detail"
PARENTFIELD = "assigned_employees"


def execute():
	if not (
		frappe.db.table_exists(PARENT_DOCTYPE)
		and frappe.db.table_exists(CHILD_DOCTYPE)
	):
		return

	legacy_rows = frappe.db.sql(
		"""
			select name, employee, start_date, end_date, salary_cost, status
			from `tabMaktab Employee Assignment`
			where ifnull(employee, '') != ''
		""",
		as_dict=True,
	)
	for row in legacy_rows:
		if frappe.db.exists(
			CHILD_DOCTYPE,
			{
				"parent": row.name,
				"parenttype": PARENT_DOCTYPE,
				"parentfield": PARENTFIELD,
			},
		):
			continue

		frappe.get_doc(
			{
				"doctype": CHILD_DOCTYPE,
				"parent": row.name,
				"parenttype": PARENT_DOCTYPE,
				"parentfield": PARENTFIELD,
				"idx": 1,
				"employee": row.employee,
				"start_date": row.start_date,
				"end_date": row.end_date,
				"salary_cost": row.salary_cost,
				"status": row.status or "Active",
			}
		).insert(ignore_permissions=True)
