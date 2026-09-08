import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Posting Date'), 'fieldname': 'posting_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Expense Type'), 'fieldname': 'expense_type', 'fieldtype': 'Data', 'width': 150},
        {'label': _('Amount'), 'fieldname': 'amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Journal Entry'), 'fieldname': 'journal_entry', 'fieldtype': 'Link', 'options': 'Journal Entry', 'width': 160},
    ]
    data = frappe.get_all('Maktab Expense', fields=['ilaqi_maktab','posting_date','expense_type','amount','journal_entry'], order_by='posting_date desc, creation desc')
    return columns, data
