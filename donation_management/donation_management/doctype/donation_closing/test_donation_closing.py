# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_closing.donation_closing import DonationClosing


class TestDonationClosing(FrappeTestCase):
	def test_fetch_is_blocked_after_pending_cash_is_fetched(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"status": "Draft",
				"closing_details": [{"source_doctype": "Donation Order", "source_name": "DO-00001"}],
			}
		)
		closing.is_new = lambda: False
		closing.set_company_default = lambda: None

		with self.assertRaisesRegex(frappe.ValidationError, "already been fetched"):
			closing.fetch_pending_cash_donations()

	def test_receive_marks_fetched_draft_closing_as_received(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"status": "Draft",
				"docstatus": 0,
				"closing_details": [{"source_doctype": "Donation Order", "source_name": "DO-00001"}],
			}
		)
		closing.is_new = lambda: False
		closing.save = lambda **kwargs: None

		with patch(
			"donation_management.donation_management.doctype.donation_closing.donation_closing.now_datetime",
			return_value="2026-10-06 12:00:00",
		), patch(
			"donation_management.donation_management.doctype.donation_closing.donation_closing.notify_finance"
		), patch(
			"donation_management.donation_management.doctype.donation_closing.donation_closing.notify_users"
		):
			closing.receive_closing()

		self.assertEqual(closing.status, "Received")
		self.assertEqual(closing.received_by, frappe.session.user)

	def test_receive_requires_draft_closing(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"status": "Received",
				"docstatus": 0,
				"closing_details": [{"source_doctype": "Donation Order", "source_name": "DO-00001"}],
			}
		)
		closing.is_new = lambda: False

		with self.assertRaisesRegex(frappe.ValidationError, "Only Draft"):
			closing.receive_closing()

	def test_form_shows_one_ungrouped_lifecycle_action(self):
		script = Path(__file__).with_name("donation_closing.js").read_text()

		self.assertNotIn("approve_closing", script)
		self.assertIn('!(frm.doc.closing_details || []).length', script)
		self.assertNotIn('receive_closing(frm), __("Actions")', script)
