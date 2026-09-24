import frappe


REPORT_REFERENCE_DOCTYPES = {
	"Book Leaves Status Report": "Donation Book Leaf",
	"Cash Handover and Cashier Variance Report": "Donation Cash Handover",
	"Donation Closing and Pending Closing": "Donation Closing",
	"Ilaqi Maktab Financial Summary": "Ilaqi Maktab",
}


def execute():
	for report, ref_doctype in REPORT_REFERENCE_DOCTYPES.items():
		if not frappe.db.exists("Report", report):
			continue

		frappe.db.set_value(
			"Report",
			report,
			"ref_doctype",
			ref_doctype,
			update_modified=False,
		)
