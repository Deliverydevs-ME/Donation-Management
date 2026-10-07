from frappe import _


def get_data():
	return {
		"fieldname": "donation_order",
		"internal_links": {
			"Journal Entry": "journal_entry",
		},
		"non_standard_fieldnames": {
			"Donation Book Leaf": "donation_order",
		},
		"transactions": [
			{"label": _("Transactions"), "items": ["Donation Book Leaf"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
