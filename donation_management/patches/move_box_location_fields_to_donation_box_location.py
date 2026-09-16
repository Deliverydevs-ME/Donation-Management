import frappe


BOX_LOCATION_FIELDS = (
	"territory",
	"zone_manager",
	"responsible_person",
	"care_of_trustee",
	"care_of_donor",
)


def execute():
	if not frappe.db.table_exists("Donation Box Location"):
		return

	create_box_locations_from_legacy_donation_locations()
	backfill_box_collection_locations()


def create_box_locations_from_legacy_donation_locations():
	columns = get_existing_donation_location_columns()
	select_fields = [
		"name",
		"location_name",
		"location_type",
		"address",
		"contact_person",
	]
	select_fields.extend(field for field in BOX_LOCATION_FIELDS if field in columns)

	locations = frappe.db.sql(
		f"""
		select {", ".join(select_fields)}
		from `tabDonation Location`
		where ifnull(location_name, '') != ''
		""",
		as_dict=True,
	)

	for location in locations:
		location_name = location.location_name or location.name
		if not location_name or not location.location_type or frappe.db.exists("Donation Box Location", location_name):
			continue

		doc = frappe.new_doc("Donation Box Location")
		doc.location_name = location_name
		doc.location_type = location.location_type
		doc.address = location.address
		doc.responsible_person = location.get("responsible_person") or location.get("contact_person")
		doc.territory = location.get("territory")
		doc.zone_manager = location.get("zone_manager")
		doc.care_of_trustee = location.get("care_of_trustee")
		doc.care_of_donor = location.get("care_of_donor")
		doc.insert(ignore_permissions=True)


def backfill_box_collection_locations():
	if not frappe.db.has_column("Box Collection", "donation_box_location"):
		return

	frappe.db.sql(
		"""
		update `tabBox Collection` collection
		inner join `tabDonation Box Location` box_location
			on box_location.name = collection.donation_location
		set collection.donation_box_location = box_location.name
		where ifnull(collection.donation_box_location, '') = ''
			and ifnull(collection.donation_location, '') != ''
		"""
	)


def get_existing_donation_location_columns():
	return set(frappe.db.get_table_columns("Donation Location"))
