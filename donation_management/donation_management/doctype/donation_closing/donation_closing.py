# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_time, getdate, now_datetime

from donation_management.donation_management.api import get_default_company
from donation_management.donation_management.notifications import notify_finance, notify_users


class DonationClosing(Document):
	def validate(self):
		self.set_company_default()
		self.set_prepared_by()
		self.set_cashier()
		self.set_totals()
		self.validate_closing_details()

	def set_prepared_by(self):
		if not self.prepared_by:
			self.prepared_by = frappe.session.user

	def set_cashier(self):
		if not self.cashier:
			self.cashier = self.prepared_by or frappe.session.user

	def on_submit(self):
		if not self.closing_details:
			frappe.throw(frappe._("Add at least one pending cash donation before submitting."))
		if self.status != "Received" or not self.received_by:
			frappe.throw(frappe._("Donation Closing must be received before submission."))
		self.validate_cash_handover()

		self.status = "Deposited"
		self.submitted_by = frappe.session.user
		self.submitted_on = now_datetime()
		self.db_set("status", self.status, update_modified=False)
		self.db_set("submitted_by", self.submitted_by, update_modified=False)
		self.db_set("submitted_on", self.submitted_on, update_modified=False)
		self.mark_sources_as_deposited()
		notify_finance(
			frappe._("Donation Closing Deposited"),
			frappe._("Donation Closing {0} has been submitted and deposited.").format(self.name),
			self.doctype,
			self.name,
		)

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", self.status, update_modified=False)
		self.reset_source_deposit_status()
		notify_finance(
			frappe._("Donation Closing Cancelled"),
			frappe._("Donation Closing {0} has been cancelled.").format(self.name),
			self.doctype,
			self.name,
		)

	def validate_cash_handover(self):
		if not self.total_amount:
			return

		if not self.cash_handover:
			frappe.throw(frappe._("Cash Handover is required before submitting Donation Closing."))

		handover = frappe.db.get_value(
			"Donation Cash Handover",
			self.cash_handover,
			["docstatus", "status", "amount", "variance"],
			as_dict=True,
		)
		if not handover:
			frappe.throw(frappe._("Cash Handover {0} was not found.").format(self.cash_handover))
		if handover.docstatus != 1 or handover.status != "Received":
			frappe.throw(frappe._("Cash Handover must be submitted and Received before closing."))
		if flt(handover.amount) < flt(self.total_amount):
			frappe.throw(frappe._("Cash Handover Amount cannot be less than Donation Closing total."))
		if flt(handover.variance):
			frappe.throw(frappe._("Cash Handover variance must be resolved before closing."))
		self.validate_cash_handover_cutoff()

	def validate_cash_handover_cutoff(self):
		cutoff_time = frappe.db.get_single_value("Donation Settings", "closing_cutoff_time")
		if not cutoff_time or not self.closing_date:
			return

		now = now_datetime()
		if getdate(self.closing_date) == getdate(now) and now.time() > get_time(cutoff_time):
			frappe.msgprint(
				frappe._("Closing is being submitted after configured cut-off time {0}.").format(cutoff_time),
				alert=True,
			)

	def set_company_default(self):
		if not self.company:
			self.company = get_default_company()

	def set_totals(self):
		self.total_amount = sum(flt(row.amount) for row in self.closing_details or [])
		self.pending_items_count = len(self.closing_details or [])

	def validate_closing_details(self):
		seen = set()
		for row in self.closing_details or []:
			key = (row.source_doctype, row.source_name)
			if key in seen:
				frappe.throw(
					frappe._("Duplicate entry for {0} {1}.").format(row.source_doctype, row.source_name)
				)
			seen.add(key)

			if is_source_in_active_closing(row.source_doctype, row.source_name, exclude=self.name):
				frappe.throw(
					frappe._("{0} {1} is already included in another active Donation Closing.").format(
						row.source_doctype,
						row.source_name,
					)
				)

	@frappe.whitelist()
	def fetch_pending_cash_donations(self):
		self.set_company_default()
		if not self.closing_date:
			frappe.throw(frappe._("Closing Date is required before fetching pending cash donations."))

		closing_date = getdate(self.closing_date)
		pending = get_pending_cash_donations(
			self.company,
			closing_date=closing_date,
			exclude_closing=self.name,
			cashier=get_fetch_cashier(),
		)
		self.closing_details = []

		for item in pending:
			posting_date = item.get("posting_date")
			if posting_date:
				posting_date = getdate(posting_date)

			self.append(
				"closing_details",
				{
					"source_doctype": item["source_doctype"],
					"source_name": item["source_name"],
					"donation_type": item.get("donation_type"),
					"amount": item.get("amount"),
					"posting_date": posting_date,
					"remarks": item.get("remarks"),
				},
			)

		self.set_totals()

		if not pending:
			return {
				"count": 0,
				"total_amount": 0,
				"message": frappe._("No pending cash donations were found."),
			}

		self.save()
		return {
			"count": self.pending_items_count,
			"total_amount": self.total_amount,
			"name": self.name,
			"closing_details": get_closing_details_payload(self),
		}

	@frappe.whitelist()
	def receive_closing(self):
		if self.is_new():
			frappe.throw(frappe._("Save Donation Closing before receiving it."))
		if self.docstatus != 0:
			frappe.throw(frappe._("Only draft Donation Closing can be received."))
		if self.status not in ("", "Draft"):
			frappe.throw(frappe._("Only Draft Donation Closing can be received."))
		if not self.closing_details:
			frappe.throw(frappe._("Add at least one pending cash donation before receiving."))

		self.received_by = frappe.session.user
		self.received_on = now_datetime()
		self.status = "Received"
		self.save(ignore_permissions=True)
		notify_finance(
			frappe._("Donation Closing Received"),
			frappe._("Donation Closing {0} is received and awaiting deposit submission.").format(self.name),
			self.doctype,
			self.name,
		)
		notify_users(
			frappe._("Donation Closing Received"),
			frappe._("Your Donation Closing {0} has been received.").format(self.name),
			users=[self.cashier],
			reference_doctype=self.doctype,
			reference_name=self.name,
		)
		return self.name

	def mark_sources_as_deposited(self):
		for row in self.closing_details or []:
			if row.source_doctype == "Donation Order" and frappe.db.has_column(
				"Donation Order", "bank_deposit_status"
			):
				frappe.db.set_value(
					"Donation Order",
					row.source_name,
					"bank_deposit_status",
					"Deposited",
					update_modified=False,
				)

	def reset_source_deposit_status(self):
		for row in self.closing_details or []:
			if row.source_doctype != "Donation Order":
				continue

			if frappe.db.get_value("Donation Order", row.source_name, "bank_deposit_status") == "Deposited":
				frappe.db.set_value(
					"Donation Order",
					row.source_name,
					"bank_deposit_status",
					"Pending Bank Deposit",
					update_modified=False,
				)

