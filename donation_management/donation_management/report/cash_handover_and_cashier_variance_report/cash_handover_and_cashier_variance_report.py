import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Handover'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Cash Handover', 'width': 170},
        {'label': _('Datetime'), 'fieldname': 'handover_datetime', 'fieldtype': 'Datetime', 'width': 160},
        {'label': _('Cashier'), 'fieldname': 'cashier', 'fieldtype': 'Link', 'options': 'User', 'width': 160},
        {'label': _('Destination'), 'fieldname': 'destination', 'fieldtype': 'Data', 'width': 170},
        {'label': _('Amount'), 'fieldname': 'amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Received'), 'fieldname': 'received_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Variance'), 'fieldname': 'variance', 'fieldtype': 'Currency', 'width': 120},
    ]
	data = frappe.get_all('Donation Cash Handover', fields=['name', 'handover_datetime', 'cashier', 'destination', 'amount', 'received_amount', 'variance'], order_by='handover_datetime desc')
	return columns, data
