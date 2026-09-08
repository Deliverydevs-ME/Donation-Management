import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Payment Schedule'), 'fieldname': 'payment_schedule', 'fieldtype': 'Link', 'options': 'Maktab Payment Schedule', 'width': 180},
        {'label': _('Donation Order'), 'fieldname': 'donation_order', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 160},
        {'label': _('Posting Date'), 'fieldname': 'posting_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Amount'), 'fieldname': 'amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Advance'), 'fieldname': 'advance_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Status'), 'fieldname': 'docstatus', 'fieldtype': 'Int', 'width': 80},
    ]
    data = frappe.get_all('Maktab Payment', fields=['ilaqi_maktab','payment_schedule','donation_order','posting_date','amount','advance_amount','docstatus'], order_by='posting_date desc, creation desc')
    return columns, data
