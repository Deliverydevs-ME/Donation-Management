import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Closing'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Closing', 'width': 160},
        {'label': _('Date'), 'fieldname': 'closing_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Prepared By'), 'fieldname': 'prepared_by', 'fieldtype': 'Link', 'options': 'User', 'width': 150},
        {'label': _('Status'), 'fieldname': 'status', 'fieldtype': 'Data', 'width': 120},
        {'label': _('Items'), 'fieldname': 'pending_items_count', 'fieldtype': 'Int', 'width': 90},
        {'label': _('Total'), 'fieldname': 'total_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Cash Handover'), 'fieldname': 'cash_handover', 'fieldtype': 'Link', 'options': 'Donation Cash Handover', 'width': 170},
    ]
	data = frappe.get_all('Donation Closing', fields=['name', 'closing_date', 'prepared_by', 'status', 'pending_items_count', 'total_amount', 'cash_handover'], order_by='closing_date desc, creation desc')
	return columns, data
