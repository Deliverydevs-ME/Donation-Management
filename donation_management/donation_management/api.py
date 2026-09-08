import re

import frappe
from frappe.utils import cint, flt, getdate

from donation_management.donation_management.doctype.donor.donor import normalize_phone
from donation_management.donation_management.doctype.donation_location_assignment.donation_location_assignment import (
	get_effective_donation_location as get_effective_donation_location_from_assignment,
)


DONOR_FIELDS = [
	"name",
	"customer_name",
	"donor_email",
	"donor_phone_number",
	"referred_by_trustee",
	"mohasil",
	"customer_pos_id",
	"party",
	"confidential_ref_co",
	"donor_information_request_status",
]


def format_donor_response(donor):
	if not donor:
		return {}

	return {
		"name": donor.name,
		"donor_name": donor.customer_name,
		"donor_email": donor.donor_email,
		"donor_phone_number": donor.donor_phone_number,
		"referred_by_trustee": donor.referred_by_trustee,
		"mohasil": donor.mohasil,
		"donor_pos_id": donor.get("customer_pos_id"),
		"party": donor.get("party"),
		"confidential_ref_co": donor.get("confidential_ref_co"),
		"donor_information_request_status": donor.get("donor_information_request_status"),
	}


@frappe.whitelist()
def get_donor_by_email(donor_email=None):
	if not donor_email:
		return {}

	donor_email = donor_email.strip().lower()
	if "@" not in donor_email:
		return {"invalid": 1}

	donor = frappe.db.get_value("Donor", {"donor_email": donor_email}, DONOR_FIELDS, as_dict=True)
	if not donor:
		return {}

	return format_donor_response(donor)


@frappe.whitelist()
def get_donor_by_cnic(donor_cnic=None):
	# Deprecated: CNIC lookup removed for donors. Kept for backward compatibility.
	return {}


@frappe.whitelist()
def get_donor_by_phone(donor_phone_number=None):
	if not donor_phone_number:
		return {}

	donor_phone_digits = normalize_phone(donor_phone_number)
	if len(donor_phone_digits) < 10:
		return {"invalid": 1}

	donor = frappe.db.get_value(
		"Donor",
		{"donor_phone_digits": donor_phone_digits},
		DONOR_FIELDS,
		as_dict=True,
	)
	if not donor:
		return {}

	return format_donor_response(donor)


@frappe.whitelist()
def get_donor_details(donor=None):
	if not donor:
		return {}

	donor_details = frappe.db.get_value("Donor", donor, DONOR_FIELDS, as_dict=True)
	return format_donor_response(donor_details)


@frappe.whitelist()
def get_donor_esaal_e_sawab(donor=None):
	if not donor:
		return []

	return frappe.get_all(
		"Esaal E Sawab Detail",
		filters={
			"parenttype": "Donor",
			"parent": donor,
			"parentfield": "esaal_e_sawab",
		},
		fields=["person_name", "relationship", "remarks"],
		order_by="idx asc",
	)


@frappe.whitelist()
def get_effective_donation_location(employee=None, donation_date=None):
	return get_effective_donation_location_from_assignment(employee, donation_date)


@frappe.whitelist()
def find_family_donors(phone_number=None, address=None):
	filters = {}
	phone_digits = normalize_phone(phone_number)
	if phone_digits:
		filters["donor_phone_digits"] = phone_digits

	or_filters = []
	if address:
		or_filters.append(["Donor", "primary_address", "like", f"%{address}%"])

	if not filters and not or_filters:
		return []

	return frappe.get_all(
		"Donor",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer_name", "donor_phone_number", "primary_address", "parent_donor", "family_relationship"],
		limit_page_length=20,
	)


@frappe.whitelist()
def get_donor_program_enrollments(donor=None):
	if not donor:
		return []

	enrollments = frappe.get_all(
		"Donor Program Enrollment",
		filters={"donor": donor},
		fields=[
			"name",
			"sponsorship_program",
			"donation_purpose",
			"student_quantity",
			"last_donation_order",
		],
		order_by="sponsorship_program asc",
	)

	for enrollment in enrollments:
		enrich_donor_program_enrollment(enrollment, donor)

	return enrollments


