# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, today

from donation_management.donation_management.doctype.donor.donor import (
	normalize_phone,
	validate_mohasil_employee,
)
from donation_management.donation_management.doctype.donation_location_assignment.donation_location_assignment import (
	get_assignment_for_date,
)
from donation_management.donation_management.doctype.donor_program_enrollment.donor_program_enrollment import (
	upsert_donor_program_enrollment,
)
from donation_management.donation_management.api import (
	account_matches_donation_type,
	get_default_company,
	get_default_cash_account,
	get_donation_purpose_account_mapping,
	get_mode_of_payment_account,
	get_receiving_account_donation_type,
)
from donation_management.donation_management.doctype.book.book import (
	get_donation_book_order_total,
	get_donation_book_used_receipts,
	get_receipt_range_count,
	receipt_number_in_range,
	update_donation_book_receipt_usage,
)


SPONSORSHIP_PURPOSE = "Sponsorship"
PRISONER_PROGRAM_SUFFIX = " - Prisoner"
ALLOWED_SPONSORSHIP_PURPOSES = (
	"Sponsorship - Prisoner",
	"Sponsorship - Student",
	"Sponsorship - MTC",
	"Sponsorship - Maktab",
)
SPONSORSHIP_DAYS_IN_MONTH = 30
DENOMINATIONS = (10, 20, 50, 100, 500, 1000, 5000)
CHEQUE_MODE_OF_PAYMENT = "Cheque"
BANK_DRAFT_MODE_OF_PAYMENT = "Bank Draft"
DEPOSIT_ACCOUNT_MODES = ("Cheque", "Card Payment")
PDC_STATUS_NOT_APPLICABLE = "Not Applicable"
PDC_STATUS_PENDING = "Pending Deposit"
PDC_STATUS_DEPOSITED = "Deposited"


def format_sponsorship_duration(total_days):
	total_days = max(cint(total_days), 0)
	months = total_days // SPONSORSHIP_DAYS_IN_MONTH
	days = total_days % SPONSORSHIP_DAYS_IN_MONTH
	parts = []
	if months:
		parts.append(frappe._("{0} month{1}").format(months, "" if months == 1 else "s"))
	if days:
		parts.append(frappe._("{0} day{1}").format(days, "" if days == 1 else "s"))
	return " ".join(parts) or frappe._("0 days")


def is_prisoner_sponsorship_program(program_name):
	return bool(program_name and str(program_name).endswith(PRISONER_PROGRAM_SUFFIX))