def get_closing_details_payload(doc):
	return [
		{
			"source_doctype": row.source_doctype,
			"source_name": row.source_name,
			"donation_type": row.donation_type,
			"amount": row.amount,
			"posting_date": row.posting_date,
			"remarks": row.remarks,
		}
		for row in doc.closing_details or []
	]


def get_fetch_cashier():
	if frappe.has_role(("Finance Manager", "CFO", "Donation Manager", "System Manager")):
		return None
	return frappe.session.user


def get_pending_cash_donations(company=None, closing_date=None, exclude_closing=None, cashier=None):
	company = company or get_default_company()
	closing_date = getdate(closing_date) if closing_date else None
	pending = []
	pending.extend(get_pending_donation_orders(company, closing_date, exclude_closing, cashier=cashier))
	pending.extend(get_pending_box_collections(company, closing_date, exclude_closing, cashier=cashier))
	pending.extend(get_pending_books(company, closing_date, exclude_closing, cashier=cashier))
	return pending


def get_pending_donation_orders(company, closing_date=None, exclude_closing=None, cashier=None):
	filters = {
		"docstatus": 1,
		"company": company,
		"mode_of_payment_type": "Cash",
		"accounting_status": "Posted",
	}
	if closing_date:
		filters["donation_posting_date"] = [
			"between",
			[
				"{0} 00:00:00".format(closing_date),
				"{0} 23:59:59".format(closing_date),
			],
		]
	if cashier:
		filters["owner"] = cashier

	orders = frappe.get_all(
		"Donation Order",
		filters=filters,
		fields=[
			"name",
			"donation_amount",
			"donation_type",
			"donation_posting_date",
			"bank_deposit_status",
		],
		order_by="donation_posting_date asc",
	)

	result = []
	for order in orders:
		deposit_status = order.bank_deposit_status or "Not Applicable"
		if deposit_status == "Deposited":
			continue

		if is_source_in_active_closing("Donation Order", order.name, exclude=exclude_closing):
			continue

		result.append(
			{
				"source_doctype": "Donation Order",
				"source_name": order.name,
				"donation_type": order.donation_type,
				"amount": order.donation_amount,
				"posting_date": getdate(order.donation_posting_date)
				if order.donation_posting_date
				else None,
				"remarks": order.name,
			}
		)
	return result


