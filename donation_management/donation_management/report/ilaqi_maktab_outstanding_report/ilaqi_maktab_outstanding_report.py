import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Due Date'), 'fieldname': 'due_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Due Amount'), 'fieldname': 'due_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Collected'), 'fieldname': 'collected_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Outstanding'), 'fieldname': 'outstanding_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Status'), 'fieldname': 'status', 'fieldtype': 'Data', 'width': 120},
    ]
    data = frappe.get_all('Maktab Payment Schedule', filters={'docstatus':['!=',2], 'outstanding_amount':['>',0]}, fields=['ilaqi_maktab','due_date','due_amount','collected_amount','outstanding_amount','status'], order_by='due_date asc')
    return columns, data
