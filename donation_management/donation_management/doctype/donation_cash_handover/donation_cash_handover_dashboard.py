from frappe import _


def get_data():
	return {
		"internal_links": {"Donation Closing": "donation_closing"},
		"transactions": [
			{"label": _("References"), "items": ["Donation Closing"]},
		],
	}