class DonationOrder(Document):
	def validate(self):
		if not self.donation_posting_date:
			self.donation_posting_date = now_datetime()

		self.set_company_defaults()
		self.set_donor_details()
		self.validate_mohasil_details()
		self.set_and_validate_donation_location()
		self.set_esaal_e_sawab_snapshot()
		self.set_purpose_details()
		self.validate_donation_book_receipts()
		self.validate_manual_receipt_uniqueness()
		self.set_previous_sponsorship_balance()
		self.set_sponsorship_allocations()
		self.validate_beneficiary()
		self.set_total_donation()
		self.validate_donation_book_amount_limit()
		self.validate_cash_denominations()
		self.set_accounting_details()
		self.set_pdc_details()
		self.set_donor_information_request_audit()
		self.validate_accounting_details()
		self.validate_posted_accounting_locked()

	def on_update(self):
		self.update_linked_donation_book_usage()
		self.create_instrument_event_if_changed()
		self.log_confidential_reference_changes()

	def on_submit(self):
		if self.is_pending_pdc() and getdate(self.cheque_deposit_date) > getdate(today()):
			frappe.throw(
				frappe._("Post-Dated Cheque Donation Order can only be submitted on or after {0}.").format(
					frappe.format_value(self.cheque_deposit_date, {"fieldtype": "Date"})
				)
			)

		self.update_donor_program_enrollments()
		if self.is_pending_pdc():
			self.accounting_status = "Not Posted"
			self.db_set("accounting_status", "Not Posted", update_modified=False)
			self.set_receipt_status()
			return
		self.set_bank_deposit_status()
		self.create_journal_entry()
		self.update_donor_program_enrollments()
		self.set_receipt_status()

	def on_cancel(self):
		self.cancel_linked_journal_entry()
		self.update_linked_donation_book_usage()
		if self.meta.has_field("receipt_status"):
			self.db_set("receipt_status", "Cancelled", update_modified=False)

	def before_cancel(self):
		self.validate_cancellation_controls()

	def on_trash(self):
		self.cancel_linked_journal_entry()

	def is_sponsorship(self):
		return any(row.donation_category == SPONSORSHIP_PURPOSE for row in self.get("purpose_details", []))

	def is_cheque_mode(self):
		return self.mode_of_payment == CHEQUE_MODE_OF_PAYMENT

	def is_bank_draft_mode(self):
		return self.mode_of_payment == BANK_DRAFT_MODE_OF_PAYMENT

	def is_deposit_account_mode(self):
		return self.mode_of_payment in DEPOSIT_ACCOUNT_MODES

	def is_manual_bank_mode(self):
		return self.mode_of_payment_type == "Bank" and not self.is_deposit_account_mode()

	def is_pending_pdc(self):
		return self.is_cheque_mode() and cint(self.is_post_dated_cheque) and self.pdc_status == PDC_STATUS_PENDING

	def set_company_defaults(self):
		if not self.company:
			self.company = get_default_company()

		if self.company and not self.currency:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")

	def set_donor_details(self):
		if not self.donor_name and self.donor_phone_number:
			self.donor_name = frappe.db.get_value(
				"Donor",
				{"donor_phone_digits": normalize_phone(self.donor_phone_number)},
				"name",
			)

		if not self.donor_name and self.donor_email:
			self.donor_name = frappe.db.get_value(
				"Donor",
				{"donor_email": self.donor_email.strip().lower()},
				"name",
			)

		if not self.donor_name:
			frappe.throw(frappe._("Donor is required."))

		donor = frappe.db.get_value(
			"Donor",
			self.donor_name,
			[
				"name",
				"customer_name",
				"donor_email",
				"donor_phone_number",
				"donor_phone_digits",
				"referred_by_trustee",
				"mohasil",
				"customer_pos_id",
				"party",
				"confidential_ref_co",
			],
			as_dict=True,
		)
		if not donor:
			frappe.throw(frappe._("Donor {0} was not found.").format(self.donor_name))

		if self.donor_phone_number:
			donor_phone_digits = normalize_phone(self.donor_phone_number)
			if donor.donor_phone_digits and donor_phone_digits != donor.donor_phone_digits:
				frappe.throw(
					frappe._("Donor Phone Number {0} does not match selected Donor {1}.").format(
						self.donor_phone_number,
						donor.name,
					)
				)

		if self.donor_email and donor.donor_email and self.donor_email.strip().lower() != donor.donor_email:
			frappe.throw(
				frappe._("Donor Email {0} does not match selected Donor {1}.").format(
					self.donor_email,
					donor.name,
				)
			)

		self.donor_email = donor.donor_email or self.donor_email
		self.donor_phone_number = donor.donor_phone_number
		self.referred_by_trustee = donor.referred_by_trustee
		if hasattr(self, "donor_pos_id"):
			self.donor_pos_id = donor.customer_pos_id
		if hasattr(self, "party"):
			self.party = donor.party
		if hasattr(self, "confidential_ref_co"):
			self.confidential_ref_co = donor.confidential_ref_co
		if cint(self.is_mohasil_collection) and not self.mohasil:
			self.mohasil = donor.mohasil
		if not self.name_on_donation_slip:
			self.name_on_donation_slip = donor.customer_name

	def set_and_validate_donation_location(self):
		posting_date = getdate(self.donation_posting_date)

		if cint(self.is_mohasil_collection):
			if not self.mohasil:
				frappe.throw(frappe._("Mohasil is required for Mohasil Collection."))

			assignment = get_assignment_for_date(self.mohasil, posting_date)
			if not assignment:
				frappe.throw(
					frappe._("No active Donation Location Assignment found for Mohasil {0} on {1}.").format(
						self.mohasil,
						frappe.format_value(posting_date, {"fieldtype": "Date"}),
					)
				)

			if self.donation_location and self.donation_location != assignment.donation_location:
				frappe.throw(
					frappe._("Donation Location must be {0} for Mohasil {1} on {2}.").format(
						assignment.donation_location,
						self.mohasil,
						frappe.format_value(posting_date, {"fieldtype": "Date"}),
					)
				)

			self.donation_location = assignment.donation_location
			self.location_assignment = assignment.name
			return

		self.location_assignment = None
		if not self.donation_location:
			frappe.throw(frappe._("Donation Location is required."))

	def set_esaal_e_sawab_snapshot(self):
		if not self.donor_name or self.get("esaal_e_sawab"):
			return

		rows = frappe.get_all(
			"Esaal E Sawab Detail",
			filters={
				"parenttype": "Donor",
				"parent": self.donor_name,
				"parentfield": "esaal_e_sawab",
			},
			fields=["person_name", "relationship", "remarks"],
			order_by="idx asc",
		)
		for row in rows:
			self.append(
				"esaal_e_sawab",
				{
					"person_name": row.person_name,
					"relationship": row.relationship,
					"remarks": row.remarks,
				},
			)

	def validate_mohasil_details(self):
		if self.manual_receipt_number:
			self.manual_receipt_number = self.manual_receipt_number.strip()
			if self.manual_receipt_number.startswith("-"):
				frappe.throw(frappe._("Manual Receipt Number cannot be negative."))

		if self.manual_receipt_number and not cint(self.is_mohasil_collection):
			self.is_mohasil_collection = 1

		if not cint(self.is_mohasil_collection):
			self.mohasil = None
			self.donation_book = None
			self.manual_receipt_number = None
			self.manual_receipt_date = None
			self.set("cash_denominations", [])
			return

		if self.manual_receipt_number and not self.mohasil:
			frappe.throw(frappe._("Mohasil is required when Manual Receipt Number is entered."))

		if self.mohasil:
			validate_mohasil_employee(self.mohasil, "Mohasil")

		if not self.mohasil:
			frappe.throw(frappe._("Mohasil is required for Mohasil Collection."))

		if not self.donation_book_serial_no:
			frappe.throw(frappe._("Donation Book is required for Mohasil Collection."))

		self.set_donation_book_from_serial()

		if not self.donation_book:
			frappe.throw(frappe._("Donation Book is required for Mohasil Collection."))

		self.validate_donation_book_for_mohasil()

	def set_donation_book_from_serial(self):
		if not self.donation_book_serial_no:
			return

		result = frappe.db.sql(
			"""
			select book.name
			from `tabBook Assignment Detail` detail
			inner join `tabBook` book
				on book.name = detail.parent
			where detail.book_serial_no = %(book_serial_no)s
				and book.book_type = 'Donation Book'
				and book.status = 'Returned'
				and book.issued_to_employee = %(mohasil)s
				and book.docstatus != 2
				and detail.parentfield = 'assigned_books'
			limit 1
			""",
			{
				"book_serial_no": self.donation_book_serial_no,
				"mohasil": self.mohasil,
			},
		)
		if not result:
			frappe.throw(
				frappe._("Donation Book Serial No {0} is not available for Mohasil {1}.").format(
					self.donation_book_serial_no,
					self.mohasil,
				)
			)
		self.donation_book = result[0][0]

	def validate_donation_book_for_mohasil(self):
		book = frappe.db.get_value(
			"Book",
			self.donation_book,
			[
				"book_type",
				"status",
				"issued_to_employee",
				"start_date",
				"from_receipt_no",
				"to_receipt_no",
				"remaining_receipts",
			],
			as_dict=True,
		)
		if not book:
			frappe.throw(frappe._("Donation Book {0} was not found.").format(self.donation_book))
		if book.book_type != "Donation Book":
			frappe.throw(frappe._("Book {0} is not a Donation Book.").format(self.donation_book))
		if book.status != "Returned":
			frappe.throw(
				frappe._("Donation Book {0} must be Returned before Donation Orders can be created against its receipts.").format(
					self.donation_book
				)
			)
		if book.issued_to_employee != self.mohasil:
			frappe.throw(
				frappe._("Donation Book {0} is issued to {1}, not selected Mohasil {2}.").format(
					self.donation_book,
					book.issued_to_employee or frappe._("nobody"),
					self.mohasil,
				)
			)

		if self.manual_receipt_date and book.start_date and getdate(self.manual_receipt_date) < getdate(book.start_date):
			frappe.throw(
				frappe._("Manual Receipt Date cannot be before Donation Book Start Date {0}.").format(
					frappe.format_value(book.start_date, {"fieldtype": "Date"})
				)
			)

		return book

	def get_purpose_receipt_numbers(self):
		self.move_legacy_parent_receipt_to_purpose_row()
		receipt_numbers = []
		for row in self.get("purpose_details", []):
			receipt_number = str(row.get("manual_receipt_number") or "").strip()
			row.manual_receipt_number = receipt_number
			if receipt_number:
				if receipt_number.startswith("-"):
					frappe.throw(
						frappe._("Manual Receipt Number cannot be negative in Purpose Detail row {0}.").format(row.idx)
					)
				receipt_numbers.append(receipt_number)
		return receipt_numbers

	def move_legacy_parent_receipt_to_purpose_row(self):
		if not self.manual_receipt_number or len(self.get("purpose_details", [])) != 1:
			return

		row = self.purpose_details[0]
		if not row.manual_receipt_number:
			row.manual_receipt_number = self.manual_receipt_number

	def validate_donation_book_receipts(self):
		if not cint(self.is_mohasil_collection):
			for row in self.get("purpose_details", []):
				row.manual_receipt_number = None
			return

		book = self.validate_donation_book_for_mohasil()
		receipt_numbers = self.get_purpose_receipt_numbers()

		for row in self.get("purpose_details", []):
			if not row.manual_receipt_number:
				frappe.throw(
					frappe._("Manual Receipt Number is required in Purpose Detail row {0} for Mohasil Collection.").format(
						row.idx
					)
				)

		unique_receipt_numbers = set(receipt_numbers)
		receipt_ranges = self.get_donation_book_receipt_ranges(book)
		for receipt_number in unique_receipt_numbers:
			if not any(
				receipt_number_in_range(
					receipt_number,
					receipt_range.from_receipt_no,
					receipt_range.to_receipt_no,
				)
				for receipt_range in receipt_ranges
			):
				frappe.throw(
					frappe._("Manual Receipt Number {0} is outside the receipt ranges assigned to Donation Book {1}.").format(
						receipt_number,
						self.donation_book,
					)
			)

			existing_order = self.get_existing_donation_book_receipt_order(receipt_number)
			if existing_order:
				frappe.throw(
					frappe._(
						"Manual Receipt Number {0} is already used for Donation Book Serial No {1} in Donation Order {2}."
					).format(
						receipt_number,
						self.donation_book_serial_no or self.donation_book,
						existing_order,
					)
				)

		total_receipts = sum(
			get_receipt_range_count(receipt_range.from_receipt_no, receipt_range.to_receipt_no)
			for receipt_range in receipt_ranges
		)
		used_receipts_without_current = get_donation_book_used_receipts(
			self.donation_book,
			exclude_order=self.name,
			donation_book_serial_no=self.donation_book_serial_no,
		)
		if used_receipts_without_current + len(unique_receipt_numbers) > total_receipts:
			frappe.throw(
				frappe._("Donation Book Serial No {0} has no remaining receipts.").format(
					self.donation_book_serial_no or self.donation_book,
				)
			)

	def get_donation_book_receipt_ranges(self, book):
		if self.donation_book_serial_no:
			serial_range = frappe.db.get_value(
				"Book Assignment Detail",
				{
					"parent": self.donation_book,
					"parenttype": "Book",
					"parentfield": "assigned_books",
					"book_serial_no": self.donation_book_serial_no,
				},
				["from_receipt_no", "to_receipt_no"],
				as_dict=True,
			)
			if serial_range and serial_range.from_receipt_no and serial_range.to_receipt_no:
				return [serial_range]

		assigned_ranges = frappe.get_all(
			"Book Assignment Detail",
			filters={
				"parent": self.donation_book,
				"parenttype": "Book",
				"parentfield": "assigned_books",
			},
			fields=["from_receipt_no", "to_receipt_no"],
			order_by="idx asc",
		)
		assigned_ranges = [
			row for row in assigned_ranges
			if row.from_receipt_no and row.to_receipt_no
		]
		if assigned_ranges:
			return assigned_ranges

		if book.from_receipt_no and book.to_receipt_no:
			return [frappe._dict({
				"from_receipt_no": book.from_receipt_no,
				"to_receipt_no": book.to_receipt_no,
			})]

		frappe.throw(frappe._("Donation Book {0} has no receipt ranges configured.").format(self.donation_book))

	def get_existing_donation_book_receipt_order(self, receipt_number):
		detail_serial_condition = ""
		parent_serial_condition = ""
		values = {
			"donation_book": self.donation_book,
			"current_order": self.name,
			"receipt_number": receipt_number,
		}
		if self.donation_book_serial_no:
			detail_serial_condition = "and parent.donation_book_serial_no = %(donation_book_serial_no)s"
			parent_serial_condition = "and donation_book_serial_no = %(donation_book_serial_no)s"
			values["donation_book_serial_no"] = self.donation_book_serial_no

		existing = frappe.db.sql(
			"""
			select existing_order.name
			from (
				select parent.name
				from `tabDonation Order` parent
				inner join `tabDonation Order Purpose Detail` detail
					on detail.parent = parent.name
				where parent.donation_book = %(donation_book)s
					and parent.docstatus != 2
					and parent.name != %(current_order)s
					{detail_serial_condition}
					and detail.manual_receipt_number = %(receipt_number)s
				union
				select name
				from `tabDonation Order`
				where donation_book = %(donation_book)s
					and docstatus != 2
					and name != %(current_order)s
					{parent_serial_condition}
					and manual_receipt_number = %(receipt_number)s
			) existing_order
			limit 1
			""".format(
				detail_serial_condition=detail_serial_condition,
				parent_serial_condition=parent_serial_condition,
			),
			values,
		)
		return existing[0][0] if existing else None

	def validate_manual_receipt_uniqueness(self):
		receipt_numbers = []
		parent_receipt = str(self.manual_receipt_number or "").strip()
		if parent_receipt:
			receipt_numbers.append(parent_receipt)

		for row in self.get("purpose_details", []):
			receipt_number = str(row.get("manual_receipt_number") or "").strip()
			if receipt_number:
				receipt_numbers.append(receipt_number)

		if not receipt_numbers:
			if self.meta.has_field("manual_receipt_reconciliation_status"):
				self.manual_receipt_reconciliation_status = "Missing"
			return

		if len(receipt_numbers) != len(set(receipt_numbers)):
			frappe.throw(frappe._("Manual Receipt Number is repeated in this Donation Order."))

		for receipt_number in set(receipt_numbers):
			existing = get_existing_manual_receipt_order(receipt_number, current_order=self.name)
			if existing:
				frappe.throw(
					frappe._("Manual Receipt Number {0} is already used in Donation Order {1}.").format(
						receipt_number,
						existing,
					)
				)

		if self.meta.has_field("manual_receipt_reconciliation_status"):
			self.manual_receipt_reconciliation_status = "Pending Conversion"

	def validate_donation_book_amount_limit(self):
		if not cint(self.is_mohasil_collection) or not self.donation_book:
			return

		returned_amount = self.get_donation_book_returned_amount()
		if returned_amount <= 0:
			return

		current_total = get_donation_book_order_total(
			self.donation_book,
			exclude_order=self.name,
			donation_book_serial_no=self.donation_book_serial_no,
		) + flt(self.donation_amount)
		if flt(current_total, 2) > flt(returned_amount, 2):
			frappe.throw(
				frappe._(
					"Donation Orders total {0} cannot exceed returned amount {1} for Donation Book Serial No {2}."
				).format(
					frappe.format_value(current_total, {"fieldtype": "Currency"}),
					frappe.format_value(returned_amount, {"fieldtype": "Currency"}),
					self.donation_book_serial_no or self.donation_book,
				)
			)

	def get_donation_book_returned_amount(self):
		if self.donation_book_serial_no:
			serial_amount = frappe.db.get_value(
				"Book Return Collection",
				{
					"parent": self.donation_book,
					"parenttype": "Book",
					"parentfield": "return_collections",
					"book_serial_no": self.donation_book_serial_no,
				},
				"collected_amount",
			)
			if serial_amount is not None:
				return flt(serial_amount)

		return flt(frappe.db.get_value("Book", self.donation_book, "collected_amount"))

	def update_linked_donation_book_usage(self):
		books = set()
		if self.donation_book:
			books.add(self.donation_book)

		previous_doc = self.get_doc_before_save()
		if previous_doc and previous_doc.donation_book:
			books.add(previous_doc.donation_book)

		for book in books:
			update_donation_book_receipt_usage(book)

	def validate_cash_denominations(self):
		if not cint(self.is_mohasil_collection):
			self.set("cash_denominations", [])
			return

		if not self.cash_denominations:
			return

		denomination_total = 0
		has_note_count = False
		for row in self.cash_denominations:
			denomination = cint(row.denomination)
			if denomination not in DENOMINATIONS:
				frappe.throw(frappe._("Invalid denomination {0}.").format(row.denomination))

			if cint(row.note_count) < 0:
				frappe.throw(frappe._("Note count cannot be negative for denomination {0}.").format(row.denomination))

			row.amount = denomination * cint(row.note_count)
			denomination_total += flt(row.amount)
			if cint(row.note_count):
				has_note_count = True

		if not has_note_count:
			return

		expected_amount = flt(self.donation_amount)
		if flt(denomination_total) != expected_amount:
			frappe.throw(
				frappe._("Cash denomination total {0} must match Total Donation Received {1}.").format(
					frappe.format_value(denomination_total, {"fieldtype": "Currency"}),
					frappe.format_value(expected_amount, {"fieldtype": "Currency"}),
				)
			)

	def validate_cancellation_controls(self):
		if not self.cancellation_reason:
			frappe.throw(frappe._("Cancellation Reason is required before cancelling Donation Order."))

		if not self.cancellation_approved_by:
			frappe.throw(frappe._("Cancellation Approved By is required before cancelling Donation Order."))

	def set_bank_deposit_status(self):
		if self.mode_of_payment_type == "Cash" and self.accounting_status == "Posted":
			self.bank_deposit_status = "Pending Bank Deposit"
		else:
			self.bank_deposit_status = "Not Applicable"
		self.db_set("bank_deposit_status", self.bank_deposit_status, update_modified=False)

	def update_donor_program_enrollments(self):
		if not self.is_sponsorship() or not self.donor_name:
			return

		for row in self.sponsorship_students or []:
			if not row.sponsorship_program or not row.quantity:
				continue

			upsert_donor_program_enrollment(
				donor=self.donor_name,
				sponsorship_program=row.sponsorship_program,
				student_quantity=row.quantity,
				donation_purpose=self.donation_purpose,
				donation_order=self.name,
			)

	def set_purpose_details(self):
		self.add_legacy_purpose_row_if_needed()
		if not self.purpose_details:
			frappe.throw(frappe._("At least one Purpose Detail row is required."))

		total_amount = 0
		sponsorship_rows = []

		for row in self.purpose_details:
			self.set_purpose_detail_row(row)
			total_amount += flt(row.amount)
			if row.donation_category == SPONSORSHIP_PURPOSE:
				sponsorship_rows.append(row)

		self.donation_amount = total_amount

		primary_row = sponsorship_rows[0] if sponsorship_rows else self.purpose_details[0]
		self.donation_type = primary_row.donation_type
		self.purpose_of_donation = primary_row.donation_category
		self.donation_purpose = primary_row.donation_purpose
		self.purpose_path = primary_row.purpose_path
		self.credit_account = primary_row.credit_account
		self.accounting_cost_center = primary_row.cost_center

		if not self.donation_purpose:
			self.requires_student = 0
			self.requires_prisoner = 0
			self.student_mode = None
			self.purpose_path = None
			return

		purposes = [
			frappe.get_cached_doc("Donation Purpose", row.donation_purpose)
			for row in (sponsorship_rows or [primary_row])
		]
		self.requires_student = 1 if any(cint(purpose.requires_student) for purpose in purposes) else 0
		self.requires_prisoner = 1 if any(cint(purpose.requires_prisoner) for purpose in purposes) else 0
		self.student_mode = purposes[0].student_mode

	def add_legacy_purpose_row_if_needed(self):
		if self.purpose_details or not (self.donation_type and self.purpose_of_donation and self.donation_purpose):
			return

		self.append(
			"purpose_details",
			{
				"donation_type": self.donation_type,
				"donation_category": self.purpose_of_donation,
				"donation_purpose": self.donation_purpose,
				"amount": flt(self.donation_amount),
				"debit_account": self.debit_account,
				"credit_account": self.credit_account,
				"cost_center": self.accounting_cost_center,
			},
		)

	def set_purpose_detail_row(self, row):
		if not row.donation_type:
			frappe.throw(frappe._("Type of Donation is required in Purpose Detail row {0}.").format(row.idx))
		if not row.donation_category:
			frappe.throw(frappe._("Donation Category is required in Purpose Detail row {0}.").format(row.idx))
		if not row.donation_purpose:
			frappe.throw(frappe._("Donation Purpose is required in Purpose Detail row {0}.").format(row.idx))
		if flt(row.amount) <= 0:
			frappe.throw(frappe._("Amount must be greater than zero in Purpose Detail row {0}.").format(row.idx))

		purpose = frappe.get_cached_doc("Donation Purpose", row.donation_purpose)
		if purpose.is_group:
			frappe.throw(frappe._("Please select a leaf Donation Purpose in Purpose Detail row {0}.").format(row.idx))

		if purpose.purpose_group != row.donation_category:
			frappe.throw(
				frappe._("Donation Purpose {0} belongs to {1}, not {2}, in row {3}.").format(
					row.donation_purpose,
					purpose.purpose_group,
					row.donation_category,
					row.idx,
				)
			)

		if row.donation_category == SPONSORSHIP_PURPOSE and row.donation_purpose not in ALLOWED_SPONSORSHIP_PURPOSES:
			frappe.throw(
				frappe._(
					"Only Sponsorship - Student, Sponsorship - Prisoner, Sponsorship - MTC, or Sponsorship - Maktab can be selected for Sponsorship in row {0}."
				).format(row.idx)
			)

		row.purpose_path = purpose.purpose_path
		mapping = get_donation_purpose_account_mapping(
			self.company,
			row.donation_type,
			row.donation_purpose,
		)
		row.credit_account = mapping.get("credit_account")
		row.cost_center = mapping.get("cost_center")
		if not row.credit_account:
			frappe.throw(
				frappe._(
					"Credit Account mapping is required for Donation Purpose {0} and Donation Type {1} in row {2}."
				).format(row.donation_purpose, row.donation_type, row.idx)
			)

	def validate_purpose(self):
		if not self.donation_purpose:
			return

		purpose = frappe.get_cached_doc("Donation Purpose", self.donation_purpose)
		if purpose.is_group:
			frappe.throw(frappe._("Please select a leaf Donation Purpose, not a group."))

		if self.purpose_of_donation and purpose.purpose_group != self.purpose_of_donation:
			frappe.throw(
				frappe._("Donation Purpose {0} belongs to {1}, not {2}.").format(
					self.donation_purpose,
					purpose.purpose_group,
					self.purpose_of_donation,
				)
			)

	def validate_beneficiary(self):
		if self.is_sponsorship():
			self.student_name = None
			self.student_mode = None
			self.prisoner_name = None
			return

		if self.requires_student and not self.student_name:
			frappe.throw(frappe._("Student is required for the selected Donation Purpose."))

		if self.requires_prisoner and not self.prisoner_name:
			frappe.throw(frappe._("Prisoner is required for the selected Donation Purpose."))

		if not self.requires_student:
			self.student_name = None
			self.student_mode = None

		if not self.requires_prisoner:
			self.prisoner_name = None

	def set_sponsorship_allocations(self):
		if not self.is_sponsorship():
			self.sponsorship_students = []
			self.previous_sponsorship_balance = 0
			self.previous_balance_used = 0
			self.sponsorship_amount = 0
			self.available_allocation_amount = 0
			self.allocated_amount = 0
			self.unallocated_amount = 0
			self.total_program_amount = 0
			self.remaining_program_cost = 0
			self.allocation_status = None
			self.sponsored_student_count = 0
			self.total_sponsored_beneficiaries = 0
			self.total_covered_months = 0
			return

		if not self.donation_purpose:
			self.reset_sponsorship_summary()
			return

		if not self.sponsorship_students:
			frappe.throw(frappe._("At least one Sponsorship Allocation row is required."))

		self.auto_allocate_sponsorship_amounts()

		allocated_amount = 0
		total_program_amount = 0
		total_sponsored_beneficiaries = 0
		total_covered_months = 0
		program_modes = self.get_sponsorship_program_modes()

		for row in self.sponsorship_students:
			self.set_sponsorship_allocation_row(row, program_modes)
			allocated_amount += flt(row.allocated_amount)
			total_program_amount += flt(row.total_program_donation)
			quantity = cint(row.quantity)
			total_sponsored_beneficiaries += quantity
			total_covered_months += flt(row.covered_months)

		if allocated_amount > flt(self.available_allocation_amount):
			frappe.throw(
				frappe._("Allocated Amount {0} cannot be greater than Available Allocation Amount {1}.").format(
					frappe.format_value(allocated_amount, {"fieldtype": "Currency"}),
					frappe.format_value(self.available_allocation_amount, {"fieldtype": "Currency"}),
				)
			)

		self.allocated_amount = allocated_amount
		self.unallocated_amount = flt(self.available_allocation_amount) - allocated_amount
		self.sponsorship_amount = flt(self.get_sponsorship_purpose_amount())
		self.total_program_amount = total_program_amount
		prior_program_allocated = self.get_donor_program_prior_allocated_total()
		self.remaining_program_cost = max(
			total_program_amount - prior_program_allocated - allocated_amount, 0
		)
		self.set_allocation_status()
		self.sponsored_student_count = total_sponsored_beneficiaries
		self.total_sponsored_beneficiaries = total_sponsored_beneficiaries
		self.total_covered_months = total_covered_months

	def set_previous_sponsorship_balance(self):
		if not self.is_sponsorship():
			self.previous_sponsorship_balance = 0
			self.previous_balance_used = 0
			self.available_allocation_amount = 0
			return

		if not self.donor_name:
			self.previous_sponsorship_balance = 0
			self.previous_balance_used = 0
			self.available_allocation_amount = flt(self.get_sponsorship_purpose_amount())
			return

		self.previous_sponsorship_balance = self.get_donor_previous_sponsorship_balance()
		self.previous_balance_used = self.previous_sponsorship_balance
		self.available_allocation_amount = flt(self.get_sponsorship_purpose_amount()) + flt(self.previous_balance_used)

	def get_sponsorship_purpose_amount(self):
		return sum(
			flt(row.amount)
			for row in self.get("purpose_details", [])
			if row.donation_category == SPONSORSHIP_PURPOSE
		)

	def auto_allocate_sponsorship_amounts(self):
		rows = self.get("sponsorship_students") or []
		if not rows:
			return

		available = flt(self.available_allocation_amount)
		if available <= 0:
			return

		if len(rows) == 1:
			row = rows[0]
			if not row.sponsorship_program or cint(row.quantity) <= 0:
				return
			if flt(row.allocated_amount) > 0:
				return

			total_program = self.get_sponsorship_row_total_program_donation(row)
			row.allocated_amount = min(available, total_program)
			return

		remaining = available
		for row in rows:
			if flt(row.allocated_amount) > 0:
				remaining -= flt(row.allocated_amount)
				continue

			if not row.sponsorship_program or cint(row.quantity) <= 0:
				continue

			total_program = self.get_sponsorship_row_total_program_donation(row)
			row.allocated_amount = min(max(remaining, 0), total_program)
			remaining -= flt(row.allocated_amount)

	def get_sponsorship_row_total_program_donation(self, row):
		if flt(row.total_program_donation) > 0:
			return flt(row.total_program_donation)

		if not row.sponsorship_program:
			return 0

		program = frappe.get_cached_doc("Sponsorship Program", row.sponsorship_program)
		return flt(program.monthly_donation) * cint(program.duration_months) * cint(row.quantity)

	def get_donor_previous_sponsorship_balance(self):
		filters = {
			"donor_name": self.donor_name,
			"purpose_of_donation": SPONSORSHIP_PURPOSE,
			"name": ["!=", self.name],
			"docstatus": 1,
		}
		if self.donation_type:
			filters["donation_type"] = self.donation_type
		if not self.is_new() and self.creation:
			filters["creation"] = ["<", self.creation]

		donation_amount = frappe.db.get_value(
			"Donation Order",
			filters,
			"sum(donation_amount)",
		)
		allocated_amount = frappe.db.get_value(
			"Donation Order",
			filters,
			"sum(allocated_amount)",
		)
		return max(flt(donation_amount) - flt(allocated_amount), 0)

	def reset_sponsorship_summary(self):
		self.sponsorship_amount = flt(self.get_sponsorship_purpose_amount()) if self.is_sponsorship() else 0
		self.available_allocation_amount = flt(self.get_sponsorship_purpose_amount()) + flt(self.previous_balance_used)
		self.allocated_amount = 0
		self.unallocated_amount = self.available_allocation_amount if self.is_sponsorship() else 0
		self.total_program_amount = 0
		self.remaining_program_cost = 0
		self.allocation_status = "Unallocated" if self.is_sponsorship() else None
		self.sponsored_student_count = 0
		self.total_sponsored_beneficiaries = 0
		self.total_covered_months = 0

	def set_allocation_status(self):
		if not self.is_sponsorship():
			self.allocation_status = None
			return

		if flt(self.allocated_amount) <= 0:
			self.allocation_status = "Unallocated"
		elif flt(self.unallocated_amount) > 0:
			self.allocation_status = "Partially Allocated"
		else:
			self.allocation_status = "Fully Allocated"

	def get_sponsorship_program_modes(self):
		modes = {
			"student": False,
			"prisoner": False,
		}
		for row in self.get("purpose_details", []):
			if row.donation_category != SPONSORSHIP_PURPOSE:
				continue
			if row.donation_purpose == "Sponsorship - Prisoner":
				modes["prisoner"] = True
			else:
				modes["student"] = True
		return modes

	def set_sponsorship_allocation_row(self, row, program_modes):
		if cint(row.quantity) <= 0:
			frappe.throw(frappe._("Quantity must be greater than zero in Sponsorship Allocation rows."))
		if not row.sponsorship_program:
			frappe.throw(frappe._("Sponsorship Program is required in Sponsorship Allocation rows."))

		is_prisoner_program = is_prisoner_sponsorship_program(row.sponsorship_program)
		if is_prisoner_program and not program_modes["prisoner"]:
			frappe.throw(
				frappe._("Prisoner program {0} requires Sponsorship - Prisoner in Purpose Details.").format(
					row.sponsorship_program
				)
			)
		if not is_prisoner_program and not program_modes["student"]:
			frappe.throw(
				frappe._("Student program {0} requires a non-prisoner Sponsorship purpose in Purpose Details.").format(
					row.sponsorship_program
				)
			)

		self.set_sponsorship_row_program_details(
			row,
			quantity=cint(row.quantity),
			row_label="Sponsorship Allocation",
		)

	def set_sponsorship_row_program_details(self, row, quantity, row_label):
		if not row.sponsorship_program:
			frappe.throw(frappe._("Sponsorship Program is required in {0} rows.").format(row_label))

		program = frappe.get_cached_doc("Sponsorship Program", row.sponsorship_program)
		row.monthly_donation = flt(program.monthly_donation)
		row.duration_months = cint(program.duration_months)
		row.total_program_donation = flt(row.monthly_donation) * cint(row.duration_months) * quantity

		if flt(row.allocated_amount) <= 0:
			frappe.throw(frappe._("Allocated Amount must be greater than zero in {0} rows.").format(row_label))

		if flt(row.allocated_amount) > flt(row.total_program_donation):
			frappe.throw(
				frappe._("Allocated Amount cannot exceed Total Program Donation for row {0}.").format(row.idx)
			)

		monthly_total = flt(row.monthly_donation) * quantity
		total_days = cint(row.duration_months) * SPONSORSHIP_DAYS_IN_MONTH
		covered_days = 0
		if monthly_total:
			covered_days = min(
				cint(round((flt(row.allocated_amount) / monthly_total) * SPONSORSHIP_DAYS_IN_MONTH)),
				total_days,
			)
		remaining_days = max(total_days - covered_days, 0)
		row.covered_months = covered_days / SPONSORSHIP_DAYS_IN_MONTH
		row.remaining_months = remaining_days / SPONSORSHIP_DAYS_IN_MONTH
		row.covered_duration = format_sponsorship_duration(covered_days)
		row.remaining_duration = format_sponsorship_duration(remaining_days)
		prior_allocated = self.get_donor_program_prior_allocated(row.sponsorship_program)
		row.remaining_amount = max(
			flt(row.total_program_donation) - prior_allocated - flt(row.allocated_amount), 0
		)

	def get_donor_program_prior_allocated_map(self):
		programs = list(
			{
				row.sponsorship_program
				for row in self.get("sponsorship_students") or []
				if row.sponsorship_program
			}
		)
		if not programs or not self.donor_name:
			return {}

		filters = {
			"donor_name": self.donor_name,
			"docstatus": 1,
		}
		if not self.is_new():
			filters["name"] = ["!=", self.name]

		rows = frappe.db.sql(
			"""
			select
				dosa.sponsorship_program,
				ifnull(sum(dosa.allocated_amount), 0) as prior_allocated
			from `tabDonation Order Sponsorship Allocation` dosa
			inner join `tabDonation Order` do on do.name = dosa.parent
			where do.donor_name = %(donor_name)s
				and do.docstatus = 1
				and dosa.sponsorship_program in %(programs)s
				{exclude_clause}
			group by dosa.sponsorship_program
			""".format(
				exclude_clause="and do.name != %(exclude_order)s" if not self.is_new() else ""
			),
			{
				"donor_name": self.donor_name,
				"programs": programs,
				"exclude_order": self.name,
			},
			as_dict=True,
		)
		return {row.sponsorship_program: flt(row.prior_allocated) for row in rows}

	def get_donor_program_prior_allocated(self, sponsorship_program):
		if not sponsorship_program or not self.donor_name:
			return 0

		return self.get_donor_program_prior_allocated_map().get(sponsorship_program, 0)

	def get_donor_program_prior_allocated_total(self):
		prior_map = self.get_donor_program_prior_allocated_map()
		return sum(prior_map.values())

	def set_total_donation(self):
		if self.is_sponsorship():
			self.total_donation = flt(self.donation_amount)
			return

		if not self.student_name:
			self.total_donation = 0
			return

		existing_total = frappe.db.get_value(
			"Donation Order",
			{
				"student_name": self.student_name,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
			"sum(donation_amount)",
		)
		self.total_donation = flt(existing_total) + flt(self.donation_amount)

	def set_accounting_details(self):
		self.accounting_status = self.accounting_status or "Not Posted"

		if self.mode_of_payment and self.company:
			mode_details = get_mode_of_payment_account(self.company, self.mode_of_payment, self.donation_type)
			self.mode_of_payment_type = mode_details.get("mode_of_payment_type")
			if self.mode_of_payment_type == "Cash":
				self.bank_account = None
				if not self.debit_account or self.get_account_details(self.debit_account).account_type != "Cash":
					self.debit_account = get_default_cash_account(
						self.company,
						self.mode_of_payment,
					)
				for row in self.purpose_details:
					row.debit_account = self.debit_account
			elif self.is_deposit_account_mode():
				if not self.bank_account:
					self.bank_account = self.debit_account or self.get_first_purpose_debit_account()
				self.debit_account = self.bank_account
				for row in self.purpose_details:
					row.debit_account = self.bank_account
			elif self.is_bank_draft_mode():
				self.bank_account = None
				for row in self.purpose_details:
					if not row.debit_account:
						row_mode_details = get_mode_of_payment_account(
							self.company,
							self.mode_of_payment,
							row.donation_type,
						)
						row.debit_account = row_mode_details.get("debit_account")
				self.debit_account = self.get_first_purpose_debit_account()
			elif self.is_manual_bank_mode():
				self.bank_account = None
				if not self.debit_account or self.get_account_details(self.debit_account).account_type != "Bank":
					self.debit_account = mode_details.get("debit_account")
				for row in self.purpose_details:
					row.debit_account = self.debit_account
			else:
				if self.mode_of_payment_type != "Bank":
					self.bank_account = None
				for row in self.purpose_details:
					if not row.debit_account:
						row_mode_details = get_mode_of_payment_account(
							self.company,
							self.mode_of_payment,
							row.donation_type,
						)
						row.debit_account = row_mode_details.get("debit_account")
				if not self.debit_account:
					self.debit_account = self.get_first_purpose_debit_account() or mode_details.get("debit_account")
				if self.mode_of_payment_type == "Bank" and not self.bank_account:
					self.bank_account = self.debit_account
		else:
			self.mode_of_payment_type = None
			self.bank_account = None

		for row in self.purpose_details:
			if row.credit_account:
				continue
			mapping = get_donation_purpose_account_mapping(
				self.company,
				row.donation_type,
				row.donation_purpose,
			)
			row.credit_account = mapping.get("credit_account")
			row.cost_center = mapping.get("cost_center")

	def validate_accounting_details(self):
		if flt(self.donation_amount) <= 0:
			frappe.throw(frappe._("Donation Amount must be greater than zero."))

		if not self.company:
			frappe.throw(frappe._("Company is required for accounting."))

		if not self.mode_of_payment:
			frappe.throw(frappe._("Mode of Payment is required for accounting."))

		if self.mode_of_payment_type == "Cash":
			if not self.debit_account:
				frappe.throw(frappe._("Debit Account is required for accounting."))
			self.validate_account(self.debit_account, "Debit Account")
		elif self.is_deposit_account_mode():
			if not self.bank_account:
				frappe.throw(frappe._("Deposit Account is required for Mode of Payment {0}.").format(self.mode_of_payment))
			if self.debit_account != self.bank_account:
				frappe.throw(frappe._("Debit Account must match the selected Deposit Account."))
			self.validate_account(self.bank_account, "Deposit Account", allowed_account_types=("Bank",))
		elif self.is_manual_bank_mode() and not self.is_bank_draft_mode():
			if not self.debit_account:
				frappe.throw(frappe._("Debit Account is required for Mode of Payment {0}.").format(self.mode_of_payment))
			self.validate_account(self.debit_account, "Debit Account", allowed_account_types=("Bank",))
		elif not self.get_first_purpose_debit_account():
			frappe.throw(frappe._("Debit Account is required in each Purpose Detail row for non-cash payments."))

		for row in self.purpose_details:
			if not row.debit_account:
				frappe.throw(
					frappe._("Debit Account is required in Purpose Detail row {0}.").format(row.idx)
				)

			if self.mode_of_payment_type == "Cash":
				if row.debit_account != self.debit_account:
					frappe.throw(
						frappe._("Debit Account in Purpose Detail row {0} must match the Cash Debit Account.").format(
							row.idx
						)
					)
			else:
				if not row.debit_account:
					frappe.throw(
						frappe._("Debit Account is required in Purpose Detail row {0} for non-cash payments.").format(
							row.idx
						)
					)
				self.validate_account(row.debit_account, "Debit Account", allowed_account_types=self.get_allowed_debit_account_types())
				if self.is_deposit_account_mode() and row.debit_account != self.bank_account:
					frappe.throw(
						frappe._("Debit Account in Purpose Detail row {0} must match the selected Deposit Account.").format(
							row.idx
						)
					)
				if self.is_manual_bank_mode() and not self.is_bank_draft_mode() and row.debit_account != self.debit_account:
					frappe.throw(
						frappe._("Debit Account in Purpose Detail row {0} must match the selected Debit Account.").format(
							row.idx
						)
					)
				if self.is_bank_draft_mode():
					self.validate_bank_draft_debit_account(row.debit_account, row.donation_type, row.idx)

			if not row.credit_account:
				frappe.throw(
					frappe._(
						"Credit Account mapping is required for Donation Purpose {0} and Donation Type {1} in row {2}."
					).format(row.donation_purpose, row.donation_type, row.idx)
				)
			self.validate_account(
				row.credit_account,
				"Credit Account",
				allowed_root_types=("Income", "Liability", "Equity"),
			)

		if self.mode_of_payment_type == "Cash":
			if self.get_account_details(self.debit_account).account_type != "Cash":
				frappe.throw(
					frappe._("Debit Account must be a {0} account for Mode of Payment {1}.").format(
						"Cash",
						self.mode_of_payment,
					)
				)

	def validate_bank_draft_debit_account(self, debit_account, donation_type, row_idx=None):
		if not self.is_bank_draft_mode() or not debit_account or not donation_type:
			return

		if account_matches_donation_type(debit_account, donation_type):
			return

		expected_account_word = get_receiving_account_donation_type(donation_type)
		if row_idx:
			frappe.throw(
				frappe._("Debit Account in Purpose Detail row {0} must contain {1} for Donation Type {2}.").format(
					row_idx,
					expected_account_word,
					donation_type,
				)
			)

		frappe.throw(
			frappe._("Debit Account must contain {0} for Donation Type {1}.").format(
				expected_account_word,
				donation_type,
			)
		)

	def set_pdc_details(self):
		if self.is_bank_draft_mode():
			self.is_post_dated_cheque = 0
			self.cheque_deposit_date = None
			self.pdc_status = PDC_STATUS_NOT_APPLICABLE
			self.pdc_posted_on = None
			if not self.instrument_status:
				self.instrument_status = "Received"
			return

		if not self.is_cheque_mode():
			self.is_post_dated_cheque = 0
			self.cheque_number = None
			self.cheque_deposit_date = None
			self.pdc_status = PDC_STATUS_NOT_APPLICABLE
			self.pdc_posted_on = None
			self.instrument_status = None
			return

		if not self.cheque_number:
			frappe.throw(frappe._("Cheque Number is required for Cheque donations."))

		if not cint(self.is_post_dated_cheque):
			self.cheque_deposit_date = None
			self.pdc_status = PDC_STATUS_NOT_APPLICABLE
			self.pdc_posted_on = None
			if not self.instrument_status:
				self.instrument_status = "Received"
			return

		if not self.cheque_deposit_date:
			frappe.throw(frappe._("Cheque Deposit Date is required for Post-Dated Cheque donations."))

		if self.journal_entry or self.pdc_status == PDC_STATUS_DEPOSITED:
			self.pdc_status = PDC_STATUS_DEPOSITED
			if not self.instrument_status:
				self.instrument_status = "Encashed"
			return

		self.pdc_status = PDC_STATUS_PENDING
		self.accounting_status = "Not Posted"
		if not self.instrument_status:
			self.instrument_status = "Pending Encashment"

	def set_donor_information_request_audit(self):
		if not self.donor_information_request_status:
			self.requesting_user = None
			self.request_date = None
			return

		previous = self.get_doc_before_save()
		if previous and previous.donor_information_request_status == self.donor_information_request_status:
			return

		self.requesting_user = frappe.session.user
		self.request_date = now_datetime()

	def create_instrument_event_if_changed(self):
		if not self.instrument_status or self.mode_of_payment not in ("Cheque", "Bank Draft"):
			return

		previous = self.get_doc_before_save()
		if previous and previous.instrument_status == self.instrument_status:
			return

		event = frappe.get_doc(
			{
				"doctype": "Donation Instrument Event",
				"donation_order": self.name,
				"event_status": self.instrument_status,
				"user": frappe.session.user,
				"proof": self.instrument_proof,
				"crossing_stamp_confirmed": self.crossing_stamp_confirmed,
				"remarks": self.instrument_event_remarks or self.remarks,
			}
		)
		event.insert(ignore_permissions=True)

	def log_confidential_reference_changes(self):
		try:
			from donation_management.donation_management.confidential import log_confidential_changes

			log_confidential_changes(self, ("party", "referred_by_trustee", "confidential_ref_co"))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Donation Order confidential access logging failed")

	def get_allowed_debit_account_types(self):
		if self.mode_of_payment_type == "Cash":
			return ("Cash",)
		if self.is_deposit_account_mode() or self.mode_of_payment_type == "Bank":
			return ("Bank",)
		return None

	def get_first_purpose_debit_account(self):
		for row in self.get("purpose_details", []):
			if row.debit_account:
				return row.debit_account
		return None

	def validate_account(self, account, label, allowed_account_types=None, allowed_root_types=None):
		account_details = self.get_account_details(account)
		if not account_details:
			frappe.throw(frappe._("{0} {1} was not found.").format(label, account))

		if account_details.company != self.company:
			frappe.throw(
				frappe._("{0} {1} does not belong to Company {2}.").format(label, account, self.company)
			)

		if account_details.is_group:
			frappe.throw(frappe._("{0} {1} cannot be a group account.").format(label, account))

		if allowed_account_types and account_details.account_type not in allowed_account_types:
			frappe.throw(
				frappe._("{0} {1} must be one of these account types: {2}.").format(
					label,
					account,
					", ".join(allowed_account_types),
				)
			)

		if allowed_root_types and account_details.root_type not in allowed_root_types:
			frappe.throw(
				frappe._("{0} {1} must be one of these root types: {2}.").format(
					label,
					account,
					", ".join(allowed_root_types),
				)
			)

	def get_account_details(self, account):
		if not account:
			return frappe._dict()

		if not hasattr(self, "_account_details_cache"):
			self._account_details_cache = {}

		if account not in self._account_details_cache:
			self._account_details_cache[account] = frappe.db.get_value(
				"Account",
				account,
				["name", "company", "is_group", "account_type", "root_type"],
				as_dict=True,
			) or frappe._dict()

		return self._account_details_cache[account]

	def validate_posted_accounting_locked(self):
		old_doc = self.get_doc_before_save()
		if not old_doc or not old_doc.journal_entry:
			return

		journal_entry_status = frappe.db.get_value("Journal Entry", old_doc.journal_entry, "docstatus")
		if journal_entry_status != 1:
			return

		locked_fields = (
			"donor_name",
			"is_mohasil_collection",
			"mohasil",
			"donation_book_serial_no",
			"donation_book",
			"manual_receipt_number",
			"manual_receipt_date",
			"company",
			"donation_posting_date",
			"mode_of_payment",
			"bank_account",
			"debit_account",
			"is_post_dated_cheque",
			"cheque_number",
			"cheque_deposit_date",
			"pdc_status",
			"donation_type",
			"donation_purpose",
			"credit_account",
			"donation_amount",
		)
		for fieldname in locked_fields:
			if str(old_doc.get(fieldname) or "") != str(self.get(fieldname) or ""):
				frappe.throw(
					frappe._("Cannot change {0} after Journal Entry {1} has been posted.").format(
						self.meta.get_label(fieldname),
						old_doc.journal_entry,
					)
				)

		if self.get_purpose_signature(old_doc) != self.get_purpose_signature(self):
			frappe.throw(
				frappe._("Cannot change Purpose Details after Journal Entry {0} has been posted.").format(
					old_doc.journal_entry
				)
			)

	def get_purpose_signature(self, doc):
		return [
			(
				row.donation_type,
				row.donation_category,
				row.donation_purpose,
				flt(row.amount),
				row.debit_account,
				row.credit_account,
				row.cost_center,
			)
			for row in doc.get("purpose_details", [])
		]

	def create_journal_entry(self, force_pdc=False):
		if self.docstatus != 1:
			return

		if self.is_pending_pdc() and not force_pdc:
			return

		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			self.set_accounting_status_from_journal_entry()
			return

		existing_journal_entry = frappe.db.get_value(
			"Journal Entry",
			{
				"user_remark": ["in", [self.get_journal_entry_user_remark(), self.get_legacy_journal_entry_user_remark()]],
				"docstatus": ["!=", 2],
			},
			"name",
		)
		if existing_journal_entry:
			self.set_gl_entry_party(existing_journal_entry)
			self.set_accounting_fields(existing_journal_entry, "Posted")
			return

		default_cost_center = self.accounting_cost_center or frappe.db.get_value(
			"Company",
			self.company,
			"cost_center",
		)
		accounts = []
		if self.mode_of_payment_type == "Cash":
			accounts.append(
				self.get_journal_entry_account_row(
					account=self.debit_account,
					debit=flt(self.donation_amount),
					credit=0,
					cost_center=default_cost_center,
				)
			)
		else:
			for row in self.purpose_details:
				accounts.append(
					self.get_journal_entry_account_row(
						account=row.debit_account,
						debit=flt(row.amount),
						credit=0,
						cost_center=row.cost_center or default_cost_center,
					)
				)

		for row in self.purpose_details:
			accounts.append(
				self.get_journal_entry_account_row(
					account=row.credit_account,
					debit=0,
					credit=flt(row.amount),
					cost_center=row.cost_center or default_cost_center,
				)
			)

		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(self.donation_posting_date),
				"pay_to_recd_from": self.get_journal_entry_received_from(),
				"user_remark": self.get_journal_entry_user_remark(),
				"accounts": accounts,
			}
		)
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.set_accounting_fields(entry.name, "Posted")

	def get_journal_entry_account_row(self, account, debit, credit, cost_center=None):
		row = {
			"account": account,
			"debit_in_account_currency": debit,
			"credit_in_account_currency": credit,
			"party_type": "Donor",
			"party": self.donor_name,
			"user_remark": "Donor: {0}".format(self.donor_name),
		}

		if cost_center:
			row["cost_center"] = cost_center

		return row

	def get_journal_entry_user_remark(self):
		return "Donation Order: {0} | Donor: {1}".format(self.name, self.donor_name)

	def get_legacy_journal_entry_user_remark(self):
		return "Donation Order: {0}".format(self.name)

	def get_journal_entry_received_from(self):
		donor_name = frappe.db.get_value("Donor", self.donor_name, "customer_name")
		return "{0} ({1})".format(donor_name or self.donor_name, self.donor_name)

	def set_accounting_fields(self, journal_entry, status):
		frappe.db.set_value(
			self.doctype,
			self.name,
			{
				"journal_entry": journal_entry,
				"accounting_status": status,
			},
			update_modified=False,
		)
		self.journal_entry = journal_entry
		self.accounting_status = status
		self.set_receipt_status()

	def set_receipt_status(self):
		if not self.meta.has_field("receipt_status"):
			return
		status = "Issued" if self.computerized_receipt else get_receipt_eligibility_status(self)
		if self.get("receipt_status") != status:
			frappe.db.set_value(self.doctype, self.name, "receipt_status", status, update_modified=False)
			self.receipt_status = status

	def set_accounting_status_from_journal_entry(self):
		docstatus = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
		status = "Posted" if docstatus == 1 else "Cancelled" if docstatus == 2 else "Not Posted"
		self.set_accounting_fields(self.journal_entry, status)

	def cancel_linked_journal_entry(self):
		if not self.journal_entry or not frappe.db.exists("Journal Entry", self.journal_entry):
			return

		entry = frappe.get_doc("Journal Entry", self.journal_entry)
		if entry.docstatus == 1:
			entry.cancel()
			self.accounting_status = "Cancelled"

	def set_gl_entry_party(self, journal_entry):
		# Backfill entries created before Donor was stored on every Journal Entry row.
		frappe.db.sql(
			"""
			update `tabJournal Entry Account`
			set party_type = %s,
				party = %s
			where parent = %s
			""",
			("Donor", self.donor_name, journal_entry),
		)
		frappe.db.sql(
			"""
			update `tabGL Entry`
			set party_type = %s,
				party = %s
			where voucher_type = 'Journal Entry'
				and voucher_no = %s
				and ifnull(is_cancelled, 0) = 0
			""",
			("Donor", self.donor_name, journal_entry),
		)