def enrich_donor_program_enrollment(enrollment, donor):
	program_name = enrollment.sponsorship_program
	quantity = cint(enrollment.student_quantity) or 1

	program = frappe.db.get_value(
		"Sponsorship Program",
		program_name,
		["monthly_donation", "duration_months", "total_program_donation"],
		as_dict=True,
	) or {}

	monthly_donation = flt(program.get("monthly_donation"))
	duration_months = cint(program.get("duration_months"))
	total_program_amount = monthly_donation * duration_months * quantity

	total_paid = frappe.db.sql(
		"""
		select ifnull(sum(dosa.allocated_amount), 0)
		from `tabDonation Order Sponsorship Allocation` dosa
		inner join `tabDonation Order` do on do.name = dosa.parent
		where do.donor_name = %s
			and do.docstatus = 1
			and dosa.sponsorship_program = %s
		""",
		(donor, program_name),
	)[0][0]

	enrollment.update(
		{
			"program_label": program_name,
			"purpose_label": enrollment.donation_purpose or "",
			"monthly_donation": monthly_donation,
			"duration_months": duration_months,
			"total_program_amount": total_program_amount,
			"total_paid": flt(total_paid),
			"balance": max(total_program_amount - flt(total_paid), 0),
		}
	)


@frappe.whitelist()
def get_donor_program_donation_details(donor=None, sponsorship_program=None):
	if not donor or not sponsorship_program:
		frappe.throw(frappe._("Donor and Sponsorship Program are required."))

	enrollment = frappe.db.get_value(
		"Donor Program Enrollment",
		{"donor": donor, "sponsorship_program": sponsorship_program},
		["name", "donation_purpose", "student_quantity", "last_donation_order"],
		as_dict=True,
	)
	if not enrollment:
		frappe.throw(frappe._("Donor is not enrolled in program {0}.").format(sponsorship_program))

	enrich_donor_program_enrollment(enrollment, donor)

	purpose_details = []
	sponsorship_row = {
		"sponsorship_program": sponsorship_program,
		"quantity": cint(enrollment.student_quantity) or 1,
	}

	last_order_name = enrollment.last_donation_order
	if last_order_name and frappe.db.exists("Donation Order", last_order_name):
		last_order = frappe.get_doc("Donation Order", last_order_name)
		purpose_details = [
			{
				"donation_type": row.donation_type,
				"donation_category": row.donation_category,
				"donation_purpose": row.donation_purpose,
				"purpose_path": row.purpose_path,
			}
			for row in last_order.get("purpose_details", [])
			if row.donation_category == "Sponsorship"
		]

		for row in last_order.get("sponsorship_students", []):
			if row.sponsorship_program == sponsorship_program:
				sponsorship_row = {
					"sponsorship_program": row.sponsorship_program,
					"quantity": cint(row.quantity) or cint(enrollment.student_quantity) or 1,
				}
				break

	if not purpose_details:
		donation_purpose = enrollment.donation_purpose
		if not donation_purpose:
			frappe.throw(
				frappe._("Donation Purpose is missing for enrollment in program {0}.").format(sponsorship_program)
			)

		donation_type = get_last_donation_type_for_program(donor, sponsorship_program)
		purpose_path = frappe.db.get_value("Donation Purpose", donation_purpose, "purpose_path")
		purpose_details = [
			{
				"donation_type": donation_type,
				"donation_category": "Sponsorship",
				"donation_purpose": donation_purpose,
				"purpose_path": purpose_path,
			}
		]

	return {
		"sponsorship_program": sponsorship_program,
		"student_quantity": sponsorship_row["quantity"],
		"donation_purpose": purpose_details[0].get("donation_purpose"),
		"purpose_of_donation": "Sponsorship",
		"donation_type": purpose_details[0].get("donation_type"),
		"purpose_details": purpose_details,
		"sponsorship_students": [sponsorship_row],
		"total_program_amount": enrollment.total_program_amount,
		"total_paid": enrollment.total_paid,
		"balance": enrollment.balance,
	}


