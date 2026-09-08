import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Cancelled On'), 'fieldname': 'modified', 'fieldtype': 'Datetime', 'width': 160},
        {'label': _('Donation Order'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 170},
        {'label': _('Donor'), 'fieldname': 'donor_name', 'fieldtype': 'Link', 'options': 'Donor', 'width': 160},
        {'label': _('Reason'), 'fieldname': 'cancellation_reason', 'fieldtype': 'Small Text', 'width': 260},
        {'label': _('Approved By'), 'fieldname': 'cancellation_approved_by', 'fieldtype': 'Link', 'options': 'User', 'width': 160},
        {'label': _('Amount'), 'fieldname': 'donation_amount', 'fieldtype': 'Currency', 'width': 120},
    ]
	data = frappe.db.sql('''
        select modified, name, donor_name, cancellation_reason, cancellation_approved_by, donation_amount
        from `tabDonation Order`
        where docstatus = 2
            and (%(from_date)s is null or date(modified) >= %(from_date)s)
            and (%(to_date)s is null or date(modified) <= %(to_date)s)
        order by modified desc
    ''', filters, as_dict=True)
	return columns, data
