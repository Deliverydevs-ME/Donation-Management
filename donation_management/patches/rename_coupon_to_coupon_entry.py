"""Rename the app-owned Coupon transaction without losing existing entries."""

import frappe


def execute():
	old_name = "Coupon"
	new_name = "Coupon Entry"

	if frappe.db.exists("DocType", old_name) and not frappe.db.exists("DocType", new_name):
		frappe.rename_doc("DocType", old_name, new_name, force=True)
	elif frappe.db.table_exists(old_name) and not frappe.db.table_exists(new_name):
		# This branch protects installations where the metadata was removed but
		# the historical transaction table still exists.
		frappe.db.sql("RENAME TABLE `tabCoupon` TO `tabCoupon Entry`")

	_update_link_options(old_name, new_name)


def _update_link_options(old_name, new_name):
	if not frappe.db.table_exists("DocField"):
		return

	frappe.db.sql(
		"""
		update `tabDocField`
		set options = %(new_name)s
		where fieldtype = 'Link' and options = %(old_name)s
		""",
		{"old_name": old_name, "new_name": new_name},
	)
