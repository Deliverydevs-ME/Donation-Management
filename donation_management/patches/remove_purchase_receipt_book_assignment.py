import frappe


def execute():
	"""Remove the obsolete Book Assignment link from the standard Purchase Receipt form."""
	for field in frappe.get_all(
		"Custom Field",
		filters={"dt": "Purchase Receipt", "fieldname": "custom_book_assignment"},
		pluck="name",
	):
		frappe.delete_doc("Custom Field", field, ignore_permissions=True)

	for setter in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Purchase Receipt", "field_name": "custom_book_assignment"},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", setter, ignore_permissions=True)
