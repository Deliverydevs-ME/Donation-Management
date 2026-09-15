import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	return get_columns(), get_data(filters)


def validate_filters(filters):
	if filters.get("from_date") and filters.get("to_date") and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
	return [
		{"label": _("Assignment"), "fieldname": "assignment", "fieldtype": "Link", "options": "Donation Location Assignment", "width": 165},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 145},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 170},
		{"label": _("Donation Location"), "fieldname": "donation_location", "fieldtype": "Link", "options": "Donation Location", "width": 170},
		{"label": _("Location Type"), "fieldname": "location_type", "fieldtype": "Link", "options": "Location Type", "width": 130},
		{"label": _("Address"), "fieldname": "address", "fieldtype": "Small Text", "width": 220},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 105},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 105},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("employee"):
		conditions.append("assignment.employee = %(employee)s")
		values["employee"] = filters.employee
	if filters.get("donation_location"):
		conditions.append("assignment.donation_location = %(donation_location)s")
		values["donation_location"] = filters.donation_location
	if filters.get("status"):
		conditions.append("assignment.status = %(status)s")
		values["status"] = filters.status
	if filters.get("from_date"):
		conditions.append("ifnull(assignment.end_date, '9999-12-31') >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("assignment.start_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	where_clause = " and " + " and ".join(conditions) if conditions else ""
	return frappe.db.sql(
		f"""
		select
			assignment.name as assignment,
			assignment.employee,
			employee.employee_name,
			assignment.donation_location,
			location.location_type,
			location.address,
			assignment.start_date,
			assignment.end_date,
			assignment.status
		from `tabDonation Location Assignment` assignment
		left join `tabEmployee` employee
			on employee.name = assignment.employee
		left join `tabDonation Location` location
			on location.name = assignment.donation_location
		where assignment.docstatus != 2
			{where_clause}
		order by assignment.start_date desc, assignment.employee
		""",
		values,
		as_dict=True,
	)
