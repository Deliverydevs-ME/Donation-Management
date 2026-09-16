import frappe


def execute():
	if not frappe.db.has_column("Donation Order", "donor_primary_address"):
		return

	frappe.db.sql(
		"""
		update `tabDonation Order` donation_order
		inner join `tabDonor` donor on donor.name = donation_order.donor_name
		set donation_order.donor_primary_address = donor.primary_address
		where ifnull(donation_order.donor_name, '') != ''
		"""
	)
