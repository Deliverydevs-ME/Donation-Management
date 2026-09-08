# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime


CONFIDENTIAL_ROLES = {
	"Donation Confidential Reference User",
	"Donation Manager",
	"System Manager",
}


def has_confidential_access(user=None):
	user_roles = set(frappe.get_roles(user))
	return bool(user_roles.intersection(CONFIDENTIAL_ROLES))


def log_confidential_access(doc, fieldname=None, access_type="Read", remarks=None):
	if not frappe.db.table_exists("Donation Confidential Access Log"):
		return

	frappe.get_doc(
		{
			"doctype": "Donation Confidential Access Log",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"fieldname": fieldname,
			"access_type": access_type,
			"accessed_by": frappe.session.user,
			"accessed_on": now_datetime(),
			"remarks": remarks,
		}
	).insert(ignore_permissions=True)


def log_confidential_changes(doc, fieldnames):
	if doc.is_new():
		for fieldname in fieldnames:
			if doc.get(fieldname):
				log_confidential_access(doc, fieldname, "Create")
		return

	previous = doc.get_doc_before_save()
	if not previous:
		return

	for fieldname in fieldnames:
		if (previous.get(fieldname) or "") == (doc.get(fieldname) or ""):
			continue
		access_type = "Update" if doc.get(fieldname) else "Clear"
		log_confidential_access(doc, fieldname, access_type)


@frappe.whitelist()
def get_confidential_reference(doctype, name, fieldname):
	if doctype not in ("Donor", "Donation Order"):
		frappe.throw(frappe._("Confidential access is not enabled for {0}.").format(doctype))

	if fieldname not in ("party", "referred_by_trustee", "confidential_ref_co"):
		frappe.throw(frappe._("Field {0} is not a confidential reference field.").format(fieldname))

	if not has_confidential_access():
		frappe.throw(frappe._("You are not allowed to access confidential donor references."))

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	log_confidential_access(doc, fieldname, "Read")
	return doc.get(fieldname)
