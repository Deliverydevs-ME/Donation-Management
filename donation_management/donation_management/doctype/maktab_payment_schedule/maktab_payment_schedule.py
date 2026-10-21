# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


class MaktabPaymentSchedule(Document):
	def validate(self):
		if not frappe.db.exists("Ilaqi Maktab", self.ilaqi_maktab):
			frappe.throw(frappe._("Ilaqi Maktab {0} was not found.").format(self.ilaqi_maktab))
		self.set_reference_details()
		validate_collection_accounts(self.custom_debit_account, self.custom_credit_account)
		if flt(self.due_amount) < 0:
			frappe.throw(frappe._("Due Amount cannot be negative."))
		if flt(self.collected_amount) < 0 or flt(self.advance_amount) < 0:
			frappe.throw(frappe._("Collected and Advance Amount cannot be negative."))

		self.outstanding_amount = max(flt(self.due_amount) - flt(self.collected_amount), 0)
		if flt(self.outstanding_amount) <= 0:
			self.status = "Paid"
		elif flt(self.collected_amount) > 0:
			self.status = "Partially Paid"
		elif self.due_date and getdate(self.due_date) < getdate(today()):
			self.status = "Overdue"
		else:
			self.status = "Pending"

	def set_reference_details(self):
		if self.ilaqi_maktab:
			maktab = frappe.db.get_value(
				"Ilaqi Maktab",
				self.ilaqi_maktab,
				["frequency", "responsible_person"],
				as_dict=True,
			)
			if maktab:
				self.frequency = maktab.frequency or self.frequency
				self.custom_responsible_person = get_employee_name(maktab.responsible_person)

		if not self.donation_order:
			return

		order = frappe.db.get_value(
			"Donation Order",
			self.donation_order,
			["mode_of_payment", "mohasil", "debit_account", "credit_account"],
			as_dict=True,
		)
		if not order:
			frappe.throw(frappe._("Donation Order {0} was not found.").format(self.donation_order))
		if not order.debit_account or not order.credit_account:
			frappe.throw(
				frappe._(
					"Donation Order {0} must have both Debit Account and Credit Account before it can be linked."
				).format(self.donation_order)
			)

		self.mode_of_payment = self.mode_of_payment or order.mode_of_payment
		self.collection_person = self.collection_person or order.mohasil
		self.custom_debit_account = order.debit_account
		self.custom_credit_account = order.credit_account


def validate_collection_accounts(debit_account, credit_account):
	if not debit_account or not credit_account:
		frappe.throw(frappe._("Both Debit Account and Credit Account are required."))
	if debit_account == credit_account:
		frappe.throw(frappe._("Debit Account and Credit Account must be different."))

	debit_details = get_ledger_account(debit_account, "Debit Account")
	credit_details = get_ledger_account(credit_account, "Credit Account")

	if debit_details.root_type != "Asset":
		frappe.throw(frappe._("Debit Account must be an Asset account."))
	if credit_details.root_type != "Income":
		frappe.throw(frappe._("Credit Account must be an Income account."))
	if debit_details.company != credit_details.company:
		frappe.throw(frappe._("Debit Account and Credit Account must belong to the same Company."))


def get_ledger_account(account, label):
	account_details = frappe.db.get_value(
		"Account",
		account,
		["name", "company", "disabled", "is_group", "root_type"],
		as_dict=True,
	)
	if not account_details:
		frappe.throw(frappe._("{0} {1} was not found.").format(label, account))
	if account_details.is_group:
		frappe.throw(frappe._("{0} cannot be a group account.").format(label))
	if account_details.disabled:
		frappe.throw(frappe._("{0} cannot be a disabled account.").format(label))

	return account_details


def get_employee_name(employee):
	if not employee:
		return None

	return frappe.db.get_value("Employee", employee, "employee_name")
