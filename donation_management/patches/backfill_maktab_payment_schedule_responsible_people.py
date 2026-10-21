import frappe

from donation_management.donation_management.doctype.maktab_payment_schedule.maktab_payment_schedule import (
	get_employee_name,
)


def execute():
	for schedule in frappe.get_all(
		"Maktab Payment Schedule", fields=["name", "ilaqi_maktab"]
	):
		responsible_person = frappe.db.get_value(
			"Ilaqi Maktab", schedule.ilaqi_maktab, "responsible_person"
		)
		frappe.db.set_value(
			"Maktab Payment Schedule",
			schedule.name,
			"custom_responsible_person",
			get_employee_name(responsible_person),
			update_modified=False,
		)
