import frappe


def validate_unique_field(doc, fieldname, label=None, value=None):
	value = value if value is not None else doc.get(fieldname)
	if value in (None, ""):
		return

	existing = frappe.db.exists(
		doc.doctype,
		{
			fieldname: value,
			"name": ["!=", doc.name],
		},
	)
	if not existing:
		return

	frappe.throw(
		frappe._("{0} {1} already exists in {2} {3}.").format(
			frappe._(label or doc.meta.get_label(fieldname) or fieldname),
			value,
			doc.doctype,
			existing,
		),
		title=frappe._("Duplicate {0}").format(frappe._(label or doc.meta.get_label(fieldname) or fieldname)),
	)
