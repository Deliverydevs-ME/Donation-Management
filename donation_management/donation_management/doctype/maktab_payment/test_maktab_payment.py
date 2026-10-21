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

	def get_collection_accounts(self):
		company = get_default_company()
		debit_account = frappe.db.get_value(
			"Account", {"company": company, "root_type": "Asset", "is_group": 0, "disabled": 0}, "name"
		)
		credit_account = frappe.db.get_value(
			"Account", {"company": company, "root_type": "Income", "is_group": 0, "disabled": 0}, "name"
		)
		if not debit_account or not credit_account:
			self.skipTest("Active Asset and Income accounts are required for Maktab Payment tests.")
		return debit_account, credit_account

	def make_schedule(self, maktab, due_amount=100):
		debit_account, credit_account = self.get_collection_accounts()
		schedule = frappe.get_doc(
			{
				"doctype": "Maktab Payment Schedule",
				"ilaqi_maktab": maktab.name,
				"due_date": "2026-12-01",
				"due_amount": due_amount,
				"custom_debit_account": debit_account,
				"custom_credit_account": credit_account,
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

	def test_frequency_updates_when_ilaqi_maktab_changes(self):
		initial_maktab = self.make_ilaqi_maktab(frequency="Monthly")
		updated_maktab = self.make_ilaqi_maktab(frequency="Yearly")
		payment = frappe.get_doc(
			{
				"doctype": "Maktab Payment",
				"ilaqi_maktab": initial_maktab.name,
				"frequency": "Quarterly",
				"posting_date": "2026-01-02",
				"amount": 100,
			}
		).insert()

		self.assertEqual(payment.frequency, "Monthly")
		payment.ilaqi_maktab = updated_maktab.name
		payment.save()

		self.assertEqual(payment.frequency, "Yearly")

	def test_payment_updates_schedule_collection_details(self):
		maktab = self.make_ilaqi_maktab(frequency="Quarterly", fixed_contribution=100)
		schedule = self.make_schedule(maktab, due_amount=100)
		schedule.submit()
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
		self.assertEqual(payment.debit_account, schedule.custom_debit_account)
		self.assertEqual(payment.credit_account, schedule.custom_credit_account)
