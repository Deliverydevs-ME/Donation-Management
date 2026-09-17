import frappe


def execute():
	remove_donation_book_leaf_donor_requirement()
	remove_donation_book_custody_transfer()


def remove_donation_book_leaf_donor_requirement():
	property_setter = "Donation Book Leaf-donor-reqd"
	if frappe.db.exists("Property Setter", property_setter):
		frappe.delete_doc(
			"Property Setter",
			property_setter,
			ignore_permissions=True,
			force=True,
		)


def remove_donation_book_custody_transfer():
	if not frappe.db.exists("DocType", "Donation Book Custody Transfer"):
		return

	frappe.delete_doc(
		"DocType",
		"Donation Book Custody Transfer",
		ignore_permissions=True,
		force=True,
	)
