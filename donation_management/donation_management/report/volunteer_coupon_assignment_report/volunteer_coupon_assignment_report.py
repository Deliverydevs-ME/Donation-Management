import frappe
from frappe import _
from frappe.utils import cint, flt


COUPON_TYPES = ("Zakat", "Atiya", "Fitra", "Fidya")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Volunteer"), "fieldname": "volunteer_name", "fieldtype": "Link", "options": "Employee", "width": 180},
		{"label": _("Coupon Type"), "fieldname": "coupon_type", "fieldtype": "Data", "width": 130},
		{"label": _("Assigned Books"), "fieldname": "assigned_books", "fieldtype": "Int", "width": 130},
		{"label": _("Total Pages"), "fieldname": "total_pages", "fieldtype": "Int", "width": 120},
		{"label": _("Used Pages"), "fieldname": "used_pages", "fieldtype": "Int", "width": 120},
		{"label": _("Remaining Pages"), "fieldname": "remaining_pages", "fieldtype": "Int", "width": 140},
		{"label": _("Collected Amount"), "fieldname": "collected_amount", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	conditions = {"book_type": "Coupon Book"}
	if filters.get("volunteer_name"):
		conditions["volunteer_name"] = filters.volunteer_name
	if filters.get("coupon_type"):
		conditions["coupon_type"] = filters.coupon_type

	books = frappe.get_all(
		"Book Assignment",
		filters=conditions,
		fields=[
			"volunteer_name",
			"coupon_type",
			"total_pages",
			"used_pages",
			"remaining_pages",
			"collected_amount",
		],
	)

	volunteers = sorted({book.volunteer_name for book in books if book.volunteer_name})
	if filters.get("volunteer_name") and filters.volunteer_name not in volunteers:
		volunteers.append(filters.volunteer_name)
	if not volunteers:
		volunteers = [filters.get("volunteer_name") or ""]

	report_rows = {
		(volunteer, coupon_type): {
			"volunteer_name": volunteer,
			"coupon_type": coupon_type,
			"assigned_books": 0,
			"total_pages": 0,
			"used_pages": 0,
			"remaining_pages": 0,
			"collected_amount": 0,
		}
		for volunteer in volunteers
		for coupon_type in COUPON_TYPES
		if not filters.get("coupon_type") or coupon_type == filters.coupon_type
	}

	for book in books:
		key = (book.volunteer_name, book.coupon_type)
		if key not in report_rows:
			report_rows[key] = {
				"volunteer_name": book.volunteer_name,
				"coupon_type": book.coupon_type,
				"assigned_books": 0,
				"total_pages": 0,
				"used_pages": 0,
				"remaining_pages": 0,
				"collected_amount": 0,
			}

		row = report_rows[key]
		row["assigned_books"] += 1
		row["total_pages"] += cint(book.total_pages)
		row["used_pages"] += cint(book.used_pages)
		row["remaining_pages"] += cint(book.remaining_pages)
		row["collected_amount"] += flt(book.collected_amount)

	return sorted(report_rows.values(), key=lambda row: (row["volunteer_name"] or "", row["coupon_type"]))
