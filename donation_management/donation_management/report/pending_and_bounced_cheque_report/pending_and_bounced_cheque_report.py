import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Donation Order'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 170},
        {'label': _('Cheque Number'), 'fieldname': 'cheque_number', 'fieldtype': 'Data', 'width': 130},
        {'label': _('Deposit Date'), 'fieldname': 'cheque_deposit_date', 'fieldtype': 'Date', 'width': 120},
        {'label': _('PDC Status'), 'fieldname': 'pdc_status', 'fieldtype': 'Data', 'width': 140},
        {'label': _('Instrument Status'), 'fieldname': 'instrument_status', 'fieldtype': 'Data', 'width': 150},
        {'label': _('Amount'), 'fieldname': 'donation_amount', 'fieldtype': 'Currency', 'width': 120},
    ]
	data = frappe.db.sql('''
        select name, cheque_number, cheque_deposit_date, pdc_status, instrument_status, donation_amount
        from `tabDonation Order`
        where docstatus != 2 and mode_of_payment = 'Cheque'
            and (pdc_status in ('Pending Deposit') or instrument_status in ('Pending Encashment', 'Bounced/Rejected'))
        order by cheque_deposit_date asc
    ''', filters, as_dict=True)
	return columns, data
