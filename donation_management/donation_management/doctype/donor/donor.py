# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.utils import now_datetime
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet

from donation_management.donation_management.doctype.donation_settings.donation_settings import (
	is_donor_contact_required,
	is_duplicate_donor_phone_allowed,
)


VALID_DONOR_TYPES = (
	"Walk-in",
	"Refered by Trustee",
	"Key Donor",
	"Sub General Donor",
	"General Donor",
	"Sub Key Donor",
)
GROUP_DONOR_TYPES = ("General Donor", "Key Donor", "Sub Key Donor")
TRUSTEE_BRANCH = "Branch:Refered by Trustee"
DONOR_TYPE_BRANCH_PREFIX = "Branch:Donor Type:"
DONOR_NODE_PREFIX = "Donor:"
TRUSTEE_NODE_PREFIX = "Trustee:"
DONOR_TREE_BRANCH_TYPES = (
	"Walk-in",
	"General Donor",
	"Key Donor",
	"Sub General Donor",
	"Sub Key Donor",
)
MOHASIL_DESIGNATION = "Mohasil"


class Donor(NestedSet):
	nsm_parent_field = "parent_donor"

	def validate(self):
		self.set_naming_series()
		self.set_donor_type()
		self.set_group_for_donor_type()
		self.set_trustee_reference()
		self.validate_parent_donor()
		self.set_donor_phone_digits()
		self.set_donor_email()
		self.validate_contact_details()
		self.validate_donor_email_format()
		self.validate_unique_donor_phone()
		self.validate_phone_not_used_by_trustee()
		self.validate_unique_donor_email()
		self.validate_mohasil()
		self.set_whatsapp_digits()
		self.set_donor_information_request_audit()

	def on_update(self):
		super().on_update()
		self.log_confidential_reference_changes()

	def set_donor_type(self):
		if self.customer_type not in VALID_DONOR_TYPES:
			frappe.throw(
				frappe._("Donor Type must be one of: {0}.").format(
					", ".join(VALID_DONOR_TYPES)
				)
			)

	def set_group_for_donor_type(self):
		if self.customer_type in GROUP_DONOR_TYPES:
			self.is_group = 1

	def set_naming_series(self):
		if self.is_new() and self.naming_series != "DONOR-.YYYY.-":
			self.naming_series = "DONOR-.YYYY.-"

	def set_trustee_reference(self):
		if self.customer_type != "Refered by Trustee":
			self.referred_by_trustee = None
			return

		self.parent_donor = None

		if not self.referred_by_trustee:
			frappe.throw(frappe._("Referred By Trustee is required."))

		if self.referred_by_trustee == self.name:
			frappe.throw(frappe._("Referred By Trustee cannot refer to the same Donor."))

		trustee = frappe.db.exists("Trustee", self.referred_by_trustee)
		if not trustee:
			frappe.throw(frappe._("Referred By Trustee {0} was not found.").format(self.referred_by_trustee))

		if not frappe.db.get_value("Trustee", self.referred_by_trustee, "is_group"):
			frappe.throw(frappe._("Referred By Trustee must be checked as Is Group."))

	def set_donor_phone_digits(self):
		if self.donor_phone_number:
			self.donor_phone_digits = normalize_phone(self.donor_phone_number) or None
		elif not self.donor_phone_digits:
			self.donor_phone_digits = None

	def set_donor_email(self):
		if self.donor_email:
			self.donor_email = self.donor_email.strip().lower()

	def validate_donor_email_format(self):
		if not self.donor_email:
			return

		if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", self.donor_email):
			frappe.throw(frappe._("Donor Email must be a valid email address and include @."))

	def validate_contact_details(self):
		if not is_donor_contact_required():
			return

		if not self.donor_phone_digits and not self.donor_email:
			frappe.throw(frappe._("Either Donor Phone Number or Donor Email is required."))

	def validate_unique_donor_email(self):
		if not self.donor_email:
			return

		existing_donor = frappe.db.exists(
			"Donor",
			{
				"donor_email": self.donor_email,
				"name": ["!=", self.name],
			},
		)
		if existing_donor:
			frappe.throw(
				frappe._("Donor Email {0} is already used by Donor {1}.").format(
					self.donor_email,
					existing_donor,
				)
			)

	def validate_unique_donor_phone(self):
		if is_duplicate_donor_phone_allowed():
			return

		if not self.donor_phone_digits:
			return

		existing_donor = frappe.db.exists(
			"Donor",
			{
				"donor_phone_digits": self.donor_phone_digits,
				"name": ["!=", self.name],
			},
		)
		if existing_donor:
			frappe.throw(
				frappe._("Donor Phone Number {0} is already used by Donor {1}.").format(
					self.donor_phone_number,
					existing_donor,
				)
			)

	def validate_phone_not_used_by_trustee(self):
		if not self.donor_phone_digits:
			return

		existing_trustee = find_trustee_by_phone_digits(self.donor_phone_digits)
		if existing_trustee:
			frappe.throw(
				frappe._("Donor Phone Number {0} is already used by Trustee {1}.").format(
					self.donor_phone_number,
					existing_trustee,
				)
			)

	def validate_parent_donor(self):
		if not self.parent_donor:
			return

		if self.parent_donor == self.name:
			frappe.throw(frappe._("Parent Donor cannot be the same Donor."))

		if not frappe.db.exists("Donor", self.parent_donor):
			frappe.throw(frappe._("Parent Donor {0} was not found.").format(self.parent_donor))

		if not frappe.db.get_value("Donor", self.parent_donor, "is_group"):
			frappe.throw(frappe._("Parent Donor must be checked as Is Group."))

		parent = self.parent_donor
		while parent:
			if parent == self.name:
				frappe.throw(frappe._("Circular Donor hierarchy is not allowed."))

			parent = frappe.db.get_value("Donor", parent, "parent_donor")

	def validate_mohasil(self):
		if not self.mohasil:
			return

		validate_mohasil_employee(self.mohasil, "Mohasil")

	def set_whatsapp_digits(self):
		if self.whatsapp_number:
			self.whatsapp_number_digits = normalize_phone(self.whatsapp_number) or None
		else:
			self.whatsapp_number_digits = None

	def set_donor_information_request_audit(self):
		if not self.donor_information_request_status:
			self.requesting_user = None
			self.request_date = None
			return

		previous = self.get_doc_before_save()
		if previous and previous.donor_information_request_status == self.donor_information_request_status:
			return

		self.requesting_user = frappe.session.user
		self.request_date = now_datetime()

	def log_confidential_reference_changes(self):
		try:
			from donation_management.donation_management.confidential import log_confidential_changes

			log_confidential_changes(self, ("party", "referred_by_trustee", "confidential_ref_co"))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Donor confidential access logging failed")


