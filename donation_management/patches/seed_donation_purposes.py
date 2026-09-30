import frappe
from frappe.utils.nestedset import rebuild_tree


PURPOSES = [
	("General", None, 1, "General", 0, 0, None),
	("General - Orphan Aid", "General", 1, "General", 0, 0, None),
	("General - Orphan Aid - Ration Reserve", "General - Orphan Aid", 0, "General", 0, 0, None),
	("General - Orphan Aid - Personage", "General - Orphan Aid", 0, "General", 0, 0, None),
	("General - Food", "General", 0, "General", 0, 0, None),
	("General - Relief", "General", 0, "General", 0, 0, None),
	("Esaal e Sawab", None, 0, "General", 0, 0, None),
	("Sponsorship", None, 1, "Sponsorship", 0, 0, None),
	("Sponsorship - Student", "Sponsorship", 0, "Sponsorship", 1, 0, None),
	("Sponsorship - Prisoner", "Sponsorship", 0, "Sponsorship", 0, 1, None),
	("Sponsorship - MTC", "Sponsorship", 0, "Sponsorship", 0, 0, None),
	("Sponsorship - Maktab", "Sponsorship", 0, "Sponsorship", 0, 0, None),
	("Sponsorship - Nazra", "Sponsorship", 1, "Sponsorship", 0, 0, None),
	("Sponsorship - Nazra - Student", "Sponsorship - Nazra", 1, "Sponsorship", 0, 0, None),
	("Sponsorship - Nazra - Student - Physical", "Sponsorship - Nazra - Student", 0, "Sponsorship", 1, 0, "Physical"),
	("Sponsorship - Nazra - Student - Online", "Sponsorship - Nazra - Student", 0, "Sponsorship", 1, 0, "Online"),
	("Sponsorship - Nazra - Prisoner", "Sponsorship - Nazra", 0, "Sponsorship", 0, 1, None),
	("Sponsorship - Hifz", "Sponsorship", 1, "Sponsorship", 0, 0, None),
	("Sponsorship - Hifz - Student", "Sponsorship - Hifz", 0, "Sponsorship", 1, 0, None),
	("Sponsorship - Hifz - Prisoner", "Sponsorship - Hifz", 0, "Sponsorship", 0, 1, None),
	("Sponsorship - MTC", "Sponsorship", 0, "Sponsorship", 0, 0, None),
	("Sponsorship - Maktab / Justuju", "Sponsorship", 0, "Sponsorship", 0, 0, None),
	("Others", None, 1, "Others", 0, 0, None),
	("Others - Fidya", "Others", 0, "Others", 0, 0, None),
	("Others - Fitra", "Others", 0, "Others", 0, 0, None),
	("Others - Charm e Qurbani", "Others", 0, "Others", 0, 0, None),
	("Welfare", None, 1, "Welfare", 0, 0, None),
	("Welfare - Ration", "Welfare", 0, "Welfare", 0, 0, None),
	("Welfare - Flood Rehab", "Welfare", 0, "Welfare", 0, 0, None),
	("Welfare - Release of Prisoner", "Welfare", 0, "Welfare", 0, 1, None),
	("Welfare - Masajid", "Welfare", 0, "Welfare", 0, 0, None),
]


def execute():
	for purpose_name, parent, is_group, purpose_group, requires_student, requires_prisoner, student_mode in PURPOSES:
		if frappe.db.exists("Donation Purpose", purpose_name):
			doc = frappe.get_doc("Donation Purpose", purpose_name)
		else:
			doc = frappe.new_doc("Donation Purpose")
			doc.purpose_name = purpose_name

		doc.parent_donation_purpose = parent
		doc.is_group = is_group
		doc.purpose_group = purpose_group
		doc.requires_student = requires_student
		doc.requires_prisoner = requires_prisoner
		doc.student_mode = student_mode
		doc.flags.ignore_permissions = True
		doc.save()

	rebuild_tree("Donation Purpose", "parent_donation_purpose")
