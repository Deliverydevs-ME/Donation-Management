from frappe import _


def get_data():
	return {
		"fieldname": "donation_closing",
		"transactions": [
			{"label": _("Cash Handling"), "items": ["Donation Cash Handover"]},
		],
	}
