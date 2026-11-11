import frappe
from frappe.utils.nestedset import rebuild_tree


SPONSORSHIP_PURPOSES = {
	"Sponsorship - Student": {
		"requires_student": 1,
		"requires_prisoner": 0,
		"sources": (
			"Sponsorship - Hifz - Student",
			"Sponsorship - Nazra - Student - Physical",
			"Sponsorship - Nazra - Student - Online",
		),
	},
	"Sponsorship - Prisoner": {
		"requires_student": 0,
		"requires_prisoner": 1,
		"sources": (
			"Sponsorship - Hifz - Prisoner",
			"Sponsorship - Nazra - Prisoner",
		),
	},
	"Sponsorship - MTC": {
		"requires_student": 0,
		"requires_prisoner": 0,
		"sources": ("Sponsorship - MTC",),
	},
	"Sponsorship - Maktab": {
		"requires_student": 0,
		"requires_prisoner": 0,
		"sources": ("Sponsorship - Maktab / Justuju",),
	},
}


def execute():
	ensure_sponsorship_parent()
	for purpose_name, settings in SPONSORSHIP_PURPOSES.items():
		doc = get_or_create_purpose(purpose_name)
		doc.parent_donation_purpose = "Sponsorship"
		doc.is_group = 0
		doc.purpose_group = "Sponsorship"
		doc.requires_student = settings["requires_student"]
		doc.requires_prisoner = settings["requires_prisoner"]
		doc.student_mode = None
		copy_account_mappings(doc, settings["sources"])
		doc.save(ignore_permissions=True)

	rebuild_tree("Donation Purpose", "parent_donation_purpose")


def ensure_sponsorship_parent():
	if frappe.db.exists("Donation Purpose", "Sponsorship"):
		parent = frappe.get_doc("Donation Purpose", "Sponsorship")
	else:
		parent = frappe.new_doc("Donation Purpose")
		parent.purpose_name = "Sponsorship"

	parent.parent_donation_purpose = None
	parent.is_group = 1
	parent.purpose_group = "Sponsorship"
	parent.requires_student = 0
	parent.requires_prisoner = 0
	parent.student_mode = None
	parent.save(ignore_permissions=True)


def get_or_create_purpose(purpose_name):
	if frappe.db.exists("Donation Purpose", purpose_name):
		return frappe.get_doc("Donation Purpose", purpose_name)

	doc = frappe.new_doc("Donation Purpose")
	doc.purpose_name = purpose_name
	return doc


def copy_account_mappings(target_doc, source_purposes):
	existing = {(row.company, row.donation_type) for row in target_doc.get("account_mappings", [])}
	for source in source_purposes:
		if source == target_doc.name or not frappe.db.exists("Donation Purpose", source):
			continue

		for mapping in frappe.get_all(
			"Donation Purpose Account Mapping",
			filters={"parent": source},
			fields=["company", "donation_type", "credit_account", "cost_center"],
			order_by="idx",
		):
			key = (mapping.company, mapping.donation_type)
			if key in existing:
				continue

			target_doc.append(
				"account_mappings",
				{
					"company": mapping.company,
					"donation_type": mapping.donation_type,
					"credit_account": mapping.credit_account,
					"cost_center": mapping.cost_center,
				},
			)
			existing.add(key)
