import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Donation Box'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Box', 'width': 160},
        {'label': _('Box Code'), 'fieldname': 'box_code', 'fieldtype': 'Data', 'width': 130},
        {'label': _('Donation Head'), 'fieldname': 'donation_head', 'fieldtype': 'Data', 'width': 130},
        {'label': _('Shape'), 'fieldname': 'box_shape', 'fieldtype': 'Link', 'options': 'Box Shape', 'width': 130},
        {'label': _('Status'), 'fieldname': 'status', 'fieldtype': 'Data', 'width': 120},
        {'label': _('Mohasil'), 'fieldname': 'mohasil', 'fieldtype': 'Link', 'options': 'Employee', 'width': 160},
    ]
	data = frappe.get_all('Donation Box', fields=['name', 'box_code', 'donation_head', 'box_shape', 'status', 'mohasil'], order_by='modified desc')
	return columns, data