def normalize_cnic(cnic):
	cnic = re.sub(r"\D", "", cnic or "")
	if len(cnic) != 13:
		frappe.throw(frappe._("Donor CNIC must contain 13 digits."))

	return f"{cnic[:5]}-{cnic[5:12]}-{cnic[12]}"


def normalize_phone(phone_number):
	return re.sub(r"\D", "", phone_number or "")


def find_trustee_by_phone_digits(phone_digits, exclude=None):
	if not phone_digits or not frappe.db.table_exists("Trustee"):
		return None

	trustee_meta = frappe.get_meta("Trustee")
	if trustee_meta.has_field("contact_digits"):
		existing_trustee = frappe.db.exists(
			"Trustee",
			{
				"contact_digits": phone_digits,
				"name": ["!=", exclude or ""],
			},
		)
		if existing_trustee:
			return existing_trustee

	for trustee in frappe.get_all(
		"Trustee",
		filters={"name": ["!=", exclude or ""]},
		fields=["name", "contact"],
	):
		if normalize_phone(trustee.contact) == phone_digits:
			return trustee.name

	return None


def validate_mohasil_employee(employee, label):
	employee_details = frappe.db.get_value(
		"Employee",
		employee,
		["designation", "status"],
		as_dict=True,
	)
	if not employee_details:
		frappe.throw(frappe._("{0} must be a valid Employee.").format(label))
	if employee_details.status != "Active":
		frappe.throw(frappe._("{0} must be an Active Employee.").format(label))
	if employee_details.designation != MOHASIL_DESIGNATION:
		frappe.throw(
			frappe._("{0} must be an Employee with designation {1}.").format(
				label,
				MOHASIL_DESIGNATION,
			)
		)