def get_last_donation_type_for_program(donor, sponsorship_program):
	donation_type = frappe.db.sql(
		"""
		select do.donation_type
		from `tabDonation Order` do
		inner join `tabDonation Order Sponsorship Allocation` dosa on dosa.parent = do.name
		where do.donor_name = %s
			and dosa.sponsorship_program = %s
			and do.docstatus = 1
			and ifnull(do.donation_type, '') != ''
		order by do.donation_posting_date desc, do.creation desc
		limit 1
		""",
		(donor, sponsorship_program),
	)
	return donation_type[0][0] if donation_type else None


@frappe.whitelist()
def get_donor_program_quantity(donor=None, sponsorship_program=None):
	if not donor or not sponsorship_program:
		return 0

	quantity = frappe.db.get_value(
		"Donor Program Enrollment",
		{"donor": donor, "sponsorship_program": sponsorship_program},
		"student_quantity",
	)
	return quantity or 0


@frappe.whitelist()
def safe_getdoctype(doctype=None, with_parent=False, cached_timestamp=None):
	"""Guard against client calls missing doctype (prevents Data Import list crash)."""
	if not doctype:
		frappe.response.docs = []
		return

	from frappe.desk.form.load import getdoctype

	return getdoctype(doctype, with_parent=with_parent, cached_timestamp=cached_timestamp)


@frappe.whitelist()
def get_student_total_donation(student_name=None, student=None, exclude_donation_order=None):
	student_name = student_name or student
	if not student_name:
		return 0

	filters = {
		"student_name": student_name,
		"docstatus": ["!=", 2],
	}
	if exclude_donation_order:
		filters["name"] = ["!=", exclude_donation_order]

	total_donation = frappe.db.get_value(
		"Donation Order",
		filters,
		"sum(donation_amount)",
	)
	return total_donation or 0


@frappe.whitelist()
def get_donor_program_prior_allocated(donor=None, sponsorship_programs=None, exclude_donation_order=None):
	if not donor:
		return {}

	if isinstance(sponsorship_programs, str):
		programs = frappe.parse_json(sponsorship_programs)
	else:
		programs = sponsorship_programs or []

	programs = [program for program in programs if program]
	if not programs:
		return {}

	exclude_clause = ""
	values = [donor, *programs]
	if exclude_donation_order:
		exclude_clause = "and do.name != %s"
		values.append(exclude_donation_order)

	placeholders = ", ".join(["%s"] * len(programs))
	rows = frappe.db.sql(
		f"""
		select
			dosa.sponsorship_program,
			ifnull(sum(dosa.allocated_amount), 0) as prior_allocated
		from `tabDonation Order Sponsorship Allocation` dosa
		inner join `tabDonation Order` do on do.name = dosa.parent
		where do.donor_name = %s
			and do.docstatus = 1
			and dosa.sponsorship_program in ({placeholders})
			{exclude_clause}
		group by dosa.sponsorship_program
		""",
		values,
		as_dict=True,
	)

	return {row.sponsorship_program: flt(row.prior_allocated) for row in rows}


@frappe.whitelist()
def get_donor_previous_sponsorship_balance(donor=None, donation_type=None, exclude_donation_order=None):
	if not donor or not donation_type:
		return 0

	filters = {
		"donor_name": donor,
		"donation_type": donation_type,
		"purpose_of_donation": "Sponsorship",
		"docstatus": 1,
	}
	if exclude_donation_order:
		filters["name"] = ["!=", exclude_donation_order]

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


@frappe.whitelist()
def get_donation_order_accounting_details(
	company=None,
	donation_type=None,
	donation_purpose=None,
	mode_of_payment=None,
):
	company = company or get_default_company()
	details = {
		"company": company,
		"mode_of_payment_type": None,
		"debit_account": None,
		"credit_account": None,
		"cost_center": None,
		"currency": None,
	}

	if company:
		details["currency"] = frappe.db.get_value("Company", company, "default_currency")

	if mode_of_payment and company:
		mode_details = get_mode_of_payment_account(company, mode_of_payment, donation_type)
		details.update(mode_details)

	if donation_purpose and donation_type and company:
		mapping = get_donation_purpose_account_mapping(company, donation_type, donation_purpose)
		details.update(mapping)

	return details


