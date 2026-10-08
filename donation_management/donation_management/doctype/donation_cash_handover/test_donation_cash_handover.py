from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_cash_handover.donation_cash_handover import (
	DonationCashHandover,
)
from donation_management.donation_management.doctype.donation_cash_handover.donation_cash_handover_dashboard import (
	get_data as get_handover_dashboard,
)
from donation_management.donation_management.doctype.donation_closing.donation_closing_dashboard import (
	get_data as get_closing_dashboard,
)


class TestDonationCashHandover(FrappeTestCase):
	def test_submitted_handover_returns_to_its_donation_closing(self):
		handover_script = Path(__file__).with_name("donation_cash_handover.js").read_text()

		self.assertIn("on_submit(frm)", handover_script)
		self.assertIn('frappe.set_route("Form", "Donation Closing", frm.doc.donation_closing)', handover_script)

	def test_linked_closing_sets_expected_handover_amount(self):
		handover = DonationCashHandover(
			{
				"doctype": "Donation Cash Handover",
				"donation_closing": "CD-TEST",
				"amount": 1,
			}
		)
		closing = frappe._dict(
			name="CD-TEST", docstatus=1, company="JTQ", cashier="cashier@example.com", total_amount=10000
		)

		with patch.object(frappe.db, "get_value", return_value=closing), patch.object(
			frappe, "get_all", return_value=[]
		):
			handover.set_donation_closing_details()

		self.assertEqual(handover.company, "JTQ")
		self.assertEqual(handover.cashier, "cashier@example.com")
		self.assertEqual(handover.amount, 10000)

	def test_linked_handover_accepts_a_saved_draft_closing(self):
		handover = DonationCashHandover(
			{"doctype": "Donation Cash Handover", "donation_closing": "CD-TEST"}
		)
		closing = frappe._dict(name="CD-TEST", docstatus=0, company="JTQ", cashier="cashier@example.com", total_amount=10000)

		with patch.object(frappe.db, "get_value", return_value=closing), patch.object(
			frappe, "get_all", return_value=[]
		):
			handover.set_donation_closing_details()

		self.assertEqual(handover.amount, 10000)

	def test_linked_handover_allows_only_one_active_record_per_closing(self):
		handover = DonationCashHandover(
			{"doctype": "Donation Cash Handover", "donation_closing": "CD-TEST"}
		)
		closing = frappe._dict(name="CD-TEST", docstatus=1, company="JTQ", cashier="cashier@example.com", total_amount=10000)

		with patch.object(frappe.db, "get_value", return_value=closing), patch.object(
			frappe, "get_all", return_value=["DCH-00001"]
		), self.assertRaisesRegex(frappe.ValidationError, "already has active Cash Handover"):
			handover.set_donation_closing_details()

	def test_dashboards_show_the_relevant_closing_and_handover_connections(self):
		closing_dashboard = get_closing_dashboard()
		handover_dashboard = get_handover_dashboard()

		self.assertEqual(closing_dashboard["fieldname"], "donation_closing")
		self.assertIn("Donation Cash Handover", closing_dashboard["transactions"][0]["items"])
		self.assertEqual(handover_dashboard["internal_links"]["Donation Closing"], "donation_closing")
