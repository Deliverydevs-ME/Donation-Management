import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today


class TestMaktabPaymentSchedule(FrappeTestCase):
	def test_frequency_is_fetched_from_ilaqi_maktab(self):
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"Test Schedule Maktab {frappe.generate_hash(length=8)}",
				"frequency": "Quarterly",
			}
		).insert()
		schedule = frappe.get_doc(
			{
				"doctype": "Maktab Payment Schedule",
				"ilaqi_maktab": maktab.name,
				"frequency": "Monthly",
				"due_date": today(),
				"due_amount": 1000,
			}
		).insert()

		self.assertEqual(schedule.frequency, "Quarterly")

		frequency_field = frappe.get_meta("Maktab Payment Schedule").get_field("frequency")
		self.assertEqual(frequency_field.fetch_from, "ilaqi_maktab.frequency")
		self.assertTrue(frequency_field.read_only)
