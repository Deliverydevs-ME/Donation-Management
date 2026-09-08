import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Manual Receipt'), 'fieldname': 'manual_receipt_number', 'fieldtype': 'Data', 'width': 150},
        {'label': _('Manual Date'), 'fieldname': 'manual_receipt_date', 'fieldtype': 'Date', 'width': 120},
        {'label': _('Donation Order'), 'fieldname': 'name', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 170},
        {'label': _('Computerized Receipt'), 'fieldname': 'computerized_receipt', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 180},
        {'label': _('Status'), 'fieldname': 'manual_receipt_reconciliation_status', 'fieldtype': 'Data', 'width': 150},
        {'label': _('Amount'), 'fieldname': 'donation_amount', 'fieldtype': 'Currency', 'width': 120},
    ]
	data = frappe.db.sql('''
        select manual_receipt_number, manual_receipt_date, name, computerized_receipt,
            manual_receipt_reconciliation_status, donation_amount
        from `tabDonation Order`
        where ifnull(manual_receipt_number, '') != ''
        order by manual_receipt_date desc, creation desc
    ''', filters, as_dict=True)
	return columns, data
