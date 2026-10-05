"""Restore Esaal person links where legacy display names uniquely match a Donor."""

import frappe


def execute():
	if not frappe.db.table_exists("Esaal E Sawab Detail"):
		return

	frappe.db.sql(
		"""
		update `tabEsaal E Sawab Detail` detail
		inner join (
			select lower(trim(customer_name)) as person_label, min(name) as person_name
			from `tabDonor`
			where is_group = 0 and ifnull(customer_name, '') != ''
			group by lower(trim(customer_name))
			having count(*) = 1
		) person on person.person_label = lower(trim(detail.person_name))
		set detail.person_name = person.person_name
		where detail.person_name is not null
			and detail.person_name != person.person_name
		"""
	)

