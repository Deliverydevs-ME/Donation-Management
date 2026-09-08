# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DonationBox(Document):
	def validate(self):
		self.validate_box_number()
		self.set_defaults()
		self.set_box_shape()
		self.set_box_code()
		self.validate_unique_box_number()

	def validate_box_number(self):
		if str(self.box_number or "").strip().startswith("-"):
			frappe.throw(frappe._("Box Number cannot be negative."))

	def on_submit(self):
		self.create_box_collection()

	def set_defaults(self):
		if not self.donation_head:
			self.donation_head = "Sadqa"

	def set_box_shape(self):
		if self.box_shape:
			return

		default_shape = frappe.db.get_value("Box Shape", {"enabled": 1}, "name", order_by="creation asc")
		if not default_shape:
			frappe.throw(frappe._("Create at least one enabled Box Shape before creating Donation Boxes."))
		self.box_shape = default_shape

	def set_box_code(self):
		if self.donation_head and self.box_number:
			self.box_code = f"{self.donation_head}-{self.box_number}"
		else:
			self.box_code = None

	def validate_unique_box_number(self):
		if not self.donation_head or not self.box_number:
			return

		existing_box = frappe.db.exists(
			"Donation Box",
			{
				"donation_head": self.donation_head,
				"box_number": self.box_number,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)
		if existing_box:
			frappe.throw(
				frappe._("Box Number {0} is already used for {1} by Donation Box {2}.").format(
					self.box_number,
					self.donation_head,
					existing_box,
				)
			)

	def create_box_collection(self):
		existing_box_collection = frappe.db.exists(
			"Box Collection",
			{
				"box_number": self.name,
				"docstatus": ["!=", 2],
			},
		)
		if existing_box_collection:
			return existing_box_collection

		box_collection = frappe.get_doc(
			{
				"doctype": "Box Collection",
				"box_number": self.name,
				"box_code": self.box_code,
				"status": "Available",
			}
		)
		box_collection.flags.from_donation_box = True
		box_collection.insert(ignore_permissions=True)
		box_collection.flags.ignore_permissions = True
		box_collection.submit()
		return box_collection.name
