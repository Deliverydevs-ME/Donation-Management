import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Date'), 'fieldname': 'posting_date', 'fieldtype': 'Date', 'width': 110},
        {'label': _('Source'), 'fieldname': 'source_type', 'fieldtype': 'Data', 'width': 140},
        {'label': _('Document'), 'fieldname': 'source_name', 'fieldtype': 'Dynamic Link', 'options': 'source_type', 'width': 170},
        {'label': _('Donation Location'), 'fieldname': 'donation_location', 'fieldtype': 'Data', 'width': 170},
        {'label': _('Collector'), 'fieldname': 'collector', 'fieldtype': 'Data', 'width': 140},
        {'label': _('Mode of Payment'), 'fieldname': 'mode_of_payment', 'fieldtype': 'Data', 'width': 130},
        {'label': _('Amount'), 'fieldname': 'amount', 'fieldtype': 'Currency', 'width': 130},
    ]
	data = frappe.db.sql('''
        select date(donation_posting_date) posting_date, 'Donation Order' source_type, name source_name,
            coalesce(donation_location, location) donation_location, mohasil collector, mode_of_payment, donation_amount amount
        from `tabDonation Order`
        where docstatus = 1
            and (%(from_date)s is null or date(donation_posting_date) >= %(from_date)s)
            and (%(to_date)s is null or date(donation_posting_date) <= %(to_date)s)
        order by posting_date desc, creation desc
    ''', filters, as_dict=True)
	return columns, data
