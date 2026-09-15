import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	columns = [
        {'label': _('Closing'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Closing', 'width': 160},
        {'label': _('Date'), 'fieldname': 'closing_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Prepared By'), 'fieldname': 'prepared_by', 'fieldtype': 'Link', 'options': 'User', 'width': 150},
        {'label': _('Status'), 'fieldname': 'status', 'fieldtype': 'Data', 'width': 120},
        {'label': _('Items'), 'fieldname': 'pending_items_count', 'fieldtype': 'Int', 'width': 90},
        {'label': _('Total'), 'fieldname': 'total_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Cash Handover'), 'fieldname': 'cash_handover', 'fieldtype': 'Link', 'options': 'Donation Cash Handover', 'width': 170},
    ]
	conditions = {}
	if filters.get("status"):
		conditions["status"] = filters.status
	if filters.get("prepared_by"):
		conditions["prepared_by"] = filters.prepared_by
	if filters.get("from_date"):
		conditions["closing_date"] = [">=", filters.from_date]
	if filters.get("to_date"):
		conditions.setdefault("closing_date", ["<=", filters.to_date])
		if filters.get("from_date"):
			conditions["closing_date"] = ["between", [filters.from_date, filters.to_date]]
	data = frappe.get_all('Donation Closing', filters=conditions, fields=['name', 'closing_date', 'prepared_by', 'status', 'pending_items_count', 'total_amount', 'cash_handover'], order_by='closing_date desc, creation desc')
	return columns, data


def validate_filters(filters):
	if filters.get("from_date") and filters.get("to_date") and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
