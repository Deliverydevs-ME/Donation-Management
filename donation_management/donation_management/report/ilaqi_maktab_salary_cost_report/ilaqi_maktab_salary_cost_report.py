import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Active Employees'), 'fieldname': 'employees', 'fieldtype': 'Int', 'width': 120},
        {'label': _('Monthly Salary/Cost'), 'fieldname': 'salary_cost', 'fieldtype': 'Currency', 'width': 150},
    ]
    data = frappe.db.sql('''
        select assignment.ilaqi_maktab, count(detail.name) employees, sum(detail.salary_cost) salary_cost
        from `tabMaktab Employee Assignment Detail` detail
        inner join `tabMaktab Employee Assignment` assignment on assignment.name = detail.parent
        where detail.parenttype = 'Maktab Employee Assignment'
            and detail.parentfield = 'assigned_employees'
            and detail.status = 'Active'
        group by assignment.ilaqi_maktab
        order by assignment.ilaqi_maktab
    ''', as_dict=True)
    return columns, data
