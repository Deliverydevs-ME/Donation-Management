import frappe


def execute():
	ensure_purchase_source_link("Material Request", "material_request_type", "Optional donation-management link for requested books.")
	ensure_purchase_source_link("Purchase Receipt", "supplier", "Optional donation-management link for purchased books.")


def ensure_purchase_source_link(doctype, insert_after, description):
	if not frappe.db.exists("DocType", doctype):
		return

	if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": "custom_book_assignment"}):
		return

	field = {
		"doctype": "Custom Field",
		"dt": doctype,
		"fieldname": "custom_book_assignment",
		"fieldtype": "Link",
		"label": "Book Assignment",
		"options": "Book Assignment",
		"description": description,
	}
	if frappe.get_meta(doctype).has_field(insert_after):
		field["insert_after"] = insert_after
	frappe.get_doc(field).insert(ignore_permissions=True)
