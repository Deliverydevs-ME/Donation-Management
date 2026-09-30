import frappe


ITEM_COUPON_VALUES = "\n10\n50\n100\n500\n1000\n5000"


def execute():
	from donation_management.patches.ensure_donation_order_layout_fields import execute as ensure_donation_order_layout

	ensure_roles()
	ensure_item_coupon_value_field()
	ensure_box_shapes()
	ensure_donation_settings()
	ensure_esaal_e_sawab_purpose()
	ensure_donation_order_layout()


def ensure_roles():
	for role_name in (
		"Donation Confidential Reference User",
		"Donation Cancellation Approver",
		"Donation Manager",
		"General Secretary",
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
	if not frappe.db.exists("Donation Settings", "Donation Settings"):
		settings = frappe.new_doc("Donation Settings")
		settings.name = "Donation Settings"
		settings.insert(ignore_permissions=True)

	frappe.db.set_single_value("Donation Settings", "allow_duplicate_donor_phone", 1)


def ensure_esaal_e_sawab_purpose():
	if frappe.db.exists("Donation Purpose", "Esaal e Sawab"):
		return

	doc = frappe.get_doc(
		{
			"doctype": "Donation Purpose",
			"purpose_name": "Esaal e Sawab",
			"purpose_group": "General",
			"is_group": 0,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
