# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


DENOMINATIONS = (10, 20, 50, 100, 500, 1000, 5000)


class BoxCollectionLog(Document):
	def validate(self):
		if self.action == "Collection":
			self.validate_collection_denominations()

	def validate_collection_denominations(self):
		if flt(self.collected_amount) < 0:
			frappe.throw(frappe._("Collected Amount cannot be negative."))

		if not self.cash_denominations:
			return

		total = 0
		for row in self.cash_denominations:
			denomination = cint(row.denomination)
			if denomination not in DENOMINATIONS:
				frappe.throw(frappe._("Invalid denomination {0}.").format(row.denomination))

			row.note_count = cint(row.note_count)
			if row.note_count < 0:
				frappe.throw(frappe._("Note count cannot be negative."))

			row.amount = denomination * row.note_count
			total += row.amount

		if total != flt(self.collected_amount):
			frappe.throw(frappe._("Cash denomination total must match Collected Amount."))
