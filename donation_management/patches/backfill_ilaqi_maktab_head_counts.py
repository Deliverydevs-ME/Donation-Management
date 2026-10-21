import frappe

from donation_management.donation_management.doctype.ilaqi_maktab.ilaqi_maktab import (
	sync_head_count,
)


def execute():
	for ilaqi_maktab in frappe.get_all("Ilaqi Maktab", pluck="name"):
		sync_head_count(ilaqi_maktab)
