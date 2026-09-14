import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	normalise_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)
	return columns, data, None, None, report_summary


def normalise_filters(filters):
	if not filters.get("from_date"):
		filters.from_date = today()
	if not filters.get("to_date"):
		filters.to_date = filters.from_date

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{
			"label": _("Donation Order"),
			"fieldname": "donation_order",
			"fieldtype": "Link",
			"options": "Donation Order",
			"width": 155,
		},
		{"label": _("Receipt No"), "fieldname": "receipt_number", "fieldtype": "Data", "width": 120},
		{
			"label": _("Location"),
			"fieldname": "donation_location",
			"fieldtype": "Link",
			"options": "Donation Location",
			"width": 160,
		},
		{
			"label": _("Cashier/Collector"),
			"fieldname": "collector",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
		{"label": _("Donor"), "fieldname": "donor_name", "fieldtype": "Link", "options": "Donor", "width": 150},
		{"label": _("Donor Classification"), "fieldname": "donor_classification", "fieldtype": "Data", "width": 145},
		{"label": _("Program/Fund"), "fieldname": "program_fund", "fieldtype": "Data", "width": 190},
		{"label": _("Payment Mode"), "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 120},
		{"label": _("Receipt Status"), "fieldname": "receipt_status", "fieldtype": "Data", "width": 120},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select
			date(donation_order.donation_posting_date) as posting_date,
			donation_order.name as donation_order,
			coalesce(
				nullif(purpose.manual_receipt_number, ''),
				nullif(donation_order.manual_receipt_number, ''),
				nullif(donation_order.computerized_receipt, ''),
				donation_order.name
			) as receipt_number,
			coalesce(donation_order.donation_location, donation_order.location) as donation_location,
			donation_order.mohasil as collector,
			donation_order.donor_name,
			coalesce(nullif(donor.registration_classification, ''), donor.customer_type) as donor_classification,
			coalesce(nullif(purpose.donation_purpose, ''), nullif(purpose.purpose_path, ''), nullif(purpose.donation_category, ''), donation_order.donation_purpose, donation_order.purpose_of_donation) as program_fund,
			donation_order.mode_of_payment,
			donation_order.receipt_status,
			ifnull(purpose.amount, donation_order.donation_amount) as amount
		from `tabDonation Order` donation_order
		left join `tabDonor` donor
			on donor.name = donation_order.donor_name
		left join `tabDonation Order Purpose Detail` purpose
			on purpose.parent = donation_order.name
			and purpose.parenttype = 'Donation Order'
			and purpose.parentfield = 'purpose_details'
		where donation_order.docstatus = 1
			{conditions}
		order by posting_date desc, donation_order.creation desc, purpose.idx asc
		""",
		filters,
		as_dict=True,
	)

	for row in rows:
		row.amount = flt(row.amount)
		row.program_fund = row.program_fund or _("Unspecified")
		row.donor_classification = row.donor_classification or _("Unspecified")
		row.receipt_status = row.receipt_status or _("Pending")
	return rows


def get_conditions(filters):
	conditions = [
		"date(donation_order.donation_posting_date) >= %(from_date)s",
		"date(donation_order.donation_posting_date) <= %(to_date)s",
	]
	if filters.get("donation_location"):
		conditions.append("coalesce(donation_order.donation_location, donation_order.location) = %(donation_location)s")
	if filters.get("collector"):
		conditions.append("donation_order.mohasil = %(collector)s")
	if filters.get("mode_of_payment"):
		conditions.append("donation_order.mode_of_payment = %(mode_of_payment)s")
	if filters.get("donor_classification"):
		conditions.append("coalesce(nullif(donor.registration_classification, ''), donor.customer_type) = %(donor_classification)s")
	if filters.get("program_fund"):
		conditions.append(
			"""coalesce(
				nullif(purpose.donation_purpose, ''),
				nullif(purpose.purpose_path, ''),
				nullif(purpose.donation_category, ''),
				donation_order.donation_purpose,
				donation_order.purpose_of_donation
			) = %(program_fund)s"""
		)
	return " and " + " and ".join(conditions)


def get_report_summary(data):
	receipts = {row.donation_order for row in data}
	locations = {row.donation_location for row in data if row.donation_location}
	return [
		{"label": _("Total Amount"), "value": sum(flt(row.amount) for row in data), "indicator": "Green", "datatype": "Currency"},
		{"label": _("Donation Orders"), "value": len(receipts), "indicator": "Blue", "datatype": "Int"},
		{"label": _("Locations"), "value": len(locations), "indicator": "Gray", "datatype": "Int"},
	]
