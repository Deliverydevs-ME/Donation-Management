import frappe
from frappe.utils import getdate

from donation_management.donation_management.doctype.book_assignment.book_assignment import (
	create_book_issue_stock_entry,
	has_submitted_book_stock_entry,
)


def execute():
	"""Create missing issue entries for active legacy Book Assignments."""
	for name in frappe.get_all(
		"Book Assignment",
		filters={"docstatus": 1, "status": ["in", ("Issued", "Returned", "Closed")]},
		pluck="name",
	):
		doc = frappe.get_doc("Book Assignment", name)
		if has_submitted_book_stock_entry(doc.stock_entry):
			continue
		if doc.status == "Returned" and not doc.is_exhausted():
			# Its legacy stock was never issued, so the returned book is already
			# correctly available in its original warehouse.
			continue

		try:
			create_book_issue_stock_entry(doc, posting_date=getdate(doc.start_date or doc.creation))
		except Exception:
			frappe.log_error(
				title="Book Assignment stock ledger backfill failed",
				message=frappe.get_traceback(),
			)
