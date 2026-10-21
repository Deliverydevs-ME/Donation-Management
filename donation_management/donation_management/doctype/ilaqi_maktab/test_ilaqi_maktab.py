import frappe
from frappe.tests.utils import FrappeTestCase


class TestIlaqiMaktab(FrappeTestCase):
	def test_location_and_effective_from_date_fields(self):
		meta = frappe.get_meta("Ilaqi Maktab")

		self.assertTrue(meta.is_submittable)
		self.assertEqual(meta.get_field("location").options, "Location")
		self.assertEqual(meta.get_field("effective_from_date").fieldtype, "Date")
		self.assertTrue(meta.get_field("head_count").read_only)
		self.assertIsNotNone(meta.get_field("amended_from"))
		self.assertIsNone(meta.get_field("donation_location"))

		permissions = {permission.role: permission for permission in meta.permissions}
		for role in ("System Manager", "Donation Manager"):
			self.assertTrue(permissions[role].submit)
			self.assertTrue(permissions[role].cancel)
			self.assertTrue(permissions[role].amend)

	def test_financial_fields_lock_on_submission_and_unlock_on_amendment(self):
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"Test Maktab {frappe.generate_hash(length=8)}",
				"status": "Active",
				"fixed_contribution": 1000,
				"frequency": "Monthly",
				"expected_monthly_cost": 750,
			}
		).insert()
		maktab.submit()

		maktab.fixed_contribution = 1200
		with self.assertRaises(frappe.UpdateAfterSubmitError):
			maktab.save()

		maktab.reload()
		maktab.cancel()

		amendment = frappe.copy_doc(maktab)
		amendment.docstatus = 0
		amendment.amended_from = maktab.name
		amendment.fixed_contribution = 1200
		amendment.insert()

		self.assertEqual(amendment.docstatus, 0)
		self.assertEqual(amendment.name, f"{maktab.name}-1")
		self.assertEqual(amendment.maktab_name, amendment.name)
		self.assertEqual(amendment.fixed_contribution, 1200)
		self.assertEqual(amendment.amended_from, maktab.name)