def get_default_company():
	return (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)


def get_mode_of_payment_account(company, mode_of_payment, donation_type=None):
	mode_of_payment_type = frappe.db.get_value("Mode of Payment", mode_of_payment, "type")
	default_account = frappe.db.get_value(
		"Mode of Payment Account",
		{
			"parent": mode_of_payment,
			"company": company,
		},
		"default_account",
	)

	if mode_of_payment_type == "Cash":
		default_account = get_default_cash_account(company, mode_of_payment)
	elif mode_of_payment == "Bank Draft" and mode_of_payment_type == "Bank" and donation_type:
		default_account = get_donation_type_receiving_account(company, mode_of_payment_type, donation_type, default_account)

	return {
		"mode_of_payment_type": mode_of_payment_type,
		"debit_account": default_account,
	}


def get_donation_type_receiving_account(company, account_type, donation_type, preferred_account=None):
	receiving_account_type = get_receiving_account_donation_type(donation_type)
	if preferred_account and account_matches_donation_type(preferred_account, donation_type):
		return preferred_account

	filters = {
		"company": company,
		"is_group": 0,
		"account_type": account_type,
		"account_name": ["like", "%{0}%".format(receiving_account_type)],
	}
	return frappe.db.get_value("Account", filters, "name")


def account_matches_donation_type(account, donation_type):
	account_details = frappe.db.get_value("Account", account, ["name", "account_name"], as_dict=True)
	if not account_details:
		return False

	receiving_account_type = get_receiving_account_donation_type(donation_type).lower()
	return receiving_account_type in (account_details.name or "").lower() or receiving_account_type in (
		account_details.account_name or ""
	).lower()


def get_receiving_account_donation_type(donation_type):
	return "Zakat" if donation_type == "Zakat" else "Atiya"


def get_donation_purpose_account_mapping(company, donation_type, donation_purpose):
	mapping = frappe.db.get_value(
		"Donation Purpose Account Mapping",
		{
			"parent": donation_purpose,
			"company": company,
			"donation_type": donation_type,
		},
		["credit_account", "cost_center"],
		as_dict=True,
	)
	if not mapping:
		return {
			"credit_account": None,
			"cost_center": None,
		}

	return {
		"credit_account": mapping.credit_account,
		"cost_center": mapping.cost_center,
	}


@frappe.whitelist()
def get_source_accounting_details(company=None, source_type=None, donation_type=None, mode_of_payment=None):
	company = company or get_default_company()
	details = {
		"company": company,
		"mode_of_payment_type": None,
		"debit_account": None,
		"credit_account": None,
		"cost_center": None,
	}

	if mode_of_payment and company:
		details.update(get_mode_of_payment_account(company, mode_of_payment, donation_type))

	if source_type and donation_type and company:
		details.update(get_donation_source_account_mapping(company, source_type, donation_type))

	return details


@frappe.whitelist()
def get_collection_cash_accounting_defaults(company=None, source_type=None, donation_type=None):
	company = company or get_default_company()
	mode_of_payment = get_default_cash_mode_of_payment()
	details = {
		"company": company,
		"mode_of_payment": mode_of_payment,
		"mode_of_payment_type": "Cash" if mode_of_payment else None,
		"debit_account": None,
		"credit_account": None,
		"cost_center": None,
	}

	if company:
		details["debit_account"] = get_default_cash_account(company, mode_of_payment)

	if source_type and donation_type and company:
		details.update(get_donation_source_account_mapping(company, source_type, donation_type))

	return details


def get_default_cash_mode_of_payment():
	return (
		frappe.db.get_value("Mode of Payment", {"name": "Cash", "enabled": 1, "type": "Cash"}, "name")
		or frappe.db.get_value("Mode of Payment", {"enabled": 1, "type": "Cash"}, "name")
	)