def get_pending_box_collections(company, closing_date=None, exclude_closing=None, cashier=None):
	cashier_condition = ""
	values = {"company": company, "closing_date": closing_date}
	if cashier:
		cashier_condition = "and collection_log.owner = %(cashier)s"
		values["cashier"] = cashier

	collections = frappe.db.sql(
		"""
		select
			collection_log.name,
			collection_log.box_collection,
			collection_log.collected_amount,
			collection_log.donation_head,
			collection_log.action_date,
			collection_log.journal_entry
		from `tabBox Collection Log` collection_log
		inner join `tabBox Collection` box_collection
			on box_collection.name = collection_log.box_collection
		inner join `tabJournal Entry` journal_entry
			on journal_entry.name = collection_log.journal_entry
			and journal_entry.docstatus = 1
		where box_collection.docstatus = 1
			and box_collection.company = %(company)s
			and collection_log.action = 'Collection'
			and (%(closing_date)s is null or date(collection_log.action_date) = %(closing_date)s)
			{cashier_condition}
			and ifnull(collection_log.collected_amount, 0) > 0
			and not exists (
				select 1
				from `tabBox Collection Log` newer_log
				where newer_log.box_collection = collection_log.box_collection
					and newer_log.action = 'Collection'
					and (
						newer_log.action_date > collection_log.action_date
						or (
							newer_log.action_date = collection_log.action_date
							and newer_log.creation > collection_log.creation
						)
					)
			)
		order by collection_log.action_date asc, collection_log.creation asc
		""".format(cashier_condition=cashier_condition),
		values,
		as_dict=True,
	)

	result = []
	for collection in collections:
		if is_source_in_active_closing("Box Collection Log", collection.name, exclude=exclude_closing):
			continue
		result.append(
			{
				"source_doctype": "Box Collection Log",
				"source_name": collection.name,
				"donation_type": collection.donation_head,
				"amount": collection.collected_amount,
				"posting_date": getdate(collection.action_date),
				"remarks": "{0} | {1}".format(collection.box_collection, collection.name),
			}
		)
	return result


def get_pending_books(company, closing_date=None, exclude_closing=None, cashier=None):
	cashier_condition = ""
	values = {"company": company, "closing_date": closing_date}
	if cashier:
		cashier_condition = "and book.owner = %(cashier)s"
		values["cashier"] = cashier

	books = frappe.db.sql(
		"""
		select
			book.name,
			book.collected_amount,
			book.coupon_type,
			journal_entry.posting_date
		from `tabBook` book
		inner join `tabJournal Entry` journal_entry
			on journal_entry.name = book.journal_entry
			and journal_entry.docstatus = 1
		where book.status in ('Returned', 'Closed')
			and book.book_type = 'Coupon Book'
			and book.company = %(company)s
			and book.accounting_status = 'Posted'
			and (%(closing_date)s is null or journal_entry.posting_date = %(closing_date)s)
			{cashier_condition}
		order by journal_entry.posting_date asc, book.creation asc
		""".format(cashier_condition=cashier_condition),
		values,
		as_dict=True,
	)

	result = []
	for book in books:
		if is_source_in_active_closing("Book", book.name, exclude=exclude_closing):
			continue
		result.append(
			{
				"source_doctype": "Book",
				"source_name": book.name,
				"donation_type": book.coupon_type,
				"amount": book.collected_amount,
				"posting_date": book.posting_date,
				"remarks": book.name,
			}
		)
	return result


def is_source_in_active_closing(source_doctype, source_name, exclude=None):
	filters = {
		"parenttype": "Donation Closing",
		"source_doctype": source_doctype,
		"source_name": source_name,
	}
	rows = frappe.get_all("Donation Closing Detail", filters=filters, fields=["parent"])
	for row in rows:
		closing_status = frappe.db.get_value("Donation Closing", row.parent, ["docstatus", "status"], as_dict=True)
		if not closing_status:
			continue
		if exclude and row.parent == exclude:
			continue
		if closing_status.docstatus == 1 and closing_status.status not in ("Cancelled",):
			return True
	return False
