import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Action Date'), 'fieldname': 'action_date', 'fieldtype': 'Datetime', 'width': 160},
        {'label': _('Box Collection'), 'fieldname': 'box_collection', 'fieldtype': 'Link', 'options': 'Box Collection', 'width': 170},
        {'label': _('Action'), 'fieldname': 'action', 'fieldtype': 'Data', 'width': 120},
        {'label': _('Location'), 'fieldname': 'location_name', 'fieldtype': 'Data', 'width': 180},
        {'label': _('Collector'), 'fieldname': 'collector', 'fieldtype': 'Link', 'options': 'Employee', 'width': 160},
        {'label': _('Amount'), 'fieldname': 'collected_amount', 'fieldtype': 'Currency', 'width': 120},
    ]
	data = frappe.get_all('Box Collection Log', fields=['action_date', 'box_collection', 'action', 'location_name', 'collector', 'collected_amount'], order_by='action_date desc')
	return columns, data
