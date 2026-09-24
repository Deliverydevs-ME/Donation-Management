import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Ilaqi Maktab'), 'fieldname': 'ilaqi_maktab', 'fieldtype': 'Link', 'options': 'Ilaqi Maktab', 'width': 180},
        {'label': _('Due'), 'fieldname': 'due_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Collected'), 'fieldname': 'collected_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Salary'), 'fieldname': 'salary_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Allowances'), 'fieldname': 'allowance_amount', 'fieldtype': 'Currency', 'width': 120},
        {'label': _('Employee Expenses'), 'fieldname': 'employee_expense_amount', 'fieldtype': 'Currency', 'width': 140},
        {'label': _('Operational Expenses'), 'fieldname': 'operational_expense_amount', 'fieldtype': 'Currency', 'width': 150},
        {'label': _('Other Expenses'), 'fieldname': 'other_expense_amount', 'fieldtype': 'Currency', 'width': 130},
        {'label': _('Total Maktab Expenses'), 'fieldname': 'expense_amount', 'fieldtype': 'Currency', 'width': 160},
        {'label': _('Net Position'), 'fieldname': 'net_position', 'fieldtype': 'Currency', 'width': 130},
    ]
	data = frappe.db.sql('''
        select m.name as ilaqi_maktab,
            ifnull(s.due_amount, 0) due_amount,
            ifnull(p.collected_amount, 0) collected_amount,
            ifnull(e.salary_amount, 0) salary_amount,
            ifnull(e.allowance_amount, 0) allowance_amount,
            ifnull(e.employee_expense_amount, 0) employee_expense_amount,
            ifnull(e.operational_expense_amount, 0) operational_expense_amount,
            ifnull(e.other_expense_amount, 0) other_expense_amount,
            ifnull(e.expense_amount, 0) expense_amount,
            ifnull(p.collected_amount, 0) - ifnull(e.expense_amount, 0) net_position
        from `tabIlaqi Maktab` m
        left join (select ilaqi_maktab, sum(due_amount) due_amount from `tabMaktab Payment Schedule` group by ilaqi_maktab) s on s.ilaqi_maktab = m.name
        left join (select ilaqi_maktab, sum(amount) collected_amount from `tabMaktab Payment` where docstatus = 1 group by ilaqi_maktab) p on p.ilaqi_maktab = m.name
        left join (
            select
                ilaqi_maktab,
                sum(case when expense_category = 'Salary' then amount else 0 end) salary_amount,
                sum(case when expense_category = 'Allowances' then amount else 0 end) allowance_amount,
                sum(case when expense_category = 'Employee Expenses' then amount else 0 end) employee_expense_amount,
                sum(case when ifnull(expense_category, 'Operational Expenses') = 'Operational Expenses' then amount else 0 end) operational_expense_amount,
                sum(case when expense_category = 'Other' then amount else 0 end) other_expense_amount,
                sum(amount) expense_amount
            from `tabMaktab Expense`
            where docstatus = 1
            group by ilaqi_maktab
        ) e on e.ilaqi_maktab = m.name
        order by m.name
    ''', filters, as_dict=True)
	return columns, data
