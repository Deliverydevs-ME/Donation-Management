from frappe import _


def get_data():
	return {
		"fieldname": "coupon_book_leaf",
		"internal_links": {
			"Book Assignment": "book",
			"Coupon Entry": "coupon_entry",
			"Journal Entry": "journal_entry",
		},
		"transactions": [
			{"label": _("Book"), "items": ["Book Assignment"]},
			{"label": _("Coupon"), "items": ["Coupon Entry"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
