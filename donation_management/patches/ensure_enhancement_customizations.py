import frappe


ITEM_COUPON_VALUES = "\n10\n50\n100\n500\n1000\n5000"


def execute():
	ensure_roles()
	ensure_item_coupon_value_field()
	ensure_box_shapes()
	ensure_donation_settings()


def ensure_roles():
	for role_name in (
		"Donation Confidential Reference User",
		"Donation Cancellation Approver",
		"Donation Manager",
	):
		if frappe.db.exists("Role", role_name):
			continue

		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)


def ensure_item_coupon_value_field():
	fieldname = "custom_donation_coupon_value"
	if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": fieldname}):
		return

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Item",
			"fieldname": fieldname,
			"fieldtype": "Select",
			"label": "Donation Coupon Value",
			"options": ITEM_COUPON_VALUES,
			"insert_after": "item_group",
			"description": "Used by Donation Management coupon/book workflows.",
		}
	).insert(ignore_permissions=True)


def ensure_box_shapes():
	for shape_name in ("Square", "Triangle", "Trapezium"):
		if frappe.db.exists("Box Shape", shape_name):
			continue

		frappe.get_doc(
			{
				"doctype": "Box Shape",
				"shape_name": shape_name,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)


def ensure_donation_settings():
	if frappe.db.exists("Donation Settings", "Donation Settings"):
		return

	settings = frappe.new_doc("Donation Settings")
	settings.name = "Donation Settings"
	settings.insert(ignore_permissions=True)
