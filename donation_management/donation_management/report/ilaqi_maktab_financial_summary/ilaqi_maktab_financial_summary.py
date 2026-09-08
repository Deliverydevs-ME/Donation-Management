import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Due'), 'fieldname': 'due_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Collected'), 'fieldname': 'collected_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Expenses'), 'fieldname': 'expense_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Net Position'), 'fieldname': 'net_position', 'fieldtype': 'Currency', 'width': 130},
    ]
	data = frappe.db.sql('''
        select m.name as ilaqi_maktab,
            ifnull(s.due_amount, 0) due_amount,
            ifnull(p.collected_amount, 0) collected_amount,
            ifnull(e.expense_amount, 0) expense_amount,
            ifnull(p.collected_amount, 0) - ifnull(e.expense_amount, 0) net_position
        from `tabIlaqi Maktab` m
        left join (select ilaqi_maktab, sum(due_amount) due_amount from `tabMaktab Payment Schedule` group by ilaqi_maktab) s on s.ilaqi_maktab = m.name
        left join (select ilaqi_maktab, sum(amount) collected_amount from `tabMaktab Payment` where docstatus = 1 group by ilaqi_maktab) p on p.ilaqi_maktab = m.name
        left join (select ilaqi_maktab, sum(amount) expense_amount from `tabMaktab Expense` where docstatus = 1 group by ilaqi_maktab) e on e.ilaqi_maktab = m.name
        order by m.name
    ''', filters, as_dict=True)
	return columns, data