@frappe.whitelist()
def get_referral_tree_children(doctype, parent=None, **kwargs):
	frappe.has_permission("Donor", "read", throw=True)
	frappe.has_permission("Trustee", "read", throw=True)

	if not parent or parent == "Donations":
		nodes = [_get_donor_type_branch_node(donor_type) for donor_type in DONOR_TREE_BRANCH_TYPES]
		nodes.insert(
			1,
			{
				"value": TRUSTEE_BRANCH,
				"title": frappe._("Refered by Trustee"),
				"expandable": _has_trustee_branch_nodes(),
				"hide_open": True,
			},
		)
		return nodes

	if parent.startswith(DONOR_TYPE_BRANCH_PREFIX):
		donor_type = parent[len(DONOR_TYPE_BRANCH_PREFIX) :]
		return _get_top_level_donor_nodes(donor_type)

	if parent == TRUSTEE_BRANCH:
		return _get_top_level_trustee_nodes()

	if parent.startswith(DONOR_NODE_PREFIX):
		return _get_child_donor_nodes(parent[len(DONOR_NODE_PREFIX) :])

	if parent.startswith(TRUSTEE_NODE_PREFIX):
		return _get_trustee_children(parent[len(TRUSTEE_NODE_PREFIX) :])

	return []


def _get_donor_type_branch_node(donor_type):
	return {
		"value": f"{DONOR_TYPE_BRANCH_PREFIX}{donor_type}",
		"title": frappe._(donor_type),
		"expandable": _has_donor_branch_nodes(donor_type),
		"hide_open": True,
	}


def _has_donor_branch_nodes(donor_type):
	return _exists(
		"Donor",
		[
			["customer_type", "=", donor_type],
			["ifnull(parent_donor, '')", "=", ""],
			["ifnull(referred_by_trustee, '')", "=", ""],
		],
	)


def _has_trustee_branch_nodes():
	return _exists("Trustee", [["ifnull(parent_trustee, '')", "=", ""], ["is_group", "=", 1]])


def _get_child_donor_nodes(parent_donor):
	return _get_donor_nodes([["parent_donor", "=", parent_donor], ["ifnull(referred_by_trustee, '')", "=", ""]])


def _get_top_level_donor_nodes(donor_type):
	return _get_donor_nodes(
		[
			["customer_type", "=", donor_type],
			["ifnull(parent_donor, '')", "=", ""],
			["ifnull(referred_by_trustee, '')", "=", ""],
		]
	)


def _get_donor_nodes(filters):
	donors = frappe.get_list(
		"Donor",
		filters=filters,
		fields=["name", "customer_name", "is_group"],
		order_by="customer_name asc, name asc",
	)

	return [
		{
			"value": f"{DONOR_NODE_PREFIX}{donor.name}",
			"title": donor.customer_name or donor.name,
			"expandable": cint(donor.is_group) or _donor_has_children(donor.name),
			"is_group": cint(donor.is_group),
			"reference_doctype": "Donor",
			"reference_name": donor.name,
		}
		for donor in donors
	]


def _donor_has_children(donor):
	return _exists("Donor", [["parent_donor", "=", donor], ["ifnull(referred_by_trustee, '')", "=", ""]])


def _get_top_level_trustee_nodes():
	return _get_trustee_nodes([["ifnull(parent_trustee, '')", "=", ""], ["is_group", "=", 1]])


def _get_trustee_children(trustee):
	nodes = _get_trustee_nodes({"parent_trustee": trustee, "is_group": 1})
	nodes.extend(_get_referred_donor_nodes(trustee))
	return nodes


def _get_trustee_nodes(filters):
	trustees = frappe.get_list(
		"Trustee",
		filters=filters,
		fields=["name", "trustee_name"],
		order_by="trustee_name asc, name asc",
	)

	return [
		{
			"value": f"{TRUSTEE_NODE_PREFIX}{trustee.name}",
			"title": trustee.trustee_name or trustee.name,
			"expandable": _trustee_has_children(trustee.name),
			"reference_doctype": "Trustee",
			"reference_name": trustee.name,
		}
		for trustee in trustees
	]


def _get_referred_donor_nodes(trustee):
	donors = frappe.get_list(
		"Donor",
		filters={"referred_by_trustee": trustee},
		fields=["name", "customer_name", "is_group"],
		order_by="customer_name asc, name asc",
	)

	return [
		{
			"value": f"{DONOR_NODE_PREFIX}{donor.name}",
			"title": donor.customer_name or donor.name,
			"expandable": cint(donor.is_group) or _donor_has_children(donor.name),
			"is_group": cint(donor.is_group),
			"reference_doctype": "Donor",
			"reference_name": donor.name,
		}
		for donor in donors
	]


def _trustee_has_children(trustee):
	return bool(
		frappe.db.exists("Trustee", {"parent_trustee": trustee, "is_group": 1})
		or frappe.db.exists("Donor", {"referred_by_trustee": trustee})
	)


def _exists(doctype, filters):
	return bool(frappe.get_all(doctype, filters=filters, pluck="name", limit=1))
