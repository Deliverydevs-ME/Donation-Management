# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class DonationBookLeaf(Document):
	def validate(self):
		self.validate_parent_assignment_state()
		self.validate_locked_state()
		self.validate_donation_order_link()
		self.validate_used_leaf_details()
		self.validate_journal_entry()
		self.validate_unique_leaf()

	def before_submit(self):
		self.validate_parent_assignment_state()
		if self.status == "Cancelled":
			frappe.throw(frappe._("A cancelled Donation Book Leaf cannot be submitted."))

	def before_cancel(self):
		if self.status == "Cancelled":
			return

		if self.donation_order and self.journal_entry:
			frappe.throw(
				frappe._(
					"A submitted Donation Book Leaf linked to Donation Order {0} and Journal Entry {1} "
					"cannot be cancelled directly. Cancel the Donation Order through its approved process."
				).format(self.donation_order, self.journal_entry)
			)

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=False)

	def validate_parent_assignment_state(self):
		if not self.book:
			return

		assignment = frappe.db.get_value(
			"Book Assignment",
			self.book,
			["name", "docstatus"],
			as_dict=True,
		)
		if assignment and assignment.docstatus == 2:
			frappe.throw(
				frappe._(
					"Donation Book Leaf {0} belongs to cancelled Book Assignment {1} and cannot be edited or submitted."
				).format(self.name or self.receipt_number, self.book)
			)

	def validate_locked_state(self):
		if self.status != "Cancelled" or self.is_new():
			return

		previous = self.get_doc_before_save()
		if previous and previous.status == "Cancelled":
			frappe.throw(frappe._("Cancelled Donation Book Leaves cannot be edited."))

	def validate_donation_order_link(self):
		if not self.donation_order:
			return

		order = frappe.db.get_value(
			"Donation Order",
			self.donation_order,
			[
				"name",
				"docstatus",
				"donor_name",
				"donation_book",
				"donation_book_serial_no",
				"manual_receipt_number",
				"manual_receipt_date",
				"mode_of_payment",
				"journal_entry",
				"accounting_status",
				"donation_amount",
				"donation_book_leaf",
			],
			as_dict=True,
		)
		if not order:
			frappe.throw(frappe._("Donation Order {0} was not found.").format(self.donation_order))
		if order.docstatus == 2:
			frappe.throw(frappe._("Cancelled Donation Orders cannot be linked to a Donation Book Leaf."))
		if order.donation_book and order.donation_book != self.book:
			frappe.throw(frappe._("Donation Book Leaf must belong to the Donation Book on the selected Donation Order."))
		if order.donation_book_serial_no and order.donation_book_serial_no != self.book_serial_no:
			frappe.throw(frappe._("Donation Book Leaf must belong to the Donation Book Serial No on the selected Donation Order."))
		if order.donation_book_leaf and order.donation_book_leaf != self.name:
			frappe.throw(
				frappe._("Donation Order {0} is linked to another Donation Book Leaf.").format(self.donation_order)
			)

		receipts = [order.manual_receipt_number]
		receipts.extend(
		row.manual_receipt_number
		for row in frappe.get_all(
			"Donation Order Purpose Detail",
			filters={"parent": self.donation_order, "parenttype": "Donation Order"},
			fields=["manual_receipt_number"],
		)
		if row.manual_receipt_number
	)
		if self.receipt_number not in receipts:
			frappe.throw(
				frappe._(
					"Receipt {0} is not used by Donation Order {1}. Select the Donation Order "
					"that uses this receipt, or select this Donation Book Leaf from the Donation Order."
				).format(
					self.receipt_number,
					self.donation_order,
				)
			)

		self.donor = order.donor_name
		self.payment_mode = order.mode_of_payment
		self.manual_receipt_date = order.manual_receipt_date
		self.journal_entry = order.journal_entry
		self.accounting_status = order.accounting_status
		self.amount = order.donation_amount
		if order.docstatus == 1:
			self.status = "Used"

	def validate_journal_entry(self):
		if not self.journal_entry:
			return

		if not self.donor:
			frappe.throw(frappe._("Select a Donor before selecting a Journal Entry."))

		journal_entry = frappe.db.get_value(
			"Journal Entry",
			self.journal_entry,
			["name", "docstatus"],
			as_dict=True,
		)
		if not journal_entry or journal_entry.docstatus == 2:
			frappe.throw(frappe._("Journal Entry {0} was not found or is cancelled.").format(self.journal_entry))

		if not frappe.db.exists(
			"Journal Entry Account",
			{
				"parent": self.journal_entry,
				"parenttype": "Journal Entry",
				"parentfield": "accounts",
				"party_type": "Donor",
				"party": self.donor,
			},
		):
			frappe.throw(
				frappe._("Journal Entry {0} is not related to Donor {1}.").format(
					self.journal_entry,
					self.donor,
				)
			)

	def validate_used_leaf_details(self):
		if self.status != "Used":
			return

		missing = []
		if not self.donor:
			missing.append(frappe._("Donor"))
		if not self.manual_receipt_date:
			missing.append(frappe._("Manual Receipt Date"))
		if missing:
			frappe.throw(
				frappe._("{0} is required when Donation Book Leaf is marked Used.").format(
					", ".join(missing)
				)
			)

	def validate_unique_leaf(self):
		if not self.book or not self.receipt_number:
			return

		existing = frappe.db.sql(
			"""
			select name
			from `tabDonation Book Leaf`
			where book = %(book)s
				and ifnull(book_serial_no, '') = %(book_serial_no)s
				and receipt_number = %(receipt_number)s
				and name != %(name)s
			limit 1
			""",
			{
				"book": self.book,
				"book_serial_no": self.book_serial_no or "",
				"receipt_number": self.receipt_number,
				"name": self.name or "",
			},
		)
		if existing:
			frappe.throw(
				frappe._("Receipt Number {0} already exists for Book {1}.").format(
					self.receipt_number,
					self.book,
				)
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_donor_journal_entries(doctype, txt, searchfield, start, page_len, filters):
	"""Return only non-cancelled Journal Entries whose accounts reference the selected Donor."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else frappe._dict(filters or {})
	donor = filters.get("donor")
	if not donor:
		return []

	journal_entry_names = frappe.get_all(
		"Journal Entry Account",
		filters={
			"parenttype": "Journal Entry",
			"parentfield": "accounts",
			"party_type": "Donor",
			"party": donor,
		},
		pluck="parent",
	)
	if not journal_entry_names:
		return []

	query_kwargs = {
		"filters": {
			"name": ["in", list(set(journal_entry_names))],
			"docstatus": ["!=", 2],
		},
		"fields": ["name", "user_remark"],
		"order_by": "posting_date desc, name desc",
		"start": cint(start),
		"page_length": cint(page_len),
	}
	if txt:
		search_text = f"%{txt}%"
		query_kwargs["or_filters"] = [
			{"name": ["like", search_text]},
			{"user_remark": ["like", search_text]},
		]

	entries = frappe.get_list("Journal Entry", **query_kwargs)
	return [(entry.name, entry.user_remark or entry.name) for entry in entries]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_donor_donation_orders(doctype, txt, searchfield, start, page_len, filters):
	"""Return Donation Orders belonging to the selected donor, led by their order number."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else frappe._dict(filters or {})
	donor = filters.get("donor")
	if not donor:
		return []

	search_text = f"%{txt}%"
	book = filters.get("book") or ""
	book_serial_no = filters.get("book_serial_no") or ""
	receipt_number = filters.get("receipt_number") or ""
	return frappe.db.sql(
		"""
		select
			order_doc.name,
			order_doc.name as label,
			order_doc.donor_name,
			order_doc.donation_posting_date
		from `tabDonation Order` order_doc
		where order_doc.donor_name = %(donor)s
			and order_doc.docstatus != 2
			and (%(book)s = '' or order_doc.donation_book = %(book)s)
			and (%(book_serial_no)s = '' or order_doc.donation_book_serial_no = %(book_serial_no)s)
			and (
				%(receipt_number)s = ''
				or order_doc.manual_receipt_number = %(receipt_number)s
				or exists (
					select 1
					from `tabDonation Order Purpose Detail` purpose_detail
					where purpose_detail.parent = order_doc.name
						and purpose_detail.parenttype = 'Donation Order'
						and purpose_detail.parentfield = 'purpose_details'
						and purpose_detail.manual_receipt_number = %(receipt_number)s
				)
			)
			and (
				order_doc.name like %(search)s
				or order_doc.donor_name like %(search)s
			)
		order by order_doc.modified desc, order_doc.name desc
		limit %(start)s, %(page_len)s
		""",
		{
			"donor": donor,
			"book": book,
			"book_serial_no": book_serial_no,
			"receipt_number": receipt_number,
			"search": search_text,
			"start": cint(start),
			"page_len": cint(page_len),
		},
	)


def cancel_leaf_for_donation_order(donation_order, clear_journal_entry=True):
	"""Mark all leaves for a cancelled order as cancelled without cancelling the leaf document again."""
	if not donation_order or not frappe.db.table_exists("Donation Book Leaf"):
		return

	leaves = frappe.get_all(
		"Donation Book Leaf",
		filters={"donation_order": donation_order},
		pluck="name",
		ignore_permissions=True,
	)
	for leaf in leaves:
		values = {"status": "Cancelled"}
		if clear_journal_entry:
			values.update({"journal_entry": None, "accounting_status": "Cancelled"})
		frappe.db.set_value("Donation Book Leaf", leaf, values, update_modified=False)


def cancel_leaves_for_book_assignment(book):
	"""Lock all generated leaves when their parent Book Assignment is cancelled."""
	if not book or not frappe.db.table_exists("Donation Book Leaf"):
		return

	frappe.db.sql(
		"""
		update `tabDonation Book Leaf`
		set status = 'Cancelled'
		where book = %s
		""",
		book,
	)
