# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from pathlib import Path
from unittest.mock import Mock, patch

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

	def test_submission_does_not_enforce_a_custom_workflow_status(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"status": "Approved",
				"closing_details": [{"source_doctype": "Donation Order", "source_name": "DO-00001"}],
			}
		)
		closing.db_set = lambda *args, **kwargs: None
		closing.mark_sources_as_deposited = lambda: None

		with patch(
			"donation_management.donation_management.doctype.donation_closing.donation_closing.now_datetime",
			return_value="2026-10-06 12:00:00",
		), patch(
			"donation_management.donation_management.doctype.donation_closing.donation_closing.notify_finance"
		):
			closing.on_submit()

		self.assertEqual(closing.status, "Approved")
		self.assertEqual(closing.submitted_by, frappe.session.user)

	def test_closing_requires_submitted_linked_cash_handover(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"name": "CD-TEST",
				"cash_handover": "DCH-TEST",
				"total_amount": 10000,
			}
		)
		handover = frappe._dict(
			name="DCH-TEST", docstatus=0, donation_closing="CD-TEST", amount=10000
		)

		with patch.object(frappe.db, "get_value", return_value=handover), self.assertRaisesRegex(
			frappe.ValidationError, "must be submitted through the configured Workflow"
		):
			closing.validate_cash_handover()

	def test_closing_accepts_submitted_linked_cash_handover(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"name": "CD-TEST",
				"cash_handover": "DCH-TEST",
				"total_amount": 10000,
			}
		)
		handover = frappe._dict(
			name="DCH-TEST", docstatus=1, donation_closing="CD-TEST", amount=10000
		)

		with patch.object(frappe.db, "get_value", return_value=handover):
			closing.validate_cash_handover()

	def test_closing_resolves_its_linked_cash_handover_when_reference_is_empty(self):
		closing = DonationClosing(
			{
				"doctype": "Donation Closing",
				"name": "CD-TEST",
				"total_amount": 10000,
			}
		)
		handover = frappe._dict(
			name="DCH-TEST", docstatus=1, donation_closing="CD-TEST", amount=10000
		)

		with patch.object(frappe, "get_all", return_value=["DCH-TEST"]), patch.object(
			frappe.db, "get_value", return_value=handover
		):
			closing.validate_cash_handover()

		self.assertEqual(closing.cash_handover, "DCH-TEST")

	def test_cancelling_closing_cancels_submitted_linked_cash_handovers(self):
		closing = DonationClosing({"doctype": "Donation Closing", "name": "CD-TEST"})
		handover = frappe._dict(flags=frappe._dict(), cancel=Mock())

		with patch.object(frappe, "get_all", return_value=["DCH-TEST"]), patch.object(
			frappe, "get_doc", return_value=handover
		):
			closing.cancel_linked_cash_handovers()

		self.assertTrue(handover.flags.ignore_permissions)
		handover.cancel.assert_called_once_with()

	def test_cancelling_closing_sets_business_status_to_cancelled(self):
		closing = DonationClosing(
			{"doctype": "Donation Closing", "name": "CD-TEST", "status": "Approved"}
		)
		closing.cancel_linked_cash_handovers = Mock()
		closing.reset_source_deposit_status = Mock()
		closing.db_set = Mock()

		with patch(
			"donation_management.donation_management.doctype.donation_closing.donation_closing.notify_finance"
		):
			closing.on_cancel()

		self.assertEqual(closing.status, "Cancelled")
		closing.db_set.assert_called_once_with("status", "Cancelled", update_modified=False)

	def test_form_shows_one_ungrouped_lifecycle_action(self):
		script = Path(__file__).with_name("donation_closing.js").read_text()

		self.assertNotIn("approve_closing", script)
		self.assertNotIn("receive_closing", script)
		self.assertIn('!(frm.doc.closing_details || []).length', script)
		self.assertIn('__("Donation Cash Handover")', script)
		self.assertIn('}, __("Create"));', script)
		self.assertIn('docstatus: ["<", 2]', script)
		self.assertIn('frm.ignore_doctypes_on_cancel_all = ["Donation Cash Handover"]', script)
