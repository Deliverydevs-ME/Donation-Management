# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class MaktabPayment(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()
		if flt(self.amount) <= 0:
			frappe.throw(frappe._("Amount must be greater than zero."))
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
			["ilaqi_maktab", "docstatus"],
			as_dict=True,
		)
		if not schedule:
			frappe.throw(frappe._("Maktab Payment Schedule {0} was not found.").format(self.payment_schedule))
		if schedule.ilaqi_maktab != self.ilaqi_maktab:
			frappe.throw(frappe._("Payment Schedule belongs to a different Ilaqi Maktab."))

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
		schedule.save(ignore_permissions=True)
