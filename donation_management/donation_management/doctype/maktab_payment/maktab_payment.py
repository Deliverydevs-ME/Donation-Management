# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class MaktabPayment(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()
		self.set_reference_details()
		if flt(self.amount) <= 0:
			frappe.throw(frappe._("Amount must be greater than zero."))
		self.validate_accounts()
		self.validate_schedule()

	def on_submit(self):
		self.apply_to_schedule()

	def on_cancel(self):
		self.apply_to_schedule(reverse=True)

	def validate_schedule(self):
		if not self.payment_schedule:
			return
		schedule = frappe.db.get_value(
			"Maktab Payment Schedule",
			self.payment_schedule,
			[
				"ilaqi_maktab",
				"docstatus",
				"frequency",
				"outstanding_amount",
				"mode_of_payment",
				"donation_order",
				"collection_person",
			],
			as_dict=True,
		)
		if not schedule:
			frappe.throw(frappe._("Maktab Payment Schedule {0} was not found.").format(self.payment_schedule))
		if schedule.ilaqi_maktab != self.ilaqi_maktab:
			frappe.throw(frappe._("Payment Schedule belongs to a different Ilaqi Maktab."))
		self.outstanding_amount = schedule.outstanding_amount
		self.frequency = schedule.frequency or self.frequency
		self.mode_of_payment = self.mode_of_payment or schedule.mode_of_payment
		self.donation_order = self.donation_order or schedule.donation_order
		self.collection_person = self.collection_person or schedule.collection_person

	def set_reference_details(self):
		if self.ilaqi_maktab and not self.payment_schedule:
			self.frequency = frappe.db.get_value("Ilaqi Maktab", self.ilaqi_maktab, "frequency") or self.frequency

		if not self.donation_order:
			return

		order = frappe.db.get_value(
			"Donation Order",
			self.donation_order,
			["mode_of_payment", "mohasil", "debit_account", "credit_account", "donation_amount"],
			as_dict=True,
		)
		if not order:
			frappe.throw(frappe._("Donation Order {0} was not found.").format(self.donation_order))

		self.mode_of_payment = self.mode_of_payment or order.mode_of_payment
		self.collection_person = self.collection_person or order.mohasil
		self.debit_account = self.debit_account or order.debit_account
		self.credit_account = self.credit_account or order.credit_account
		self.amount = flt(self.amount) or flt(order.donation_amount)

	def validate_accounts(self):
		for fieldname, label in (("debit_account", "Debit Account"), ("credit_account", "Credit Account")):
			account = self.get(fieldname)
			if not account:
				continue

			is_group = frappe.db.get_value("Account", account, "is_group")
			if is_group is None:
				frappe.throw(frappe._("{0} {1} was not found.").format(label, account))
			if is_group:
				frappe.throw(frappe._("{0} cannot be a group account.").format(label))

	def apply_to_schedule(self, reverse=False):
		if not self.payment_schedule:
			return
		schedule = frappe.get_doc("Maktab Payment Schedule", self.payment_schedule)
		multiplier = -1 if reverse else 1
		schedule.collected_amount = flt(schedule.collected_amount) + (flt(self.amount) * multiplier)
		schedule.advance_amount = flt(schedule.advance_amount) + (flt(self.advance_amount) * multiplier)
		schedule.outstanding_amount = max(flt(schedule.due_amount) - flt(schedule.collected_amount), 0)
		if flt(schedule.outstanding_amount) <= 0:
			schedule.status = "Paid"
		elif flt(schedule.collected_amount) > 0:
			schedule.status = "Partially Paid"
		else:
			schedule.status = "Pending"
		if not reverse:
			if self.frequency:
				schedule.frequency = self.frequency
			if self.mode_of_payment:
				schedule.mode_of_payment = self.mode_of_payment
			if self.donation_order:
				schedule.donation_order = self.donation_order
			if self.collection_person:
				schedule.collection_person = self.collection_person
		else:
			set_latest_payment_reference(schedule)
		schedule.save(ignore_permissions=True)


def set_latest_payment_reference(schedule):
	latest_payment = frappe.get_all(
		"Maktab Payment",
		filters={"payment_schedule": schedule.name, "docstatus": 1},
		fields=["frequency", "mode_of_payment", "donation_order", "collection_person"],
		order_by="posting_date desc, creation desc",
		limit=1,
	)
	if latest_payment:
		latest_payment = latest_payment[0]
		schedule.frequency = latest_payment.frequency or schedule.frequency
		schedule.mode_of_payment = latest_payment.mode_of_payment
		schedule.donation_order = latest_payment.donation_order
		schedule.collection_person = latest_payment.collection_person
	else:
		schedule.mode_of_payment = None
		schedule.donation_order = None
		schedule.collection_person = None
