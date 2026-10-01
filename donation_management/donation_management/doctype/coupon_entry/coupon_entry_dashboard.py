from frappe import _


def get_data():
	return {
		"internal_links": {
			"Book Assignment": "book",
			"Journal Entry": "journal_entry",
		},
		"non_standard_fieldnames": {
			"Coupon Book Leaf": "coupon_entry",
		},
		"transactions": [
			{"label": _("References"), "items": ["Book Assignment"]},
			{"label": _("Transactions"), "items": ["Coupon Book Leaf"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
