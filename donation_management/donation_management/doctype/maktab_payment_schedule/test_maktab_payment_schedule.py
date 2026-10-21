import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from donation_management.donation_management.api import get_default_company


class TestMaktabPaymentSchedule(FrappeTestCase):
	def get_collection_accounts(self):
		company = get_default_company()
		debit_account = frappe.db.get_value(
			"Account", {"company": company, "root_type": "Asset", "is_group": 0, "disabled": 0}, "name"
		)
		credit_account = frappe.db.get_value(
			"Account", {"company": company, "root_type": "Income", "is_group": 0, "disabled": 0}, "name"
		)
		if not debit_account or not credit_account:
			self.skipTest("Active Asset and Income accounts are required for Maktab Payment Schedule tests.")
		return debit_account, credit_account

	def test_frequency_is_fetched_from_ilaqi_maktab(self):
		meta = frappe.get_meta("Maktab Payment Schedule")
		self.assertTrue(meta.is_submittable)
		permissions = {permission.role: permission for permission in meta.permissions}
		for role in ("System Manager", "Donation Manager"):
			self.assertTrue(permissions[role].submit)
			self.assertTrue(permissions[role].cancel)
			self.assertTrue(permissions[role].amend)

		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"Test Schedule Maktab {frappe.generate_hash(length=8)}",
				"frequency": "Quarterly",
			}
		).insert()
		debit_account, credit_account = self.get_collection_accounts()
		schedule = frappe.get_doc(
			{
				"doctype": "Maktab Payment Schedule",
				"ilaqi_maktab": maktab.name,
				"frequency": "Monthly",
				"due_date": today(),
				"due_amount": 1000,
				"custom_debit_account": debit_account,
				"custom_credit_account": credit_account,
			}
		).insert()

		self.assertEqual(schedule.frequency, "Quarterly")

		frequency_field = frappe.get_meta("Maktab Payment Schedule").get_field("frequency")
		self.assertEqual(frequency_field.fetch_from, "ilaqi_maktab.frequency")
		self.assertTrue(frequency_field.read_only)
		self.assertEqual(frappe.get_meta("Maktab Payment Schedule").get_field("custom_debit_account").options, "Account")
		self.assertEqual(frappe.get_meta("Maktab Payment Schedule").get_field("custom_credit_account").options, "Account")

	def test_responsible_person_uses_employee_name(self):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Maktab",
				"last_name": "Responsible Person",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2026-01-01",
				"company": get_default_company(),
				"status": "Active",
				"custom_cnic": frappe.generate_hash(length=13).upper().replace("-", "1")[:13],
			}
		).insert(ignore_permissions=True)
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"Test Responsible Maktab {frappe.generate_hash(length=8)}",
				"responsible_person": employee.name,
			}
		).insert()
		debit_account, credit_account = self.get_collection_accounts()
		schedule = frappe.get_doc(
			{
				"doctype": "Maktab Payment Schedule",
				"ilaqi_maktab": maktab.name,
				"due_date": today(),
				"due_amount": 1000,
				"custom_debit_account": debit_account,
				"custom_credit_account": credit_account,
			}
		).insert()

		self.assertEqual(schedule.custom_responsible_person, employee.employee_name)
		field = frappe.get_meta("Maktab Payment Schedule").get_field("custom_responsible_person")
		self.assertEqual(field.fieldtype, "Data")
		self.assertTrue(field.read_only)

	def test_accounts_must_be_active_collection_ledgers(self):
		debit_account, credit_account = self.get_collection_accounts()
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"Test Accounts Maktab {frappe.generate_hash(length=8)}",
			}
		).insert()

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Maktab Payment Schedule",
					"ilaqi_maktab": maktab.name,
					"due_date": today(),
					"due_amount": 1000,
					"custom_debit_account": credit_account,
					"custom_credit_account": credit_account,
				}
			).insert()

		self.assertNotEqual(debit_account, credit_account)
