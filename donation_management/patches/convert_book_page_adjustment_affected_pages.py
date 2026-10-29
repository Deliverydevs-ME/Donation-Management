import frappe
from frappe.utils import cint


def execute():
	"""Move the temporary page grid back into the requested text-field format."""
	if not frappe.db.exists("DocType", "Book Page Adjustment"):
		return

	page_rows_by_adjustment = {}
	if frappe.db.table_exists("Book Page Adjustment Page"):
		for row in frappe.db.sql(
			"""
			select parent, page_no
			from `tabBook Page Adjustment Page`
			where parenttype = 'Book Page Adjustment'
				and parentfield = 'affected_page_details'
			order by parent asc, page_no asc
			""",
			as_dict=True,
		):
			page_rows_by_adjustment.setdefault(row.parent, []).append(cint(row.page_no))

	for adjustment in frappe.get_all(
		"Book Page Adjustment", fields=["name", "affected_pages", "affected_page_count"]
	):
		pages = sorted(set(page_rows_by_adjustment.get(adjustment.name, [])))
		if pages:
			selection = ",".join(str(page_no) for page_no in pages)
			count = len(pages)
		else:
			# Before page-level input existed, Affected Pages stored a page count.
			# Preserve that capacity effect for legacy records during the schema change.
			count = cint(adjustment.affected_pages)
			selection = "1-{0}".format(count) if count > 1 else str(count or "")

		frappe.db.set_value(
			"Book Page Adjustment",
			adjustment.name,
			{"affected_pages": selection, "affected_page_count": count},
			update_modified=False,
		)

	# The temporary child DocType is no longer reachable from the parent form.
	# Remove its metadata without touching historical database rows during deployment.
	frappe.db.delete("DocType", {"name": "Book Page Adjustment Page"})
