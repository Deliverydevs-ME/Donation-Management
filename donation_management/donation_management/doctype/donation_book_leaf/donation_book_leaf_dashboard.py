from frappe import _


def get_data():
	return {
		"fieldname": "donation_book_leaf",
		"internal_links": {
			"Book Assignment": "book",
			"Journal Entry": "journal_entry",
		},
		"transactions": [
			{"label": _("Book"), "items": ["Book Assignment"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
