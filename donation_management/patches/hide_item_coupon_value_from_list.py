import frappe


def execute():
	"""Keep the internal coupon-value setup field out of the Item list view."""
	frappe.db.set_value(
		"Custom Field",
		{"dt": "Item", "fieldname": "custom_donation_coupon_value"},
		"in_list_view",
		0,
	)
	frappe.clear_cache(doctype="Item")
