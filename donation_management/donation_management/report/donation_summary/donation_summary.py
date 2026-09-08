# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from erpnext.accounts.utils import get_currency_precision, get_fiscal_year
from frappe import _
from frappe.utils import flt, get_first_day, getdate


ACCOUNTING_STATUSES = ("Posted", "Pending", "All")
DONATION_TYPES = ("Zakat", "Atiya", "Sadqa")
PREFERRED_TRANSACTION_TYPES = (
	"Cash",
	"Cheque",
	"Bank Draft",
	"Credit Card",
	"Card Payment",
	"Wire Transfer",
	"Box Collection",
	"Coupon",
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	currency = frappe.db.get_value("Company", filters.company, "default_currency")
	fiscal_year = get_fiscal_year(filters.to_date, company=filters.company, verbose=0)
	fiscal_year_start = getdate(fiscal_year[1])
	month_start = get_first_day(filters.to_date)
	query_start = min(getdate(filters.from_date), fiscal_year_start, month_start)

	receipts, reconciliations = get_receipts(
		company=filters.company,
		from_date=query_start,
		to_date=filters.to_date,
		accounting_status=filters.accounting_status,
	)
	validate_posted_accounting(reconciliations, filters.company)

	period_receipts = filter_receipts(receipts, filters.from_date, filters.to_date)
	fiscal_ytd_receipts = filter_receipts(receipts, fiscal_year_start, filters.to_date)
	mtd_receipts = filter_receipts(receipts, month_start, filters.to_date)

	return (
		get_columns(currency),
		get_data(period_receipts, fiscal_ytd_receipts, mtd_receipts),
	)


def validate_filters(filters):
	for fieldname, label in (
		("company", _("Company")),
		("from_date", _("From Date")),
		("to_date", _("To Date")),
	):
		if not filters.get(fieldname):
			frappe.throw(_("{0} is required.").format(label))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	filters.accounting_status = filters.get("accounting_status") or "Posted"
	if filters.accounting_status not in ACCOUNTING_STATUSES:
		frappe.throw(_("Accounting Status must be Posted, Pending, or All."))


def get_columns(currency):
	return [
		{"label": _("#"), "fieldname": "row_number", "fieldtype": "Int", "width": 55},
		{
			"label": _("Transaction Type"),
			"fieldname": "summary_label",
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"label": _("No. of Receipts"),
			"fieldname": "receipt_count",
			"fieldtype": "Int",
			"width": 180,
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"options": currency,
			"width": 220,
		},
	]


def get_receipts(company, from_date, to_date, accounting_status):
	receipts = []
	reconciliations = {}

	order_receipts, order_reconciliations = get_donation_order_receipts(
		company, from_date, to_date, accounting_status
	)
	box_receipts, box_reconciliations = get_box_collection_receipts(
		company, from_date, to_date, accounting_status
	)
	coupon_receipts, coupon_reconciliations = get_coupon_receipts(
		company, from_date, to_date, accounting_status
	)

	receipts.extend(order_receipts)
	receipts.extend(box_receipts)
	receipts.extend(coupon_receipts)
	reconciliations.update(order_reconciliations)
	reconciliations.update(box_reconciliations)
	reconciliations.update(coupon_reconciliations)

	return receipts, reconciliations


def get_donation_order_receipts(company, from_date, to_date, accounting_status):
	rows = get_source_rows(
		"""
		select
			donation_order.name,
			donation_order.donation_posting_date as operational_date,
			coalesce(donation_order.donation_location, donation_order.location) as location,
			donation_order.mode_of_payment,
			donation_order.donation_amount,
			donation_order.accounting_status,
			donation_order.journal_entry,
			journal_entry.posting_date as journal_posting_date,
			journal_entry.docstatus as journal_docstatus
		from `tabDonation Order` donation_order
		left join `tabJournal Entry` journal_entry
			on journal_entry.name = donation_order.journal_entry
		where donation_order.company = %(company)s
			and donation_order.docstatus = 1
		""",
		"donation_order.donation_posting_date",
		company,
		from_date,
		to_date,
		accounting_status,
	)
	if not rows:
		return [], {}

	purpose_rows = frappe.get_all(
		"Donation Order Purpose Detail",
		filters={
			"parent": ["in", [row.name for row in rows]],
			"parenttype": "Donation Order",
			"parentfield": "purpose_details",
		},
		fields=["parent", "donation_type", "amount"],
		order_by="parent, idx",
		limit_page_length=0,
	)
	allocations = defaultdict(lambda: defaultdict(float))
	for row in purpose_rows:
		allocations[row.parent][row.donation_type] += flt(row.amount)

	receipts = []
	reconciliations = {}
	for row in rows:
		donation_allocations = dict(allocations.get(row.name, {}))
		purpose_total = sum(donation_allocations.values())
		assert_amount_matches(
			purpose_total,
			row.donation_amount,
			_("Donation Order {0} purpose total").format(row.name),
		)

		status = get_row_accounting_status(row)
		receipt = {
			"receipt_id": "Donation Order:{0}".format(row.name),
			"source_type": "Donation Order",
			"source_name": row.name,
			"transaction_type": row.mode_of_payment or _("Unspecified"),
			"territory": row.location or _("Unspecified"),
			"amount": flt(row.donation_amount),
			"donation_allocations": donation_allocations,
			"accounting_status": status,
			"effective_date": get_effective_date(row, status),
			"journal_entry": row.journal_entry,
		}
		receipts.append(receipt)
		add_reconciliation(
			reconciliations,
			source_type="Donation Order",
			source_name=row.name,
			journal_entry=row.journal_entry,
			amount=row.donation_amount,
			status=status,
		)

	return receipts, reconciliations


def get_box_collection_receipts(company, from_date, to_date, accounting_status):
	rows = get_source_rows(
		"""
		select
			collection_log.name,
			collection_log.action_date as operational_date,
			collection_log.donation_head,
			collection_log.collected_amount,
			collection_log.journal_entry,
			journal_entry.posting_date as journal_posting_date,
			journal_entry.docstatus as journal_docstatus
		from `tabBox Collection Log` collection_log
		inner join `tabBox Collection` box_collection
			on box_collection.name = collection_log.box_collection
		left join `tabJournal Entry` journal_entry
			on journal_entry.name = collection_log.journal_entry
		where box_collection.company = %(company)s
			and box_collection.docstatus = 1
			and collection_log.action = 'Collection'
		""",
		"collection_log.action_date",
		company,
		from_date,
		to_date,
		accounting_status,
		has_accounting_status=False,
	)

	receipts = []
	reconciliations = {}
	for row in rows:
		status = get_row_accounting_status(row)
		receipt = {
			"receipt_id": "Box Collection Log:{0}".format(row.name),
			"source_type": "Box Collection",
			"source_name": row.name,
			"transaction_type": "Box Collection",
			"territory": None,
			"amount": flt(row.collected_amount),
			"donation_allocations": {row.donation_head: flt(row.collected_amount)},
			"accounting_status": status,
			"effective_date": get_effective_date(row, status),
			"journal_entry": row.journal_entry,
		}
		receipts.append(receipt)
		add_reconciliation(
			reconciliations,
			source_type="Box Collection Log",
			source_name=row.name,
			journal_entry=row.journal_entry,
			amount=row.collected_amount,
			status=status,
		)

	return receipts, reconciliations


def get_coupon_receipts(company, from_date, to_date, accounting_status):
	rows = get_source_rows(
		"""
		select
			coupon.name,
			coupon.posting_date as operational_date,
			coupon.book,
			coupon.amount,
			book.coupon_type,
			book.collected_amount as book_collected_amount,
			book.accounting_status,
			book.journal_entry,
			journal_entry.posting_date as journal_posting_date,
			journal_entry.docstatus as journal_docstatus
		from `tabCoupon` coupon
		inner join `tabBook` book
			on book.name = coupon.book
		left join `tabJournal Entry` journal_entry
			on journal_entry.name = book.journal_entry
		where book.company = %(company)s
			and book.book_type = 'Coupon Book'
			and book.status in ('Returned', 'Closed')
			and coupon.docstatus != 2
		""",
		"coupon.posting_date",
		company,
		from_date,
		to_date,
		accounting_status,
	)
	if not rows:
		return [], {}

	book_names = list({row.book for row in rows})
	book_coupon_totals = {
		row.book: flt(row.total_amount)
		for row in frappe.db.sql(
			"""
			select book, sum(amount) as total_amount
			from `tabCoupon`
			where book in %(book_names)s
				and docstatus != 2
			group by book
			""",
			{"book_names": tuple(book_names)},
			as_dict=True,
		)
	}

	receipts = []
	reconciliations = {}
	for row in rows:
		status = get_row_accounting_status(row)
		assert_amount_matches(
			book_coupon_totals.get(row.book, 0),
			row.book_collected_amount,
			_("Book {0} coupon total").format(row.book),
		)

		receipt = {
			"receipt_id": "Coupon:{0}".format(row.name),
			"source_type": "Coupon",
			"source_name": row.name,
			"transaction_type": "Coupon",
			"territory": None,
			"amount": flt(row.amount),
			"donation_allocations": {row.coupon_type: flt(row.amount)},
			"accounting_status": status,
			"effective_date": get_effective_date(row, status),
			"journal_entry": row.journal_entry,
		}
		receipts.append(receipt)
		add_reconciliation(
			reconciliations,
			source_type="Book",
			source_name=row.book,
			journal_entry=row.journal_entry,
			amount=row.book_collected_amount,
			status=status,
		)

	return receipts, reconciliations


def get_source_rows(
	base_query,
	operational_date_field,
	company,
	from_date,
	to_date,
	accounting_status,
	has_accounting_status=True,
):
	values = {
		"company": company,
		"from_date": getdate(from_date),
		"to_date": getdate(to_date),
	}
	queries = []

	if accounting_status in ("Posted", "All"):
		queries.append(
			"""
			{0}
				and journal_entry.docstatus = 1
				and journal_entry.posting_date between %(from_date)s and %(to_date)s
			""".format(base_query)
		)

	if accounting_status in ("Pending", "All"):
		pending_status_condition = ""
		if has_accounting_status:
			pending_status_condition = "and ifnull(accounting_status, 'Not Posted') = 'Not Posted'"
		queries.append(
			"""
			{0}
				and (journal_entry.name is null or journal_entry.docstatus = 0)
				{1}
				and date({2}) between %(from_date)s and %(to_date)s
			""".format(base_query, pending_status_condition, operational_date_field)
		)

	rows = []
	for query in queries:
		rows.extend(frappe.db.sql(query, values, as_dict=True))
	return rows


def get_row_accounting_status(row):
	return "Posted" if row.journal_docstatus == 1 else "Pending"


def get_effective_date(row, accounting_status):
	if accounting_status == "Posted":
		return getdate(row.journal_posting_date)
	return getdate(row.operational_date)


def add_reconciliation(
	reconciliations,
	source_type,
	source_name,
	journal_entry,
	amount,
	status,
):
	if status != "Posted":
		return

	key = "{0}:{1}".format(source_type, source_name)
	reconciliations[key] = {
		"source_type": source_type,
		"source_name": source_name,
		"journal_entry": journal_entry,
		"amount": flt(amount),
	}


def validate_posted_accounting(reconciliations, company):
	if not reconciliations:
		return

	journal_entries = [row["journal_entry"] for row in reconciliations.values()]
	if len(journal_entries) != len(set(journal_entries)):
		frappe.throw(
			_(
				"Donation Summary cannot be generated because one Journal Entry is linked to multiple source transactions."
			)
		)

	journal_entry_rows = {
		row.name: row
		for row in frappe.get_all(
			"Journal Entry",
			filters={"name": ["in", journal_entries]},
			fields=["name", "company", "docstatus"],
			limit_page_length=0,
		)
	}
	journal_totals = get_journal_entry_totals(journal_entries)
	gl_totals = get_gl_entry_totals(journal_entries)
	errors = []

	for row in reconciliations.values():
		journal_entry = journal_entry_rows.get(row["journal_entry"])
		label = "{0} {1}".format(row["source_type"], row["source_name"])
		if not journal_entry or journal_entry.docstatus != 1:
			errors.append(_("{0}: linked Journal Entry is not submitted.").format(label))
			continue
		if journal_entry.company != company:
			errors.append(
				_("{0}: Journal Entry belongs to a different company.").format(label)
			)
			continue

		journal_debit, journal_credit = journal_totals.get(journal_entry.name, (0, 0))
		gl_debit, gl_credit = gl_totals.get(journal_entry.name, (0, 0))
		expected_amount = row["amount"]

		if not amounts_match(journal_debit, expected_amount) or not amounts_match(
			journal_credit, expected_amount
		):
			errors.append(
				_("{0}: Journal Entry {1} does not match source amount {2}.").format(
					label,
					journal_entry.name,
					frappe.format_value(expected_amount, {"fieldtype": "Currency"}),
				)
			)
			continue

		if not amounts_match(gl_debit, journal_debit) or not amounts_match(
			gl_credit, journal_credit
		):
			errors.append(
				_("{0}: General Ledger does not match Journal Entry {1}.").format(
					label,
					journal_entry.name,
				)
			)

	if errors:
		frappe.throw(
			_("Donation Summary accounting validation failed:<br>{0}").format(
				"<br>".join(errors[:20])
			)
		)


def get_journal_entry_totals(journal_entries):
	return {
		row.parent: (flt(row.debit), flt(row.credit))
		for row in frappe.db.sql(
			"""
			select parent, sum(debit) as debit, sum(credit) as credit
			from `tabJournal Entry Account`
			where parent in %(journal_entries)s
			group by parent
			""",
			{"journal_entries": tuple(journal_entries)},
			as_dict=True,
		)
	}


def get_gl_entry_totals(journal_entries):
	return {
		row.voucher_no: (flt(row.debit), flt(row.credit))
		for row in frappe.db.sql(
			"""
			select voucher_no, sum(debit) as debit, sum(credit) as credit
			from `tabGL Entry`
			where voucher_type = 'Journal Entry'
				and voucher_no in %(journal_entries)s
				and ifnull(is_cancelled, 0) = 0
			group by voucher_no
			""",
			{"journal_entries": tuple(journal_entries)},
			as_dict=True,
		)
	}


def assert_amount_matches(actual, expected, label):
	if amounts_match(actual, expected):
		return
	frappe.throw(
		_("{0} does not match the recorded amount. Expected {1}, found {2}.").format(
			label,
			frappe.format_value(expected, {"fieldtype": "Currency"}),
			frappe.format_value(actual, {"fieldtype": "Currency"}),
		)
	)


def amounts_match(first, second):
	precision = get_currency_precision() or 2
	return flt(first, precision) == flt(second, precision)


def filter_receipts(receipts, from_date, to_date):
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	return [
		receipt
		for receipt in receipts
		if from_date <= getdate(receipt["effective_date"]) <= to_date
	]


def get_data(period_receipts, fiscal_ytd_receipts, mtd_receipts):
	rows = []
	row_number = 0

	def add_row(
		label="",
		receipt_count=None,
		total_amount=None,
		is_section=False,
		is_total=False,
		is_summary=False,
		is_detail=False,
		numbered=True,
	):
		nonlocal row_number
		if numbered:
			row_number += 1
		rows.append(
			{
				"row_number": row_number if numbered else None,
				"summary_label": label,
				"receipt_count": receipt_count,
				"total_amount": total_amount,
				"is_section": is_section,
				"is_total": is_total,
				"is_summary": is_summary,
				"is_detail": is_detail,
			}
		)

	transaction_groups = aggregate_receipts(period_receipts, "transaction_type")
	add_row(_("Transaction Type"), is_section=True)
	for transaction_type in sort_transaction_types(transaction_groups):
		group = transaction_groups[transaction_type]
		add_row(
			transaction_type,
			group["receipt_count"],
			group["total_amount"],
			is_detail=True,
		)
	add_row(
		_("Total"),
		len({receipt["receipt_id"] for receipt in period_receipts}),
		sum(flt(receipt["amount"]) for receipt in period_receipts),
		is_total=True,
	)

	add_row(numbered=False)
	order_receipts = [
		receipt for receipt in period_receipts if receipt["source_type"] == "Donation Order"
	]
	territory_groups = aggregate_receipts(order_receipts, "territory")
	add_row(_("Territory (Donation Orders Only)"), is_section=True)
	for territory in sorted(territory_groups):
		group = territory_groups[territory]
		add_row(
			territory,
			group["receipt_count"],
			group["total_amount"],
			is_detail=True,
		)
	add_row(
		_("Total"),
		len({receipt["receipt_id"] for receipt in order_receipts}),
		sum(flt(receipt["amount"]) for receipt in order_receipts),
		is_total=True,
	)

	add_row(numbered=False)
	add_row(_("Donation Type"), is_section=True)
	type_receipts = set()
	type_total = 0
	for donation_type in DONATION_TYPES:
		receipt_ids = set()
		amount = 0
		for receipt in period_receipts:
			type_amount = flt(receipt["donation_allocations"].get(donation_type))
			if not type_amount:
				continue
			receipt_ids.add(receipt["receipt_id"])
			type_receipts.add(receipt["receipt_id"])
			amount += type_amount
		type_total += amount
		add_row(donation_type, len(receipt_ids), amount, is_detail=True)
	add_row(_("Total"), len(type_receipts), type_total, is_total=True)

	add_row(numbered=False)
	add_row(
		_("Period Total"),
		len({receipt["receipt_id"] for receipt in period_receipts}),
		sum(flt(receipt["amount"]) for receipt in period_receipts),
		is_summary=True,
	)
	add_row(
		_("YTD"),
		len({receipt["receipt_id"] for receipt in fiscal_ytd_receipts}),
		sum(flt(receipt["amount"]) for receipt in fiscal_ytd_receipts),
		is_summary=True,
	)
	add_row(
		_("MTD"),
		len({receipt["receipt_id"] for receipt in mtd_receipts}),
		sum(flt(receipt["amount"]) for receipt in mtd_receipts),
		is_summary=True,
	)

	return rows


def aggregate_receipts(receipts, key):
	groups = defaultdict(lambda: {"receipt_ids": set(), "total_amount": 0})
	for receipt in receipts:
		group_name = receipt.get(key) or _("Unspecified")
		groups[group_name]["receipt_ids"].add(receipt["receipt_id"])
		groups[group_name]["total_amount"] += flt(receipt["amount"])

	return {
		group_name: {
			"receipt_count": len(group["receipt_ids"]),
			"total_amount": group["total_amount"],
		}
		for group_name, group in groups.items()
	}


def sort_transaction_types(groups):
	preferred_order = {
		transaction_type: index
		for index, transaction_type in enumerate(PREFERRED_TRANSACTION_TYPES)
	}
	return sorted(
		groups,
		key=lambda transaction_type: (
			preferred_order.get(transaction_type, len(preferred_order)),
			transaction_type,
		),
	)
