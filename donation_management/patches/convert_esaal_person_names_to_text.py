"""Convert legacy Esaal e Sawab Donor links to their display names."""

import frappe


def execute():
	if not frappe.db.table_exists("Esaal E Sawab Detail"):
		return

	frappe.db.sql(
		"""
		update `tabEsaal E Sawab Detail` detail
		inner join `tabDonor` donor on donor.name = detail.person_name
		set detail.person_name = coalesce(nullif(donor.customer_name, ''), donor.name)
		where detail.person_name is not null
		"""
	)
