# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet

from donation_management.donation_management.validations import validate_unique_field


class DonationPurpose(NestedSet):
	nsm_parent_field = "parent_donation_purpose"

	def validate(self):
		validate_unique_field(self, "purpose_name", "Purpose Name")
		self.set_purpose_path()
		self.validate_account_mappings()

	def on_update(self):
		super().on_update()

	def set_purpose_path(self):
		parts = [self.purpose_name]
		parent = self.parent_donation_purpose
		while parent:
			parent_doc = frappe.get_cached_doc("Donation Purpose", parent)
			parts.insert(0, parent_doc.purpose_name)
			parent = parent_doc.parent_donation_purpose

		self.purpose_path = " > ".join(parts)

	def validate_account_mappings(self):
		if not self.account_mappings:
			return

		if self.is_group:
			frappe.throw(frappe._("Account mappings can only be added on leaf Donation Purposes."))

		seen = set()
		for row in self.account_mappings:
			key = (row.company, row.donation_type)
			if key in seen:
				frappe.throw(
					frappe._("Duplicate account mapping for {0} and {1}.").format(
						row.company,
						row.donation_type,
					)
				)
			seen.add(key)

			self.validate_account_mapping_account(row)
			self.validate_account_mapping_cost_center(row)

	def validate_account_mapping_account(self, row):
		account = frappe.db.get_value(
			"Account",
			row.credit_account,
			["name", "company", "is_group", "root_type"],
			as_dict=True,
		)
		if not account:
			frappe.throw(frappe._("Credit Account {0} was not found.").format(row.credit_account))

		if account.company != row.company:
			frappe.throw(
				frappe._("Credit Account {0} does not belong to Company {1}.").format(
					row.credit_account,
					row.company,
				)
			)

		if account.is_group:
			frappe.throw(frappe._("Credit Account {0} cannot be a group account.").format(row.credit_account))

		if account.root_type not in ("Income", "Liability", "Equity"):
			frappe.throw(
				frappe._("Credit Account {0} must be an Income, Liability, or Equity account.").format(
					row.credit_account
				)
			)

	def validate_account_mapping_cost_center(self, row):
		if not row.cost_center:
			return

		cost_center = frappe.db.get_value(
			"Cost Center",
			row.cost_center,
			["name", "company", "is_group"],
			as_dict=True,
		)
		if not cost_center:
			frappe.throw(frappe._("Cost Center {0} was not found.").format(row.cost_center))

		if cost_center.company != row.company:
			frappe.throw(
				frappe._("Cost Center {0} does not belong to Company {1}.").format(
					row.cost_center,
					row.company,
				)
			)

		if cost_center.is_group:
			frappe.throw(frappe._("Cost Center {0} cannot be a group cost center.").format(row.cost_center))
