import frappe
from frappe import _
from erpnext.accounts.doctype.gl_entry.gl_entry import GLEntry
from erpnext.accounts.party import validate_party_frozen_disabled

DEFAULT_ALLOWED_ACCOUNT_TYPES = {"Receivable", "Payable", "Equity"}
DONATION_ORDER_ALLOWED_ACCOUNT_TYPES = {"Cash", "Bank"}
DONATION_ORDER_ALLOWED_ROOT_TYPES = {"Income"}


class CustomGLEntry(GLEntry):
	def validate_party(self):
		validate_party_frozen_disabled(self.party_type, self.party)
		self.validate_account_party_type()

	def validate_account_party_type(self):
		if self.is_cancelled:
			return

		if self.party_type and self.party:
			account = frappe.get_cached_value(
				"Account",
				self.account,
				["account_type", "root_type"],
				as_dict=True,
			)
			account_type = account.account_type if account else None
			root_type = account.root_type if account else None
			if (
				self.party_type == "Donor"
				and self.is_donation_order_journal_entry()
				and (
					account_type in DONATION_ORDER_ALLOWED_ACCOUNT_TYPES
					or root_type in DONATION_ORDER_ALLOWED_ROOT_TYPES
				)
			):
				return

			party_account_type = frappe.get_cached_value("Party Type", self.party_type, "account_type")
			allowed_account_types = DEFAULT_ALLOWED_ACCOUNT_TYPES | {party_account_type}

			if account_type and account_type not in allowed_account_types:
				frappe.throw(
					_("Party Type {0} cannot be used with account {1}.").format(
						self.party_type,
						self.account,
					)
				)

	def is_donation_order_journal_entry(self):
		if self.voucher_type != "Journal Entry" or not self.voucher_no:
			return False

		user_remark = frappe.get_cached_value("Journal Entry", self.voucher_no, "user_remark") or ""
		return user_remark.startswith("Donation Order:")