def get_default_cash_account(company, mode_of_payment=None):
	default_account = None
	if mode_of_payment:
		default_account = frappe.db.get_value(
			"Mode of Payment Account",
			{
				"parent": mode_of_payment,
				"company": company,
			},
			"default_account",
		)
		if default_account:
			account_type = frappe.db.get_value(
				"Account",
				{
					"name": default_account,
					"company": company,
					"is_group": 0,
				},
				"account_type",
			)
			if account_type != "Cash":
				default_account = None

	return (
		default_account
		or frappe.db.get_value(
			"Account",
			{
				"company": company,
				"is_group": 0,
				"account_type": "Cash",
				"account_name": ["like", "%Donation Cash%"],
			},
			"name",
		)
		or frappe.db.get_value(
			"Account",
			{
				"company": company,
				"is_group": 0,
				"account_type": "Cash",
			},
			"name",
		)
	)


def get_donation_source_account_mapping(company, source_type, donation_type):
	mapping = frappe.db.get_value(
		"Donation Source Account Mapping",
		{
			"company": company,
			"source_type": source_type,
			"donation_type": donation_type,
		},
		["credit_account", "cost_center"],
		as_dict=True,
	)
	if not mapping:
		return {
			"credit_account": None,
			"cost_center": None,
		}

	return {
		"credit_account": mapping.credit_account,
		"cost_center": mapping.cost_center,
	}


def set_collection_accounting_details(doc, source_type, donation_type):
	doc.accounting_status = doc.accounting_status or "Not Posted"

	if not doc.company:
		doc.company = get_default_company()

	doc.mode_of_payment = get_default_cash_mode_of_payment()
	if doc.mode_of_payment and doc.company:
		doc.mode_of_payment_type = "Cash"
		doc.debit_account = get_default_cash_account(doc.company, doc.mode_of_payment)
	else:
		doc.mode_of_payment_type = None

	if source_type and donation_type and doc.company:
		mapping = get_donation_source_account_mapping(doc.company, source_type, donation_type)
		if not doc.credit_account:
			doc.credit_account = mapping.get("credit_account")
		if not doc.accounting_cost_center:
			doc.accounting_cost_center = mapping.get("cost_center")


def validate_collection_accounting_details(doc, source_type, donation_type, amount):
	if flt(amount) <= 0:
		frappe.throw(frappe._("Collected Amount must be greater than zero."))

	if not doc.company:
		frappe.throw(frappe._("Company is required for accounting."))

	if not doc.mode_of_payment:
		frappe.throw(frappe._("Mode of Payment is required for accounting."))

	if not doc.debit_account:
		frappe.throw(frappe._("Debit Account is required for accounting."))

	if not doc.credit_account:
		frappe.throw(
			frappe._("Income Account is required for {0} collection.").format(source_type)
		)

	validate_account_for_company(doc.company, doc.debit_account, "Debit Account")
	validate_account_for_company(
		doc.company,
		doc.credit_account,
		"Credit Account",
		allowed_root_types=("Income",),
	)

	if doc.mode_of_payment_type != "Cash":
		frappe.throw(frappe._("Mode of Payment must be Cash for {0}.").format(source_type))

	account_type = frappe.db.get_value("Account", doc.debit_account, "account_type")
	if account_type != "Cash":
		frappe.throw(frappe._("Debit Account must be a Cash account."))


def validate_account_for_company(company, account, label, allowed_root_types=None):
	account_details = frappe.db.get_value(
		"Account",
		account,
		["name", "company", "is_group", "root_type"],
		as_dict=True,
	)
	if not account_details:
		frappe.throw(frappe._("{0} {1} was not found.").format(label, account))

	if account_details.company != company:
		frappe.throw(frappe._("{0} {1} does not belong to Company {2}.").format(label, account, company))

	if account_details.is_group:
		frappe.throw(frappe._("{0} {1} cannot be a group account.").format(label, account))

	if allowed_root_types and account_details.root_type not in allowed_root_types:
		frappe.throw(
			frappe._("{0} {1} must be one of these root types: {2}.").format(
				label,
				account,
				", ".join(allowed_root_types),
			)
		)