def get_existing_manual_receipt_order(manual_receipt_number, current_order=None):
	manual_receipt_number = str(manual_receipt_number or "").strip()
	if not manual_receipt_number:
		return None

	values = {"manual_receipt_number": manual_receipt_number}
	exclude_parent = ""
	exclude_detail = ""
	if current_order and not str(current_order).startswith("new-"):
		values["current_order"] = current_order
		exclude_parent = "and name != %(current_order)s"
		exclude_detail = "and parent.name != %(current_order)s"

	existing = frappe.db.sql(
		"""
		select existing_order.name
		from (
			select name
			from `tabDonation Order`
			where docstatus != 2
				{exclude_parent}
				and manual_receipt_number = %(manual_receipt_number)s
			union
			select parent.name
			from `tabDonation Order` parent
			inner join `tabDonation Order Purpose Detail` detail
				on detail.parent = parent.name
			where parent.docstatus != 2
				{exclude_detail}
				and detail.manual_receipt_number = %(manual_receipt_number)s
		) existing_order
		limit 1
		""".format(
			exclude_parent=exclude_parent,
			exclude_detail=exclude_detail,
		),
		values,
	)
	return existing[0][0] if existing else None


def get_receipt_eligibility_status(doc):
	if doc.docstatus == 2:
		return "Cancelled"
	if doc.docstatus != 1:
		return "Pending"

	policy = frappe.db.get_single_value("Donation Settings", "receipt_timing_policy") or "After Deposit"
	if policy == "Before Handover":
		return "Eligible"

	if doc.mode_of_payment_type == "Cash":
		return "Eligible" if is_donation_order_deposited(doc.name) else "Blocked"

	if doc.mode_of_payment in (CHEQUE_MODE_OF_PAYMENT, BANK_DRAFT_MODE_OF_PAYMENT):
		return "Eligible" if doc.instrument_status == "Encashed" else "Blocked"

	return "Eligible" if doc.accounting_status == "Posted" else "Blocked"


