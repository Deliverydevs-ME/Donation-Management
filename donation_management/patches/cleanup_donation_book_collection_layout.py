import frappe


def execute():
	"""Remove an obsolete exported layout override for Donation Book Collection."""
	custom_field = "Donation Book Collection-custom_section_break_o5mxt"
	property_setter = "Donation Book Collection-main-field_order"

	if frappe.db.exists("Custom Field", custom_field):
		frappe.delete_doc("Custom Field", custom_field, force=1, ignore_permissions=True)
	if frappe.db.exists("Property Setter", property_setter):
		frappe.delete_doc("Property Setter", property_setter, force=1, ignore_permissions=True)

	frappe.clear_cache(doctype="Donation Book Collection")