def create_collection_journal_entry(
	doc,
	source_type,
	donation_type,
	amount,
	posting_date,
	remarks,
	received_from,
	reference_name=None,
):
	if not reference_name and doc.journal_entry and frappe.db.exists("Journal Entry", doc.journal_entry):
		set_collection_accounting_fields(doc, doc.journal_entry, get_journal_entry_accounting_status(doc.journal_entry))
		return doc.journal_entry

	user_remark = get_collection_journal_entry_user_remark(doc, source_type, reference_name)
	existing_journal_entry = frappe.db.get_value(
		"Journal Entry",
		{
			"user_remark": user_remark,
			"docstatus": ["!=", 2],
		},
		"name",
	)
	if existing_journal_entry:
		set_collection_accounting_fields(doc, existing_journal_entry, "Posted")
		return existing_journal_entry

	cost_center = doc.accounting_cost_center or frappe.db.get_value("Company", doc.company, "cost_center")
	entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": doc.company,
			"posting_date": getdate(posting_date),
			"pay_to_recd_from": received_from,
			"user_remark": user_remark,
			"accounts": [
				get_collection_journal_entry_account_row(
					account=doc.debit_account,
					debit=flt(amount),
					credit=0,
					cost_center=cost_center,
					remarks=remarks,
				),
				get_collection_journal_entry_account_row(
					account=doc.credit_account,
					debit=0,
					credit=flt(amount),
					cost_center=cost_center,
					remarks=remarks,
				),
			],
		}
	)
	entry.insert(ignore_permissions=True)
	entry.submit()
	set_collection_accounting_fields(doc, entry.name, "Posted")
	return entry.name


def get_collection_journal_entry_account_row(account, debit, credit, cost_center=None, remarks=None):
	row = {
		"account": account,
		"debit_in_account_currency": debit,
		"credit_in_account_currency": credit,
		"user_remark": remarks,
	}
	if cost_center:
		row["cost_center"] = cost_center

	return row


def get_collection_journal_entry_user_remark(doc, source_type, reference_name=None):
	if reference_name:
		return "{0}: {1} | Log: {2}".format(source_type, doc.name, reference_name)

	return "{0}: {1}".format(source_type, doc.name)


def set_collection_accounting_fields(doc, journal_entry, status):
	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"journal_entry": journal_entry,
			"accounting_status": status,
		},
		update_modified=False,
	)
	doc.journal_entry = journal_entry
	doc.accounting_status = status


def get_journal_entry_accounting_status(journal_entry):
	docstatus = frappe.db.get_value("Journal Entry", journal_entry, "docstatus")
	return "Posted" if docstatus == 1 else "Cancelled" if docstatus == 2 else "Not Posted"


@frappe.whitelist()
def auto_map_donation_purpose_accounts(company=None, dry_run=0):
	company = company or get_default_company()
	dry_run = bool(int(dry_run or 0))
	donation_types = get_template_donation_types(company)
	accounts = get_credit_account_candidates(company)
	result = {
		"company": company,
		"dry_run": dry_run,
		"created": [],
		"existing": [],
		"skipped": [],
	}

	for purpose in frappe.get_all(
		"Donation Purpose",
		filters={"is_group": 0},
		fields=["name", "purpose_name", "purpose_group", "purpose_path"],
		order_by="purpose_group, purpose_path, name",
	):
		account = find_matching_credit_account(purpose, accounts)
		if not account:
			result["skipped"].append(
				{
					"donation_purpose": purpose.name,
					"reason": "No confident credit account match found",
				}
			)
			continue

		for donation_type in donation_types:
			if frappe.db.exists(
				"Donation Purpose Account Mapping",
				{
					"parent": purpose.name,
					"company": company,
					"donation_type": donation_type,
				},
			):
				result["existing"].append(
					{
						"donation_purpose": purpose.name,
						"donation_type": donation_type,
					}
				)
				continue

			result["created"].append(
				{
					"donation_purpose": purpose.name,
					"donation_type": donation_type,
					"credit_account": account.name,
				}
			)
			if dry_run:
				continue

			doc = frappe.get_doc("Donation Purpose", purpose.name)
			doc.append(
				"account_mappings",
				{
					"company": company,
					"donation_type": donation_type,
					"credit_account": account.name,
				},
			)
			doc.save(ignore_permissions=True)

	if not dry_run:
		frappe.db.commit()

	return result


