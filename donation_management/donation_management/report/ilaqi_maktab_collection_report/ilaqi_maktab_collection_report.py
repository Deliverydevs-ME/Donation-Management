import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Collected'), 'fieldname': 'collected_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Advance'), 'fieldname': 'advance_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Payments'), 'fieldname': 'payments', 'fieldtype': 'Int', 'width': 100},
    ]
    data = frappe.db.sql('''
        select ilaqi_maktab, sum(amount) collected_amount, sum(advance_amount) advance_amount, count(*) payments
        from `tabMaktab Payment`
        where docstatus = 1
        group by ilaqi_maktab
        order by ilaqi_maktab
    ''', as_dict=True)
    return columns, data
