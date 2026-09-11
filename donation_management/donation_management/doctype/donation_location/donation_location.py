# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from donation_management.donation_management.validations import validate_unique_field


class DonationLocation(Document):
	def validate(self):
		validate_unique_field(self, "location_name", "Location Name")
