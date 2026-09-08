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

		if not self.handover_datetime:
			self.handover_datetime = now_datetime()

		if not self.destination:
			self.destination = frappe.db.get_single_value("Donation Settings", "cash_handover_destination")

		if (
			frappe.db.get_single_value("Donation Settings", "require_cash_handover_proof")
			and not self.proof
		):
			frappe.throw(frappe._("Proof is required for Cash Handover."))

		self.variance = flt(self.amount) - flt(self.received_amount)
		if self.status == "Received" and self.variance:
			frappe.throw(frappe._("Variance must be resolved before marking handover as Received."))

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
		notify_finance(
			frappe._("Cash Handover Cancelled"),
			frappe._("Cash Handover {0} has been cancelled.").format(self.name),
			self.doctype,
			self.name,
		)
