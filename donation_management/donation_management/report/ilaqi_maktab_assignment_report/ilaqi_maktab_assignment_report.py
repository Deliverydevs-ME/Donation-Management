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
    data = frappe.db.sql('''
        select
            assignment.ilaqi_maktab,
            detail.employee,
            detail.start_date,
            detail.end_date,
            detail.salary_cost,
            detail.status
        from `tabMaktab Employee Assignment Detail` detail
        inner join `tabMaktab Employee Assignment` assignment on assignment.name = detail.parent
        where detail.parenttype = 'Maktab Employee Assignment'
            and detail.parentfield = 'assigned_employees'
        order by assignment.ilaqi_maktab, detail.start_date desc
    ''', as_dict=True)
    return columns, data
