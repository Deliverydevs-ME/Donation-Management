import json

import frappe


def execute():
	setter_name = "Donation Order-main-field_order"
	value = frappe.db.get_value("Property Setter", setter_name, "value")
	if not value:
		return

	try:
		field_order = json.loads(value)
	except (TypeError, ValueError):
		return

	changed = False
	if "donation_book_leaf" not in field_order:
		serial_index = field_order.index("donation_book_serial_no") if "donation_book_serial_no" in field_order else -1
		field_order.insert(serial_index + 1, "donation_book_leaf")
		changed = True

	if "requires_esaal_e_sawab" not in field_order:
		prisoner_index = field_order.index("requires_prisoner") if "requires_prisoner" in field_order else len(field_order) - 1
		field_order.insert(prisoner_index + 1, "requires_esaal_e_sawab")
		changed = True

	if changed:
		frappe.db.set_value(
			"Property Setter",
			setter_name,
			"value",
			json.dumps(field_order),
			update_modified=False,
		)
