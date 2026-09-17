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
		conditions.append("coalesce(collection.status, latest_log.status_after) = %(status)s")
		values["status"] = filters.status
	if filters.get("donation_box_location"):
		conditions.append("collection.donation_box_location = %(donation_box_location)s")
		values["donation_box_location"] = filters.donation_box_location
	if filters.get("mohasil"):
		conditions.append(
			"""(
				box.mohasil = %(mohasil)s
				or collection.deployment_officer = %(mohasil)s
				or collection.collection_office = %(mohasil)s
				or latest_log.staff = %(mohasil)s
				or latest_log.collector = %(mohasil)s
			)"""
		)
		values["mohasil"] = filters.mohasil

	where_clause = " and " + " and ".join(conditions) if conditions else ""
	return frappe.db.sql(
		f"""
		select
			base.box_number,
			base.box_code,
			base.status,
			base.location_name,
			base.location_address,
			base.location_type,
			base.territory,
			base.issue_date,
			base.last_collection_date,
			base.last_received_date,
			base.responsible_person,
			base.mohasil,
			base.zone_manager,
			case
				when base.status in ('Closed', 'Cancelled', 'Available', 'Received', 'Returned') then 0
				when base.issue_date is null then 0
				else datediff(%(today)s, base.issue_date)
			end as days_outstanding
		from (
		select
			coalesce(collection.box_number, latest_log.donation_box) as box_number,
			coalesce(collection.box_code, latest_log.box_code, box.box_code) as box_code,
			coalesce(collection.status, latest_log.status_after) as status,
			coalesce(location.location_name, collection.location_name, latest_log.location_name) as location_name,
			coalesce(location.address, collection.donor_location, latest_log.donor_location) as location_address,
			coalesce(location.location_type, collection.location_type, latest_log.location_type) as location_type,
			coalesce(location.territory, box.territory) as territory,
			coalesce(collection.assignment_date, issue_log.issue_date) as issue_date,
			coalesce(collection.collection_date, collection_log.collection_date) as last_collection_date,
			coalesce(collection.received_on, received_log.received_on) as last_received_date,
			coalesce(location.responsible_person, collection.contact, collection.care_of_donor, collection.care_of_trustee) as responsible_person,
			coalesce(box.mohasil, collection.collection_office, collection.deployment_officer, latest_log.collector, latest_log.staff) as mohasil,
			coalesce(location.zone_manager, box.zone_manager) as zone_manager
		from (
			select name as box_collection
			from `tabBox Collection`
			union
			select box_collection
			from `tabBox Collection Log`
			where ifnull(box_collection, '') != ''
		) source
		left join `tabBox Collection` collection
			on collection.name = source.box_collection
		left join (
			select log.*
			from `tabBox Collection Log` log
			inner join (
				select box_collection, max(action_date) as action_date
				from `tabBox Collection Log`
				where ifnull(box_collection, '') != ''
				group by box_collection
			) latest
				on latest.box_collection = log.box_collection
				and latest.action_date = log.action_date
		) latest_log
			on latest_log.box_collection = source.box_collection
		left join (
			select box_collection, max(action_date) as issue_date
			from `tabBox Collection Log`
			where action in ('Issuance', 'Reissuance', 'Issue', 'Reissue')
			group by box_collection
		) issue_log
			on issue_log.box_collection = source.box_collection
		left join (
			select box_collection, max(action_date) as collection_date
			from `tabBox Collection Log`
			where action in ('Collection', 'Collected', 'Under Collection')
			group by box_collection
		) collection_log
			on collection_log.box_collection = source.box_collection
		left join (
			select box_collection, max(action_date) as received_on
			from `tabBox Collection Log`
			where action in ('Receive', 'Received')
			group by box_collection
		) received_log
			on received_log.box_collection = source.box_collection
		left join `tabDonation Box` box
			on box.name = coalesce(collection.box_number, latest_log.donation_box)
		left join `tabDonation Box Location` location
			on location.name = collection.donation_box_location
		where coalesce(collection.box_number, latest_log.donation_box) is not null
			{where_clause}
		) base
		order by days_outstanding desc, base.issue_date desc, base.box_number
		""",
		values,
		as_dict=True,
	)
