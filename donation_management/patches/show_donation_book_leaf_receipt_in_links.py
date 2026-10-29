import frappe


def execute():
	"""Show the manual receipt number, rather than the generated leaf ID, in Link fields."""
	frappe.db.set_value("DocType", "Donation Book Leaf", "show_title_field_in_link", 1, update_modified=False)
	frappe.clear_cache(doctype="Donation Book Leaf")
