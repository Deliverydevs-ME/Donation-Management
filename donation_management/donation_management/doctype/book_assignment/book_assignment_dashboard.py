from frappe import _


def get_data():
	return {
		"fieldname": "book",
		"non_standard_fieldnames": {
			"Book Assignment Issue Log": "book_assignment",
			"Material Request": "custom_book_assignment",
			"Purchase Receipt": "custom_book_assignment",
		},
		"internal_links": {
			"Journal Entry": "journal_entry",
			"Stock Entry": "stock_entry",
		},
		"transactions": [
			{"label": _("Purchase Sources"), "items": ["Material Request", "Purchase Receipt", "Stock Entry"]},
			{"label": _("Coupon Processing"), "items": ["Coupon Entry", "Coupon Book Leaf"]},
			{"label": _("Assignment History"), "items": ["Book Assignment Issue Log"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
