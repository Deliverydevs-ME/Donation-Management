import json

import frappe

from donation_management.patches.ensure_book_assignment_connections import (
	ensure_purchase_source_link,
)
from donation_management.patches.ensure_enhancement_customizations import (
	ensure_esaal_e_sawab_purpose,
)


def execute():
	ensure_purchase_source_link(
		"Material Request",
		"material_request_type",
		"Optional donation-management link for requested books.",
	)
	ensure_purchase_source_link(
		"Purchase Receipt",
		"supplier",
		"Optional donation-management link for purchased books.",
	)
	ensure_esaal_e_sawab_purpose()

	if frappe.db.exists("DocType", "Donation Book Leaf"):
		frappe.db.set_value("DocType", "Donation Book Leaf", "is_submittable", 1, update_modified=False)

	for setter_name in (
		"Donation Book Leaf-donation_order-reqd",
		"Donation Book Leaf-returned_amount-hidden",
		"Donation Book Leaf-returned_amount-read_only",
	):
		if frappe.db.exists("Property Setter", setter_name):
			frappe.delete_doc("Property Setter", setter_name, force=True, ignore_permissions=True)

	remove_doctype_link("Donation Book Leaf", "Donation Order")
	remove_doctype_link("Donation Order", "Donation Book Leaf")

	field_order_setter = "Donation Book Leaf-main-field_order"
	field_order = frappe.db.get_value("Property Setter", field_order_setter, "value")
	if field_order:
		try:
			fields = json.loads(field_order)
		except (TypeError, ValueError):
			fields = []
		if "returned_amount" in fields:
			fields.remove("returned_amount")
			frappe.db.set_value(
				"Property Setter",
				field_order_setter,
				"value",
				json.dumps(fields),
				update_modified=False,
			)


def remove_doctype_link(parent, link_doctype):
	if not frappe.db.table_exists("DocType Link"):
		return

	frappe.db.delete(
		"DocType Link",
		{"parent": parent, "link_doctype": link_doctype},
	)
