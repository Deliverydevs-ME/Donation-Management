# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

from pathlib import Path
from inspect import unwrap
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.doctype.donation_order.donation_order import (
	DonationOrder,
	_get_donation_book_leaf_for_mohasil,
	get_esaal_e_sawab_key,
)
from donation_management.donation_management.api import get_esaal_person_options


class TestDonationOrder(FrappeTestCase):
	def test_connections_include_linked_donation_book_leaves(self):
		dashboard = frappe.get_meta("Donation Order").get_dashboard_data()

		self.assertEqual(dashboard.internal_links["Journal Entry"], "journal_entry")
		self.assertEqual(dashboard.non_standard_fieldnames["Donation Book Leaf"], "donation_order")
		self.assertTrue(
			any("Donation Book Leaf" in transaction["items"] for transaction in dashboard.transactions)
		)

	def test_client_defers_leaf_cancellation_to_parent_order(self):
		order_script = (Path(__file__).resolve().parent / "donation_order.js").read_text()
		self.assertIn('frm.ignore_doctypes_on_cancel_all = ["Donation Book Leaf"]', order_script)

	def test_submits_selected_donation_book_leaf_with_order(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"name": "DO-TEST",
				"donation_book_leaf": "DBL-TEST",
			}
		)
		leaf = MagicMock(name="Donation Book Leaf")
		leaf.name = "DBL-TEST"
		leaf.docstatus = 0

		with patch.object(frappe, "get_doc", return_value=leaf):
			order.submit_linked_donation_book_leaf()

		self.assertEqual(leaf.donation_order, "DO-TEST")
		leaf.save.assert_called_once_with(ignore_permissions=True)
		self.assertTrue(leaf.flags.ignore_permissions)
		leaf.submit.assert_called_once_with()

	def test_does_not_resubmit_an_already_submitted_leaf_for_same_order(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"name": "DO-TEST",
				"donation_book_leaf": "DBL-TEST",
			}
		)
		leaf = MagicMock(name="Donation Book Leaf")
		leaf.name = "DBL-TEST"
		leaf.docstatus = 1
		leaf.donation_order = "DO-TEST"

		with patch.object(frappe, "get_doc", return_value=leaf):
			order.submit_linked_donation_book_leaf()

		leaf.save.assert_not_called()
		leaf.submit.assert_not_called()

	def test_cancels_owned_journal_entry_without_separate_entry_permission(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"journal_entry": "ACC-JV-TEST",
			}
		)
		entry = MagicMock(name="Journal Entry")
		entry.docstatus = 1

		with patch.object(frappe.db, "exists", return_value=True), patch.object(
			frappe, "get_doc", return_value=entry
		):
			order.cancel_linked_journal_entry()

		self.assertTrue(entry.flags.ignore_permissions)
		entry.cancel.assert_called_once_with()

	def test_esaal_person_search_accepts_json_link_filters(self):
		with patch.object(frappe.db, "sql", return_value=[]) as sql:
			self.assertEqual(
				unwrap(get_esaal_person_options)(
					"Donor",
					"",
					"name",
					0,
					1,
					'{"donor":"DN-10650"}',
				),
				[],
			)

		sql.assert_called_once()
		self.assertIn("DN-10650", str(sql.call_args))

	def test_esaal_empty_state_guides_users_to_selected_donor(self):
		doctype_root = Path(__file__).resolve().parent
		order_script = (doctype_root / "donation_order.js").read_text()
		donor_script = (doctype_root.parent / "donor" / "donor.js").read_text()

		self.assertIn("prompt_to_add_esaal_person", order_script)
		self.assertIn("Add Person to Donor", order_script)
		self.assertIn('"only_select", 1', order_script)
		self.assertIn("get_donor_esaal_e_sawab", order_script)
		self.assertIn('"person_name", "fieldtype", "Select"', order_script)
		self.assertIn('"relationship", "read_only", 1', order_script)
		self.assertIn("ESAAL_E_SAWAB_RETURN_CONTEXT_KEY", order_script)
		self.assertIn("return_to_donation_order_after_esaal_person_added", donor_script)

	def test_esaal_e_sawab_key_normalizes_person_and_relationship(self):
		self.assertEqual(
			get_esaal_e_sawab_key("  Abdul   Rahman  ", " Father "),
			("abdul rahman", "father"),
		)

	def test_esaal_e_sawab_key_requires_person_name(self):
		self.assertIsNone(get_esaal_e_sawab_key("", "Father"))

	def test_esaal_selection_accepts_registered_person(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"donor_name": "DN-TEST",
				"donation_purpose": "Esaal e Sawab",
				"esaal_e_sawab": [
					{"person_name": "PERSON-0001", "relationship": "Brother"},
				],
			}
		)

		with patch.object(
			frappe,
			"get_all",
			return_value=[frappe._dict(person_name="PERSON-0001", relationship="Brother")],
		):
			order.validate_esaal_e_sawab_selection()

	def test_esaal_selection_rejects_person_not_registered_under_donor(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"donor_name": "DN-TEST",
				"donation_purpose": "Esaal e Sawab",
				"esaal_e_sawab": [{"person_name": "NEW-PERSON", "relationship": "Brother"}],
			}
		)

		with patch.object(frappe, "get_all", return_value=[]):
			with self.assertRaisesRegex(frappe.ValidationError, "not registered"):
				order.validate_esaal_e_sawab_selection()

	def test_esaal_selection_requires_at_least_one_person(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"donor_name": "DN-TEST",
				"donation_purpose": "Esaal e Sawab",
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "At least one person"):
			order.validate_esaal_e_sawab_selection()

	def test_esaal_selection_requires_relationship_for_new_person(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"donor_name": "DN-TEST",
				"donation_purpose": "Esaal e Sawab",
				"esaal_e_sawab": [{"person_name": "New Person"}],
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Person Name and Relationship"):
			order.validate_esaal_e_sawab_selection()

	def test_mohasil_collection_requires_donation_book_leaf(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"is_mohasil_collection": 1,
				"mohasil": "EMP-1010",
				"donation_book_serial_no": "DB-02",
			}
		)

		with patch(
			"donation_management.donation_management.doctype.donor.donor.validate_mohasil_employee"
			), patch.object(order, "set_donation_book_from_serial"), patch.object(
			order, "validate_donation_book_for_mohasil"
		):
			with self.assertRaisesRegex(frappe.ValidationError, "Donation Book Leaf is required"):
				order.validate_mohasil_details()

	def test_mohasil_location_error_explains_how_to_fix_assignment(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"is_mohasil_collection": 1,
				"mohasil": "EMP-1010",
				"donation_posting_date": "2026-10-06",
			}
		)

		with patch(
			"donation_management.donation_management.doctype.donation_order.donation_order.get_assignment_for_date",
			return_value=None,
		):
			with self.assertRaisesRegex(frappe.ValidationError, "Create or activate a Donation Location Assignment"):
				order.set_and_validate_donation_location()

	def test_mohasil_leaf_receipt_can_match_the_single_purpose_row(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"manual_receipt_number": "002",
				"purpose_details": [{"manual_receipt_number": "002"}],
			}
		)

		with patch(
			"donation_management.donation_management.doctype.donation_order.donation_order.get_existing_manual_receipt_order",
			return_value=None,
		):
			order.validate_manual_receipt_uniqueness()

	def test_manual_receipt_uniqueness_rejects_duplicate_purpose_rows(self):
		order = DonationOrder(
			{
				"doctype": "Donation Order",
				"purpose_details": [
					{"manual_receipt_number": "002"},
					{"manual_receipt_number": "002"},
				],
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Manual Receipt Number is repeated"):
			order.validate_manual_receipt_uniqueness()

	def test_current_order_can_submit_its_legacy_used_book_leaf(self):
		leaf = frappe._dict(
			name="DBL-TEST",
			book="BK-TEST",
			book_serial_no="DB-TEST",
			receipt_number="001",
			status="Used",
			donation_order="DO-TEST",
		)
		assignment = frappe._dict(
			book="BK-TEST",
			book_status="Returned",
			issued_to_employee="EMP-TEST",
			book_type="Donation Book",
		)

		with patch.object(frappe.db, "get_value", return_value=leaf), patch.object(
			frappe.db, "sql", return_value=[assignment]
		):
			result = _get_donation_book_leaf_for_mohasil("DBL-TEST", "EMP-TEST", current_order="DO-TEST")

		self.assertEqual(result.name, "DBL-TEST")
