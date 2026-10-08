"""Preserve existing Donation Closing to Cash Handover references as a two-way link."""

import frappe


def execute():
	if not frappe.db.has_column("Donation Cash Handover", "donation_closing"):
		return

	for closing in frappe.get_all(
		"Donation Closing",
		filters={"cash_handover": ["is", "set"]},
		fields=["name", "cash_handover"],
		limit_page_length=0,
	):
		if not frappe.db.get_value("Donation Cash Handover", closing.cash_handover, "donation_closing"):
			frappe.db.set_value(
				"Donation Cash Handover",
				closing.cash_handover,
				"donation_closing",
				closing.name,
				update_modified=False,
			)
