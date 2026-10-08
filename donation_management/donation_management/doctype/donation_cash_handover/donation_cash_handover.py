# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from donation_management.donation_management.notifications import notify_finance, notify_users


class DonationCashHandover(Document):
	def validate(self):
		if not self.company:
			from donation_management.donation_management.api import get_default_company

			self.company = get_default_company()

		self.set_donation_closing_details()

		if not self.handover_datetime:
			self.handover_datetime = now_datetime()

		if not self.destination:
			self.destination = frappe.db.get_single_value("Donation Settings", "cash_handover_destination")

		if not self.proof:
			frappe.throw(frappe._("Proof is required for Cash Handover."))

		self.variance = flt(self.amount) - flt(self.received_amount)
		if self.status == "Received" and self.variance:
			frappe.throw(frappe._("Variance must be resolved before marking handover as Received."))

	def after_insert(self):
		self.set_closing_handover_reference()

	def on_update(self):
		self.set_closing_handover_reference()

	def on_submit(self):
		self.status = "Received"
		self.db_set("status", "Received", update_modified=False)
		notify_finance(
			frappe._("Cash Handover Received"),
			frappe._("Cash Handover {0} has been received.").format(self.name),
			self.doctype,
			self.name,
		)
		notify_users(
			frappe._("Cash Handover Received"),
			frappe._("Your Cash Handover {0} has been received.").format(self.name),
			users=[self.cashier],
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", "Cancelled", update_modified=False)
		self.clear_closing_handover_reference()
		notify_finance(
			frappe._("Cash Handover Cancelled"),
			frappe._("Cash Handover {0} has been cancelled.").format(self.name),
			self.doctype,
			self.name,
		)

	def set_donation_closing_details(self):
		if not self.donation_closing:
			return

		closing = frappe.db.get_value(
			"Donation Closing",
			self.donation_closing,
			["name", "docstatus", "company", "cashier", "total_amount"],
			as_dict=True,
		)
		if not closing:
			frappe.throw(frappe._("Donation Closing {0} was not found.").format(self.donation_closing))
		if closing.docstatus == 2:
			frappe.throw(
				frappe._("Donation Closing {0} has been cancelled and cannot be used for Cash Handover.").format(
					self.donation_closing
				)
			)

		filters = {"donation_closing": self.donation_closing, "docstatus": ["<", 2]}
		if self.name:
			filters["name"] = ["!=", self.name]
		existing = frappe.get_all(
			"Donation Cash Handover",
			filters=filters,
			pluck="name",
			limit_page_length=1,
		)
		if existing:
			frappe.throw(
				frappe._("Donation Closing {0} already has active Cash Handover {1}.").format(
					self.donation_closing,
					existing[0],
				)
			)

		self.company = closing.company
		self.cashier = closing.cashier
		self.amount = flt(closing.total_amount)

	def set_closing_handover_reference(self):
		if self.donation_closing:
			frappe.db.set_value(
				"Donation Closing", self.donation_closing, "cash_handover", self.name, update_modified=False
			)

	def clear_closing_handover_reference(self):
		if self.donation_closing and frappe.db.get_value(
			"Donation Closing", self.donation_closing, "cash_handover"
		) == self.name:
			frappe.db.set_value(
				"Donation Closing", self.donation_closing, "cash_handover", None, update_modified=False
			)
