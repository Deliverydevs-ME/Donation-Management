# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from donation_management.donation_management.api import get_default_company


class TestMaktabPayment(FrappeTestCase):
	def make_ilaqi_maktab(self, frequency="Quarterly", fixed_contribution=100):
		maktab = frappe.get_doc(
			{
				"doctype": "Ilaqi Maktab",
				"maktab_name": f"TEST-MAKTAB-PAY-{frappe.generate_hash(length=8)}",
				"head_count": 1,
				"status": "Active",
				"frequency": frequency,
				"fixed_contribution": fixed_contribution,
			}
		)
		maktab.insert()
		return maktab

	def make_employee(self):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": f"Maktab Collector {frappe.generate_hash(length=5)}",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2026-01-01",
				"company": get_default_company(),
				"status": "Active",
				"custom_cnic": frappe.generate_hash(length=13).upper().replace("-", "1")[:13],
			}
		)
		employee.insert(ignore_permissions=True)
		return employee.name

	def ensure_mode_of_payment(self):
		mode = "Cash"
		if not frappe.db.exists("Mode of Payment", mode):
			frappe.get_doc(
				{
					"doctype": "Mode of Payment",
					"mode_of_payment": mode,
					"type": "Cash",
				}
			).insert(ignore_permissions=True)
		return mode

	def make_schedule(self, maktab, due_amount=100):
		schedule = frappe.get_doc(
			{
				"doctype": "Maktab Payment Schedule",
				"ilaqi_maktab": maktab.name,
				"due_date": "2026-12-01",
				"due_amount": due_amount,
			}
		)
		schedule.insert()
		return schedule

	def test_schedule_fetches_frequency_and_outstanding(self):
		maktab = self.make_ilaqi_maktab(frequency="Half Yearly", fixed_contribution=500)
		schedule = self.make_schedule(maktab, due_amount=500)

		self.assertEqual(schedule.frequency, "Half Yearly")
		self.assertEqual(schedule.outstanding_amount, 500)
		self.assertEqual(schedule.status, "Pending")

	def test_payment_updates_schedule_collection_details(self):
		maktab = self.make_ilaqi_maktab(frequency="Quarterly", fixed_contribution=100)
		schedule = self.make_schedule(maktab, due_amount=100)
		mode_of_payment = self.ensure_mode_of_payment()
		collector = self.make_employee()

		payment = frappe.get_doc(
			{
				"doctype": "Maktab Payment",
				"ilaqi_maktab": maktab.name,
				"payment_schedule": schedule.name,
				"posting_date": "2026-01-02",
				"amount": 40,
				"mode_of_payment": mode_of_payment,
				"collection_person": collector,
			}
		)
		payment.insert()
		payment.submit()

		schedule.reload()
		self.assertEqual(payment.frequency, "Quarterly")
		self.assertEqual(payment.outstanding_amount, 100)
		self.assertEqual(schedule.collected_amount, 40)
		self.assertEqual(schedule.outstanding_amount, 60)
		self.assertEqual(schedule.mode_of_payment, mode_of_payment)
		self.assertEqual(schedule.collection_person, collector)
		self.assertEqual(schedule.status, "Partially Paid")
