import frappe
from frappe import _


def execute(filters=None):
    columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Expected'), 'fieldname': 'expected_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Actual'), 'fieldname': 'actual_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Variance'), 'fieldname': 'variance', 'fieldtype': 'Currency', 'width': 130},
    ]
    data = frappe.db.sql('''
        select m.name ilaqi_maktab,
            ifnull(s.expected_amount, 0) expected_amount,
            ifnull(p.actual_amount, 0) actual_amount,
            ifnull(p.actual_amount, 0) - ifnull(s.expected_amount, 0) variance
        from `tabIlaqi Maktab` m
        left join (select ilaqi_maktab, sum(due_amount) expected_amount from `tabMaktab Payment Schedule` where docstatus != 2 group by ilaqi_maktab) s on s.ilaqi_maktab = m.name
        left join (select ilaqi_maktab, sum(amount) actual_amount from `tabMaktab Payment` where docstatus = 1 group by ilaqi_maktab) p on p.ilaqi_maktab = m.name
        order by m.name
    ''', as_dict=True)
    return columns, data