def is_donation_order_deposited(donation_order):
	if frappe.db.get_value("Donation Order", donation_order, "bank_deposit_status") == "Deposited":
		return True

	return bool(
		frappe.db.sql(
			"""
			select closing.name
			from `tabDonation Closing Detail` detail
			inner join `tabDonation Closing` closing
				on closing.name = detail.parent
			where detail.source_doctype = 'Donation Order'
				and detail.source_name = %(donation_order)s
				and closing.docstatus = 1
				and closing.status = 'Deposited'
			limit 1
			""",
			{"donation_order": donation_order},
		)
	)


@frappe.whitelist()
def issue_computerized_receipt(donation_order):
	doc = frappe.get_doc("Donation Order", donation_order)
	doc.check_permission("write")

	if doc.docstatus != 1:
		frappe.throw(frappe._("Donation Order must be submitted before issuing the computerized receipt."))
	if doc.computerized_receipt:
		return {
			"receipt_status": "Issued",
			"computerized_receipt": doc.computerized_receipt,
		}

	status = get_receipt_eligibility_status(doc)
	if status != "Eligible":
		frappe.throw(frappe._("Computerized receipt cannot be issued yet. Current status: {0}.").format(status))

	issued_on = now_datetime()
	frappe.db.set_value(
		"Donation Order",
		doc.name,
		{
			"computerized_receipt": doc.name,
			"receipt_status": "Issued",
			"computerized_receipt_issued_on": issued_on,
			"computerized_receipt_issued_by": frappe.session.user,
			"manual_receipt_reconciliation_status": "Converted"
			if doc.manual_receipt_number
			else doc.manual_receipt_reconciliation_status,
		},
		update_modified=False,
	)
	return {
		"receipt_status": "Issued",
		"computerized_receipt": doc.name,
		"issued_on": issued_on,
	}


