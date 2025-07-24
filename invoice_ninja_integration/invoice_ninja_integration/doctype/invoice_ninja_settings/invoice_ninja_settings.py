import frappe
from frappe.model.document import Document
import requests
from frappe.utils import get_site_url


class InvoiceNinjaSettings(Document):
	def validate(self):
		"""Validate settings before saving"""
		if self.enabled:
			if not self.invoice_ninja_url or not self.api_token:
				frappe.throw("Invoice Ninja URL and API Token are required when enabled")

		# Set webhook URL automatically
		self.webhook_url = f"{get_site_url()}/api/method/invoice_ninja_integration.www.webhook"

	@frappe.whitelist()
	def test_connection(self):
		"""Test connection to Invoice Ninja API"""
		try:
			headers = {
				'X-API-TOKEN': self.get_password('api_token'),
				'Content-Type': 'application/json'
			}

			response = requests.get(
				f"{self.invoice_ninja_url.rstrip('/')}/api/v1/ping",
				headers=headers,
				timeout=10
			)

			if response.status_code == 200:
				self.connection_status = "Connected"
				frappe.msgprint("Connection successful!", indicator="green")
			else:
				self.connection_status = "Failed"
				frappe.msgprint(f"Connection failed: {response.status_code}", indicator="red")

		except Exception as e:
			self.connection_status = "Failed"
			frappe.msgprint(f"Connection error: {str(e)}", indicator="red")

		self.save()
		return {"success": self.connection_status == "Connected"}

	@frappe.whitelist()
	def get_invoice_ninja_client(self):
		"""Get configured Invoice Ninja API client"""
		if not self.enabled:
			frappe.throw("Invoice Ninja integration is not enabled")

		if not self.invoice_ninja_url or not self.api_token:
			frappe.throw("Invoice Ninja URL and API Token are required")

		from invoice_ninja_integration.utils.invoice_ninja_client import InvoiceNinjaClient
		return InvoiceNinjaClient(
			url=self.invoice_ninja_url,
			token=self.get_password('api_token')
		)
