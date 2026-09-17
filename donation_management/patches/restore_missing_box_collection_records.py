import frappe


def execute():
	if not (
		frappe.db.table_exists("Donation Box")
		and frappe.db.table_exists("Box Collection")
	):
		return

	for box in frappe.get_all(
		"Donation Box",
		filters={"docstatus": 1},
		fields=["name", "box_number", "box_code", "donation_head", "box_shape", "status"],
	):
		if frappe.db.exists("Box Collection", {"box_number": box.name, "docstatus": ["!=", 2]}):
			continue

		latest_log = get_latest_box_log(box)
		create_missing_box_collection(box, latest_log)


def get_latest_box_log(box):
	if not frappe.db.table_exists("Box Collection Log"):
		return None

	logs = frappe.get_all(
		"Box Collection Log",
		filters={"donation_box": box.name},
		fields=[
			"name",
			"box_collection",
			"status_after",
			"location_type",
			"location_name",
			"donor_location",
			"contact",
			"staff",
			"collector",
			"collected_amount",
			"manual_receipt_date",
			"mode_of_payment",
			"payment_mode",
		],
		order_by="action_date desc, creation desc",
		limit=1,
	)
	return logs[0] if logs else None


def create_missing_box_collection(box, latest_log=None):
	status = (latest_log.status_after if latest_log else None) or box.status or "Available"
	doc = frappe.get_doc(
		{
			"doctype": "Box Collection",
			"box_number": box.name,
			"box_code": box.box_code,
			"donation_head": box.donation_head,
			"box_shape": box.box_shape,
			"status": status,
		}
	)

	if latest_log:
		if latest_log.box_collection and not frappe.db.exists("Box Collection", latest_log.box_collection):
			doc.name = latest_log.box_collection
		doc.location_type = latest_log.location_type
		doc.location_name = latest_log.location_name
		doc.donor_location = latest_log.donor_location
		doc.contact = latest_log.contact
		doc.collected_amount = latest_log.collected_amount or 0
		doc.manual_receipt_date = latest_log.manual_receipt_date
		doc.mode_of_payment = latest_log.mode_of_payment or latest_log.payment_mode
		if is_valid_mohasil(latest_log.staff):
			doc.deployment_officer = latest_log.staff
		if is_valid_mohasil(latest_log.collector):
			doc.collection_office = latest_log.collector

	doc.flags.from_donation_box = True
	doc.insert(ignore_permissions=True)
	doc.flags.ignore_permissions = True
	doc.submit()

	if box.status != status:
		frappe.db.set_value("Donation Box", box.name, "status", status, update_modified=False)


def is_valid_mohasil(employee):
	if not employee:
		return False

	employee_details = frappe.db.get_value(
		"Employee",
		employee,
		["designation", "status"],
		as_dict=True,
	)
	return bool(
		employee_details
		and employee_details.status == "Active"
		and employee_details.designation == "Mohasil"
	)
