import frappe


def execute():
	if not frappe.db.exists("Report", "Donation Box Status Report"):
		return

	frappe.db.set_value(
		"Report",
		"Donation Box Status Report",
		"ref_doctype",
		"Box Collection",
		update_modified=False,
	)
