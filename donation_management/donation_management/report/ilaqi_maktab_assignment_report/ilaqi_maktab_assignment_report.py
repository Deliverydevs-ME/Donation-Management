import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Employee'), 'fieldname': 'employee', 'fieldtype': 'Link', 'options': 'Employee', 'width': 160},
        {'label': _('Start Date'), 'fieldname': 'start_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('End Date'), 'fieldname': 'end_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Salary/Cost'), 'fieldname': 'salary_cost', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Status'), 'fieldname': 'status', 'fieldtype': 'Data', 'width': 110},
    ]
    data = frappe.get_all('Maktab Employee Assignment', fields=['ilaqi_maktab','employee','start_date','end_date','salary_cost','status'], order_by='ilaqi_maktab, start_date desc')
    return columns, data
