# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe


FINANCE_NOTIFICATION_ROLES = ("Finance Manager", "CFO", "Donation Manager")


def notify_users(subject, message, users=None, roles=None, reference_doctype=None, reference_name=None):
	recipients = set(users or [])
	for role in roles or []:
		recipients.update(
			frappe.get_all(
				"Has Role",
				filters={"role": role, "parenttype": "User"},
				pluck="parent",
			)
		)

	for user in sorted(recipients):
		if not user or user == "Guest":
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"email_content": message,
				"for_user": user,
				"type": "Alert",
				"document_type": reference_doctype,
				"document_name": reference_name,
			}
		).insert(ignore_permissions=True)


def notify_finance(subject, message, reference_doctype=None, reference_name=None):
	notify_users(
		subject,
		message,
		roles=FINANCE_NOTIFICATION_ROLES,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
	)
