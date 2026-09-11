import frappe


AUDIT_FIELDS = ("requesting_user", "request_date")


def execute():
	frappe.reload_doc("donation_management", "doctype", "donor")
	remove_hidden_property_setters()
	ensure_docfields_visible()
	frappe.clear_cache(doctype="Donor")


def remove_hidden_property_setters():
	property_setters = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": "Donor",
			"field_name": ["in", AUDIT_FIELDS],
			"property": "hidden",
			"value": ["in", ("1", 1)],
		},
		pluck="name",
	)

	for property_setter in property_setters:
		frappe.delete_doc("Property Setter", property_setter, ignore_permissions=True, force=True)


def ensure_docfields_visible():
	for fieldname in AUDIT_FIELDS:
		field = frappe.db.get_value(
			"DocField",
			{"parent": "Donor", "fieldname": fieldname},
			"name",
		)
		if not field:
			continue

		frappe.db.set_value(
			"DocField",
			field,
			{
				"hidden": 0,
				"read_only": 1,
				"print_hide": 1,
			},
			update_modified=False,
		)
