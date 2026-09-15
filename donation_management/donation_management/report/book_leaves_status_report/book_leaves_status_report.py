import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Book"), "fieldname": "book", "fieldtype": "Link", "options": "Book", "width": 150},
		{"label": _("Book Serial No"), "fieldname": "book_serial_no", "fieldtype": "Link", "options": "Serial No", "width": 145},
		{"label": _("Receipt Number"), "fieldname": "receipt_number", "fieldtype": "Data", "width": 125},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130},
		{"label": _("Donor"), "fieldname": "donor", "fieldtype": "Link", "options": "Donor", "width": 150},
		{"label": _("Donation Order"), "fieldname": "donation_order", "fieldtype": "Link", "options": "Donation Order", "width": 165},
		{"label": _("Payment Mode"), "fieldname": "payment_mode", "fieldtype": "Link", "options": "Mode of Payment", "width": 125},
		{"label": _("Manual Receipt Date"), "fieldname": "manual_receipt_date", "fieldtype": "Date", "width": 130},
		{"label": _("Journal Entry"), "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 150},
		{"label": _("Accounting Status"), "fieldname": "accounting_status", "fieldtype": "Data", "width": 130},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("book"):
		conditions.append("leaf.book = %(book)s")
		values["book"] = filters.book
	if filters.get("book_serial_no"):
		conditions.append("leaf.book_serial_no = %(book_serial_no)s")
		values["book_serial_no"] = filters.book_serial_no
	if filters.get("status"):
		conditions.append("leaf.status = %(status)s")
		values["status"] = filters.status
	if filters.get("leaf_group") == "Unused Books":
		conditions.append("leaf.status = 'Pending'")
	elif filters.get("leaf_group") == "Partially Utilized Books":
		conditions.append("book.used_receipts > 0 and book.remaining_receipts > 0")
	elif filters.get("leaf_group") == "Books Waiting for Receiving":
		conditions.append("book.status = 'Issued'")
	elif filters.get("leaf_group") == "Remaining Leaves":
		conditions.append("leaf.status in ('Pending', 'Received', 'Returned Unused')")
	elif filters.get("leaf_group") == "Used / Cancelled / Destroyed / Pending Leaves":
		conditions.append("leaf.status in ('Used', 'Cancelled', 'Destroyed', 'Pending')")

	where_clause = "where " + " and ".join(conditions) if conditions else ""
	return frappe.db.sql(
		f"""
		select
			leaf.book,
			leaf.book_serial_no,
			leaf.receipt_number,
			leaf.status,
			leaf.donor,
			leaf.donation_order,
			leaf.payment_mode,
			leaf.manual_receipt_date,
			leaf.journal_entry,
			leaf.accounting_status
		from `tabDonation Book Leaf` leaf
		left join `tabBook` book
			on book.name = leaf.book
		{where_clause}
		order by leaf.book, cast(leaf.receipt_number as unsigned), leaf.receipt_number
		""",
		values,
		as_dict=True,
	)
