import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Box Number"), "fieldname": "box_number", "fieldtype": "Link", "options": "Donation Box", "width": 150},
		{"label": _("Box Code"), "fieldname": "box_code", "fieldtype": "Data", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Location"), "fieldname": "location_name", "fieldtype": "Data", "width": 170},
		{"label": _("Location Address"), "fieldname": "location_address", "fieldtype": "Small Text", "width": 220},
		{"label": _("Location Type"), "fieldname": "location_type", "fieldtype": "Link", "options": "Location Type", "width": 130},
		{"label": _("Territory/Zone"), "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 135},
		{"label": _("Issue Date"), "fieldname": "issue_date", "fieldtype": "Date", "width": 110},
		{"label": _("Last Collection Date"), "fieldname": "last_collection_date", "fieldtype": "Date", "width": 135},
		{"label": _("Last Received Date"), "fieldname": "last_received_date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Responsible Person"), "fieldname": "responsible_person", "fieldtype": "Data", "width": 155},
		{"label": _("Mohasil"), "fieldname": "mohasil", "fieldtype": "Link", "options": "Employee", "width": 140},
		{"label": _("Zone/Territory Manager"), "fieldname": "zone_manager", "fieldtype": "Link", "options": "Employee", "width": 170},
		{"label": _("Days Outstanding"), "fieldname": "days_outstanding", "fieldtype": "Int", "width": 130},
	]


def get_data(filters):
	conditions = []
	values = {"today": today()}
	if filters.get("status"):
		conditions.append("collection.status = %(status)s")
		values["status"] = filters.status
	if filters.get("donation_location"):
		conditions.append("collection.donation_location = %(donation_location)s")
		values["donation_location"] = filters.donation_location
	if filters.get("mohasil"):
		conditions.append("(box.mohasil = %(mohasil)s or collection.deployment_officer = %(mohasil)s or collection.collection_office = %(mohasil)s)")
		values["mohasil"] = filters.mohasil

	where_clause = " and " + " and ".join(conditions) if conditions else ""
	return frappe.db.sql(
		f"""
		select
			collection.box_number,
			collection.box_code,
			collection.status,
			coalesce(location.shophouse_name, collection.location_name, location.location_name) as location_name,
			coalesce(collection.donor_location, location.address) as location_address,
			coalesce(collection.location_type, location.location_type) as location_type,
			coalesce(location.territory, box.territory) as territory,
			collection.assignment_date as issue_date,
			collection.collection_date as last_collection_date,
			collection.received_on as last_received_date,
			coalesce(location.responsible_person, collection.contact, collection.care_of_donor, collection.care_of_trustee) as responsible_person,
			coalesce(box.mohasil, collection.collection_office, collection.deployment_officer) as mohasil,
			coalesce(location.zone_manager, box.zone_manager) as zone_manager,
			case
				when collection.status in ('Closed', 'Cancelled', 'Available', 'Received', 'Returned') then 0
				when collection.assignment_date is null then 0
				else datediff(%(today)s, collection.assignment_date)
			end as days_outstanding
		from `tabBox Collection` collection
		left join `tabDonation Box` box
			on box.name = collection.box_number
		left join `tabDonation Location` location
			on location.name = collection.donation_location
		where collection.docstatus != 2
			{where_clause}
		order by days_outstanding desc, collection.modified desc
		""",
		values,
		as_dict=True,
	)
