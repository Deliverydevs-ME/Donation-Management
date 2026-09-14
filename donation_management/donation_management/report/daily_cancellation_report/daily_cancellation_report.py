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
		{"label": _("Cancelled On"), "fieldname": "cancelled_on", "fieldtype": "Datetime", "width": 155},
		{
			"label": _("Document No"),
			"fieldname": "donation_order",
			"fieldtype": "Link",
			"options": "Donation Order",
			"width": 155,
		},
		{"label": _("Receipt No"), "fieldname": "receipt_number", "fieldtype": "Data", "width": 130},
		{"label": _("Donor"), "fieldname": "donor_name", "fieldtype": "Link", "options": "Donor", "width": 150},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Donation Date/Time"), "fieldname": "donation_datetime", "fieldtype": "Datetime", "width": 155},
		{"label": _("Cancelled By"), "fieldname": "cancelled_by", "fieldtype": "Link", "options": "User", "width": 145},
		{"label": _("Reason"), "fieldname": "reason", "fieldtype": "Small Text", "width": 260},
		{"label": _("Approval Reference"), "fieldname": "approval_reference", "fieldtype": "Data", "width": 230},
		{
			"label": _("Replacement Document"),
			"fieldname": "replacement_document",
			"fieldtype": "Link",
			"options": "Donation Order",
			"width": 165,
		},
		{"label": _("Receipt Status"), "fieldname": "receipt_status", "fieldtype": "Data", "width": 120},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select
			donation_order.modified as cancelled_on,
			donation_order.name as donation_order,
			coalesce(
				nullif(donation_order.computerized_receipt, ''),
				nullif(donation_order.manual_receipt_number, ''),
				donation_order.name
			) as receipt_number,
			donation_order.donor_name,
			donation_order.donation_amount as amount,
			donation_order.donation_posting_date as donation_datetime,
			donation_order.modified_by as cancelled_by,
			donation_order.cancellation_reason as reason,
			donation_order.cancellation_status,
			donation_order.cancellation_approved_by,
			donation_order.cancellation_approved_on,
			donation_order.replacement_donation_order as replacement_document,
			donation_order.receipt_status
		from `tabDonation Order` donation_order
		where donation_order.docstatus = 2
			{conditions}
		order by donation_order.modified desc
		""",
		filters,
		as_dict=True,
	)

	for row in rows:
		row.amount = flt(row.amount)
		row.approval_reference = get_approval_reference(row)
		row.receipt_status = row.receipt_status or _("Cancelled")
	return rows


def get_conditions(filters):
	conditions = [
		"date(donation_order.modified) >= %(from_date)s",
		"date(donation_order.modified) <= %(to_date)s",
	]
	if filters.get("donor"):
		conditions.append("donation_order.donor_name = %(donor)s")
	if filters.get("cancelled_by"):
		conditions.append("donation_order.modified_by = %(cancelled_by)s")
	return " and " + " and ".join(conditions)


def get_approval_reference(row):
	parts = []
	if row.cancellation_status:
		parts.append(row.cancellation_status)
	if row.cancellation_approved_by:
		parts.append(_("Approved by {0}").format(row.cancellation_approved_by))
	if row.cancellation_approved_on:
		parts.append(frappe.format_value(row.cancellation_approved_on, {"fieldtype": "Datetime"}))
	return " | ".join(parts)


def get_report_summary(data):
	return [
		{"label": _("Cancelled Amount"), "value": sum(flt(row.amount) for row in data), "indicator": "Red", "datatype": "Currency"},
		{"label": _("Cancelled Documents"), "value": len({row.donation_order for row in data}), "indicator": "Orange", "datatype": "Int"},
	]
