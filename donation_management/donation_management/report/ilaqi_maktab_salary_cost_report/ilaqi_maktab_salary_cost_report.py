import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Active Employees'), 'fieldname': 'employees', 'fieldtype': 'Int', 'width': 120},
        {'label': _('Monthly Salary/Cost'), 'fieldname': 'salary_cost', 'fieldtype': 'Currency', 'width': 150},
    ]
    data = frappe.db.sql('''
        select ilaqi_maktab, count(*) employees, sum(salary_cost) salary_cost
        from `tabMaktab Employee Assignment`
        where status = 'Active'
        group by ilaqi_maktab
        order by ilaqi_maktab
    ''', as_dict=True)
    return columns, data