@frappe.whitelist()
def check_manual_receipt_duplicate(
	donation_book=None,
	donation_book_serial_no=None,
	manual_receipt_number=None,
	current_order=None,
):
	manual_receipt_number = str(manual_receipt_number or "").strip()
	if not donation_book_serial_no or not manual_receipt_number:
		return {"exists": False}

	if not donation_book:
		donation_book = frappe.db.get_value(
			"Book Assignment Detail",
			{
				"book_serial_no": donation_book_serial_no,
				"parenttype": "Book",
				"parentfield": "assigned_books",
			},
			"parent",
		)

	if not donation_book:
		return {"exists": False}

	detail_serial_condition = "and parent.donation_book_serial_no = %(donation_book_serial_no)s"
	parent_serial_condition = "and donation_book_serial_no = %(donation_book_serial_no)s"
	exclude_condition = ""
	values = {
		"donation_book": donation_book,
		"donation_book_serial_no": donation_book_serial_no,
		"manual_receipt_number": manual_receipt_number,
	}
	if current_order and not str(current_order).startswith("new-"):
		exclude_condition = "and {alias}.name != %(current_order)s"
		values["current_order"] = current_order

	detail_exclude_condition = exclude_condition.format(alias="parent") if exclude_condition else ""
	parent_exclude_condition = exclude_condition.format(alias="`tabDonation Order`") if exclude_condition else ""

	existing = frappe.db.sql(
		"""
		select existing_order.name
		from (
			select parent.name
			from `tabDonation Order` parent
			inner join `tabDonation Order Purpose Detail` detail
				on detail.parent = parent.name
			where parent.donation_book = %(donation_book)s
				and parent.docstatus != 2
				{detail_exclude_condition}
				{detail_serial_condition}
				and detail.manual_receipt_number = %(manual_receipt_number)s
			union
			select name
			from `tabDonation Order`
			where donation_book = %(donation_book)s
				and docstatus != 2
				{parent_exclude_condition}
				{parent_serial_condition}
				and manual_receipt_number = %(manual_receipt_number)s
		) existing_order
		limit 1
		""".format(
			detail_exclude_condition=detail_exclude_condition,
			parent_exclude_condition=parent_exclude_condition,
			detail_serial_condition=detail_serial_condition,
			parent_serial_condition=parent_serial_condition,
		),
		values,
	)

	if not existing:
		global_existing = get_existing_manual_receipt_order(manual_receipt_number, current_order=current_order)
		if not global_existing:
			return {"exists": False}
		existing_order = global_existing
	else:
		existing_order = existing[0][0]

	return {
		"exists": True,
		"donation_order": existing_order,
	}


