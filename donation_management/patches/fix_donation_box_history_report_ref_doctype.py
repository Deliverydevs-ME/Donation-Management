import frappe


def execute():
	for report in ("Donation Box Status Report", "Donation Box History Report"):
		if not frappe.db.exists("Report", report):
			continue

		frappe.db.set_value(
			"Report",
			report,
			"ref_doctype",
			"Box Collection",
			update_modified=False,
		)
