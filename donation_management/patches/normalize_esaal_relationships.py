import frappe


def execute():
	legacy_values = {
		"Dada": "Grand Father",
		"Dadi": "Grand Mother",
		"Nana": "Grand Father",
		"Nani": "Grand Mother",
	}
	for old_value, new_value in legacy_values.items():
		frappe.db.sql(
			"""
			update `tabEsaal E Sawab Detail`
			set relationship = %s
			where relationship = %s
			""",
			(new_value, old_value),
		)
