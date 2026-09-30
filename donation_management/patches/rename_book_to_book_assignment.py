"""Rename the app-owned Book transaction to Book Assignment safely."""

import frappe


def execute():
	if frappe.db.exists("DocType", "Book") and not frappe.db.exists("DocType", "Book Assignment"):
		frappe.rename_doc("DocType", "Book", "Book Assignment", force=True)

	if frappe.db.exists("DocType", "Book Return Collection") and not frappe.db.exists(
		"DocType", "Legacy Book Return Collection"
	):
		# Keep historical rows auditable while removing the old child DocType from the active workflow.
		frappe.rename_doc("DocType", "Book Return Collection", "Legacy Book Return Collection", force=True)

	_update_historical_source_values()


def _update_historical_source_values():
	if frappe.db.table_exists("Donation Closing Detail"):
		frappe.db.sql(
			"""
			update `tabDonation Closing Detail`
			set source_doctype = 'Book Assignment'
			where source_doctype = 'Book'
			"""
		)

	if frappe.db.table_exists("Donation Source Account Mapping"):
		frappe.db.sql(
			"""
			update `tabDonation Source Account Mapping`
			set source_type = 'Book Assignment'
			where source_type = 'Book'
			"""
		)

	if frappe.db.table_exists("Book Assignment Detail"):
		frappe.db.sql(
			"""
			update `tabBook Assignment Detail`
			set parenttype = 'Book Assignment'
			where parenttype = 'Book'
			"""
		)