@frappe.whitelist()
def create_pdc_journal_entry(donation_order):
	doc = frappe.get_doc("Donation Order", donation_order)
	doc.check_permission("write")

	if not doc.is_cheque_mode() or not cint(doc.is_post_dated_cheque):
		frappe.throw(frappe._("Create Payment Entry is only available for post-dated cheque Donation Orders."))

	if doc.docstatus != 1:
		frappe.throw(frappe._("Donation Order must be submitted before creating Journal Entry."))

	if doc.pdc_status != PDC_STATUS_PENDING:
		frappe.throw(frappe._("Only pending PDC Donation Orders can be deposited."))

	if doc.journal_entry:
		frappe.throw(frappe._("Payment Entry already exists for this Donation Order."))

	if getdate(doc.cheque_deposit_date) > getdate(today()):
		frappe.throw(
			frappe._("Cheque can only be deposited on or after {0}.").format(
				frappe.format_value(doc.cheque_deposit_date, {"fieldtype": "Date"})
			)
		)

	doc.create_journal_entry(force_pdc=True)
	if not doc.journal_entry:
		frappe.throw(frappe._("Payment Entry could not be created for this Donation Order."))

	posted_on = now_datetime()
	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"pdc_status": PDC_STATUS_DEPOSITED,
			"pdc_posted_on": posted_on,
			"instrument_status": "Encashed",
			"receipt_status": "Eligible",
		},
		update_modified=False,
	)
	doc.pdc_status = PDC_STATUS_DEPOSITED
	doc.pdc_posted_on = posted_on
	doc.instrument_status = "Encashed"

	return {
		"journal_entry": doc.journal_entry,
	}
