"""Move active source mappings onto operational records, then remove the obsolete DocType."""

import frappe


def execute():
	if not frappe.db.table_exists("Donation Source Account Mapping"):
		return

	mappings = {
		(row.company, row.source_type, row.donation_type): row
		for row in frappe.get_all(
			"Donation Source Account Mapping",
			fields=["company", "source_type", "donation_type", "credit_account", "cost_center"],
			limit_page_length=0,
		)
	}
	backfill_box_collection_accounts(mappings)
	backfill_coupon_assignment_accounts(mappings)

	if frappe.db.exists("DocType", "Donation Source Account Mapping"):
		frappe.delete_doc("DocType", "Donation Source Account Mapping", force=1, ignore_permissions=True)

	if frappe.db.table_exists("Donation Source Account Mapping"):
		# MariaDB treats DROP TABLE as an implicit commit. Finish Frappe's
		# migration transaction before executing the requested destructive step.
		frappe.db.commit()
		frappe.db.sql("drop table `tabDonation Source Account Mapping`")


def backfill_box_collection_accounts(mappings):
	for collection in frappe.get_all(
		"Box Collection",
		fields=["name", "company", "donation_head", "credit_account", "accounting_cost_center"],
		limit_page_length=0,
	):
		mapping = mappings.get((collection.company, "Box Collection", collection.donation_head))
		if not mapping:
			continue

		values = {}
		if not collection.credit_account and mapping.credit_account:
			values["credit_account"] = mapping.credit_account
		if not collection.accounting_cost_center and mapping.cost_center:
			values["accounting_cost_center"] = mapping.cost_center
		if values:
			frappe.db.set_value("Box Collection", collection.name, values, update_modified=False)


def backfill_coupon_assignment_accounts(mappings):
	for row in frappe.get_all(
		"Book Assignment Detail",
		filters={"parenttype": "Book Assignment", "parentfield": "assigned_books", "book_type": "Coupon Book"},
		fields=["name", "parent", "coupon_type", "credit_account"],
		limit_page_length=0,
	):
		if row.credit_account:
			continue

		company = frappe.db.get_value("Book Assignment", row.parent, "company")
		mapping = mappings.get((company, "Coupon Entry", row.coupon_type)) or mappings.get(
			(company, "Book Assignment", row.coupon_type)
		)
		if mapping and mapping.credit_account:
			frappe.db.set_value(
				"Book Assignment Detail", row.name, "credit_account", mapping.credit_account, update_modified=False
			)
