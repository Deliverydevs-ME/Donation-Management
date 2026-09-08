import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
        {'label': _('Book'), 'fieldname': 'book', 'fieldtype': 'Link', 'options': 'Book', 'width': 160},
        {'label': _('Book Serial No'), 'fieldname': 'book_serial_no', 'fieldtype': 'Link', 'options': 'Serial No', 'width': 150},
        {'label': _('Receipt Number'), 'fieldname': 'receipt_number', 'fieldtype': 'Data', 'width': 130},
        {'label': _('Status'), 'fieldname': 'status', 'fieldtype': 'Data', 'width': 140},
        {'label': _('Donor'), 'fieldname': 'donor', 'fieldtype': 'Link', 'options': 'Donor', 'width': 160},
        {'label': _('Donation Order'), 'fieldname': 'donation_order', 'fieldtype': 'Link', 'options': 'Donation Order', 'width': 170},
    ]
	data = frappe.get_all('Donation Book Leaf', fields=['book', 'book_serial_no', 'receipt_number', 'status', 'donor', 'donation_order'], order_by='book, receipt_number')
	return columns, data
