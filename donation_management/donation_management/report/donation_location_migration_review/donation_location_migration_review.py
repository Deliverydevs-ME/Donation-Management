import frappe
from frappe import _


def execute(filters=None):
	columns = [
		{'label': _('Donation Order'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 170},
		{'label': _('Legacy Location'), 'fieldname': 'location', 'fieldtype': 'Link', 'options': 'Location Type', 'width': 170},
		{'label': _('Donation Location'), 'fieldname': 'donation_location', 'fieldtype': 'Link', 'options': 'Donation Location', 'width': 170},
		{'label': _('Mohasil'), 'fieldname': 'mohasil', 'fieldtype': 'Link', 'options': 'Employee', 'width': 160},
		{'label': _('Posting Date'), 'fieldname': 'donation_posting_date', 'fieldtype': 'Datetime', 'width': 160},
	]
	data = frappe.db.sql('''
		select name, location, donation_location, mohasil, donation_posting_date
		from `tabDonation Order`
		where ifnull(location, '') != '' and ifnull(donation_location, '') = ''
		order by donation_posting_date desc
	''', as_dict=True)
	return columns, data
