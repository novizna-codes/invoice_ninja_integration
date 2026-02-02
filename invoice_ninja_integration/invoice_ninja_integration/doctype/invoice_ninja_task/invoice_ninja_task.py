# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InvoiceNinjaTask(Document):
	def convert_to_timesheet(self):
		"""Convert Invoice Ninja Task to ERPNext Timesheet for native billing"""
		if not self.customer or not self.duration_hours:
			frappe.throw("Customer and duration are required to create timesheet")

		# Check if already converted
		existing = frappe.db.exists("Timesheet", {"invoice_ninja_task": self.name})
		if existing:
			return existing

		timesheet = frappe.get_doc({
			"doctype": "Timesheet",
			"employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}),
			"invoice_ninja_task": self.name,
			"time_logs": [{
				"activity_type": "Consulting",  # Default
				"from_time": self.start_time,
				"to_time": self.end_time,
				"hours": self.duration_hours,
				"billing_hours": self.duration_hours,
				"billing_rate": self.rate,
				"billing_amount": self.duration_hours * self.rate,
				"is_billable": 1,
				"project": self.project,
				"description": self.description
			}]
		})

		timesheet.insert(ignore_permissions=True)
		timesheet.submit()

		return timesheet.name