def get_template_donation_types(company):
	template_rows = frappe.get_all(
		"Donation Purpose Account Mapping",
		filters={
			"parent": "Others - Charm e Qurbani",
			"company": company,
		},
		pluck="donation_type",
	)
	return template_rows or ["Zakat", "Atiya", "Sadqa"]


def get_credit_account_candidates(company):
	return frappe.get_all(
		"Account",
		filters={
			"company": company,
			"is_group": 0,
			"root_type": ["in", ["Income", "Liability", "Equity"]],
		},
		fields=["name", "account_name", "account_type", "root_type"],
		order_by="name",
	)


def find_matching_credit_account(purpose, accounts):
	purpose_text = normalize_account_match_text(
		" ".join(
			filter(
				None,
				[purpose.name, purpose.purpose_name, purpose.purpose_group, purpose.purpose_path],
			)
		)
	)
	account_by_alias = get_account_alias_map(accounts)

	for purpose_alias, account_alias in get_purpose_account_aliases().items():
		if purpose_alias in purpose_text and account_alias in account_by_alias:
			return account_by_alias[account_alias]

	core_text = normalize_account_match_text(purpose.purpose_name or purpose.name)
	core_text = remove_account_match_words(core_text, ("general", "sponsorship", "others", "welfare"))
	core_text = remove_account_match_words(
		core_text,
		("student", "prisoner", "physical", "online", "reserve", "rehab", "aid"),
	)

	if not core_text:
		return None

	exact_matches = [
		account
		for account in accounts
		if normalize_account_match_text(account.account_name) == core_text
		or normalize_account_match_text(account.name) == core_text
	]
	if len(exact_matches) == 1:
		return exact_matches[0]

	contains_matches = [
		account
		for account in accounts
		if core_text in normalize_account_match_text(account.account_name)
		or core_text in normalize_account_match_text(account.name)
	]
	if len(contains_matches) == 1:
		return contains_matches[0]

	return None


def get_purpose_account_aliases():
	return {
		"charm e qurbani": "charme qurbani",
		"charme qurbani": "charme qurbani",
		"fidya": "fidya",
		"fitra": "fitra",
		"flood rehab": "flood relief",
		"flood relief": "flood relief",
		"relief": "flood relief",
		"hifz": "hifz",
		"nazra": "nazra",
		"masajid": "construction of masajid",
		"ration": "ration",
		"release of prisoner": "release of prisoner",
	}


def get_account_alias_map(accounts):
	account_by_alias = {}
	for account in accounts:
		account_by_alias[normalize_account_match_text(account.account_name)] = account
		account_by_alias[normalize_account_match_text(account.name)] = account

	return account_by_alias


def normalize_account_match_text(value):
	value = re.sub(r"\s+-\s+j$", "", str(value or ""), flags=re.IGNORECASE)
	value = value.replace("&", " and ")
	value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
	return re.sub(r"\s+", " ", value).strip().lower()


def remove_account_match_words(text, words):
	tokens = [token for token in text.split() if token not in words]
	return " ".join(tokens)


@frappe.whitelist()
def backfill_donation_order_gl_party(donation_order=None):
	filters = {
		"journal_entry": ["is", "set"],
		"donor_name": ["is", "set"],
	}
	if donation_order:
		filters["name"] = donation_order

	orders = frappe.get_all("Donation Order", filters=filters, fields=["name", "donor_name", "journal_entry"])
	updated = []
	for order in orders:
		frappe.db.sql(
			"""
			update `tabGL Entry`
			set party_type = %s,
				party = %s
			where voucher_type = 'Journal Entry'
				and voucher_no = %s
				and ifnull(is_cancelled, 0) = 0
			""",
			("Donor", order.donor_name, order.journal_entry),
		)
		updated.append(
			{
				"donation_order": order.name,
				"journal_entry": order.journal_entry,
				"donor": order.donor_name,
			}
		)

	frappe.db.commit()
	return {
		"updated": updated,
		"count": len(updated),
	}
