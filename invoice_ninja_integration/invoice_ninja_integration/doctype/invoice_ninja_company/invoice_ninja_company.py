# Copyright (c) 2025, Novizna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url
import secrets
from urllib.parse import quote, urlparse, parse_qs, urlencode, urlunparse


class InvoiceNinjaCompany(Document):
	def validate(self):
		"""Validate currency account mappings and prepare webhook URL"""
		self.validate_currency_account_mappings()
		# Only set webhook URL if it's empty (preserves manual URLs)
		if not self.webhook_url:
			self.set_webhook_url()
		else:
			# Normalize manually entered URLs to ensure proper encoding
			self.normalize_webhook_url()

	def before_save(self):
		"""Auto-register webhooks if enabled"""
		# Check if company is being enabled and auto-register is on
		if self.enabled and self.auto_register_webhooks:
			if not self.webhooks_registered and self.api_token:
				# Will register after save completes
				self._should_auto_register = True

	def on_update(self):
		"""Handle auto-registration after save"""
		if hasattr(self, '_should_auto_register') and self._should_auto_register:
			try:
				self.auto_register_webhooks_silently()
				delattr(self, '_should_auto_register')
			except Exception as e:
				frappe.log_error(
					f"Auto-registration failed for {self.name}: {str(e)}",
					"Webhook Auto-Registration Error"
				)

	def validate_currency_account_mappings(self):
		"""Validate that receivable accounts support their mapped currencies"""
		if not self.currency_account_mappings:
			return

		# Get the ERPNext company this Invoice Ninja Company is mapped to
		settings = frappe.get_single("Invoice Ninja Settings")
		erpnext_company = None

		if settings.company_mappings:
			for company_mapping in settings.company_mappings:
				if company_mapping.invoice_ninja_company_id == self.company_id:
					erpnext_company = company_mapping.erpnext_company
					break

		# If no mapping found, skip validation (user hasn't set up company mapping yet)
		if not erpnext_company:
			return

		seen_currencies = set()
		default_count = 0

		for mapping in self.currency_account_mappings:
			# Check for duplicate currencies
			if mapping.currency in seen_currencies:
				frappe.throw(f"Currency {mapping.currency} is mapped multiple times. Each currency should be mapped only once.")
			seen_currencies.add(mapping.currency)

			# Count defaults
			if mapping.is_default:
				default_count += 1

			# Validate account belongs to the mapped ERPNext company
			account_company = frappe.db.get_value(
				"Account",
				mapping.receivable_account,
				"company"
			)

			if account_company != erpnext_company:
				frappe.throw(
					f"Account {mapping.receivable_account} belongs to company {account_company}, "
					f"but this Invoice Ninja Company is mapped to {erpnext_company}"
				)

			# Validate account is a receivable account
			account_type = frappe.db.get_value(
				"Account",
				mapping.receivable_account,
				"account_type"
			)

			if account_type != "Receivable":
				frappe.throw(
					f"Account {mapping.receivable_account} is not a Receivable account. "
					f"Only Receivable accounts can be used for invoice debit_to field."
				)

			# Validate account currency matches mapping currency
			account_currency = frappe.db.get_value(
				"Account",
				mapping.receivable_account,
				"account_currency"
			)

			if account_currency and account_currency != mapping.currency:
				frappe.throw(
					f"Account {mapping.receivable_account} has currency {account_currency}, "
					f"but is mapped to {mapping.currency}. Account currency must match the mapping."
				)

		# Warn if more than one default
		if default_count > 1:
			frappe.msgprint(
				"Multiple default currency mappings found. "
				"Only one should be marked as default.",
				indicator="orange"
			)

	def normalize_webhook_url(self):
		"""
		Normalize webhook URL by properly encoding query parameters
		This ensures manually entered URLs pass Laravel validation
		"""
		if not self.webhook_url:
			return

		try:
			# Parse the URL
			parsed = urlparse(self.webhook_url)

			# Parse query parameters
			params = parse_qs(parsed.query, keep_blank_values=True)

			# Flatten params (parse_qs returns lists)
			flat_params = {
				k: v[0] if v else '' for k, v in params.items()
			}

			# Re-encode query string with proper encoding
			encoded_query = urlencode(flat_params, quote_via=quote)

			# Rebuild URL with encoded query
			normalized = urlunparse((
				parsed.scheme,
				parsed.netloc,
				parsed.path,
				parsed.params,
				encoded_query,
				parsed.fragment
			))

			self.webhook_url = normalized

		except Exception as e:
			# Log but don't fail validation if URL parsing fails
			frappe.log_error(
				f"Failed to normalize webhook URL: {str(e)}",
				"Webhook URL Normalization"
			)

	def set_webhook_url(self):
		"""Set the webhook URL for this company"""
		# Generate URL based on current site
		site_url = get_url()
		base_url = (
			f"{site_url}/api/method/"
			"invoice_ninja_integration.webhook_handler.handle_webhook"
		)
		# URL-encode company parameter to handle spaces and special chars
		# This fixes Laravel URL validation in Invoice Ninja
		encoded_company = quote(self.name)
		self.webhook_url = f"{base_url}?company={encoded_company}"

	@frappe.whitelist()
	def regenerate_webhook_url(self):
		"""
		Regenerate webhook URL (useful if site URL changed)
		Callable from button - forces regeneration
		"""
		# Clear URL first to force regeneration
		self.webhook_url = None
		self.set_webhook_url()
		self.save(ignore_permissions=True)

		frappe.msgprint(
			f"Webhook URL regenerated successfully.<br><br>"
			f"<b>New URL:</b><br>{self.webhook_url}<br><br>"
			f"<b>Note:</b> If webhooks are already registered, "
			"you need to re-register them with the new URL.",
			indicator="green",
			alert=True
		)

		return {
			"success": True,
			"webhook_url": self.webhook_url,
			"message": "Webhook URL regenerated successfully"
		}

	def generate_webhook_secret(self):
		"""Generate a random webhook secret"""
		if not self.webhook_secret:
			self.webhook_secret = secrets.token_urlsafe(32)

	@frappe.whitelist()
	def generate_new_secret(self):
		"""
		Generate a new webhook secret (callable from button)
		This will overwrite any existing secret
		"""
		self.webhook_secret = secrets.token_urlsafe(32)
		self.save(ignore_permissions=True)

		frappe.msgprint(
			"New webhook secret generated successfully. "
			"If webhooks are already registered, you may need to re-register "
			"them for the new secret to take effect.",
			indicator="green",
			alert=True
		)

		return {
			"success": True,
			"message": "Webhook secret generated successfully"
		}

	def auto_register_webhooks_silently(self):
		"""
		Auto-register webhooks without user interaction
		Called after save when auto_register_webhooks is enabled
		"""
		try:
			# Ensure webhook secret exists before registering
			self.generate_webhook_secret()
			if self.has_value_changed("webhook_secret"):
				self.save(ignore_permissions=True)

			from invoice_ninja_integration.webhook_manager import (
				register_webhooks
			)

			result = register_webhooks(self.name)

			if result.get("success"):
				frappe.msgprint(
					f"Webhooks automatically registered: "
					f"{result.get('message')}",
					indicator="green",
					alert=True
				)
			else:
				frappe.msgprint(
					f"Failed to auto-register webhooks: "
					f"{result.get('message')}",
					indicator="orange",
					alert=True
				)

		except Exception as e:
			frappe.log_error(
				f"Auto-register webhooks failed: {str(e)}",
				"Webhook Auto-Registration"
			)

	@frappe.whitelist()
	def check_webhook_health(self):
		"""Check webhook health status"""
		try:
			from invoice_ninja_integration.webhook_manager import (
				get_webhook_status
			)

			result = get_webhook_status(self.name)

			if result.get("success"):
				active = result.get("active_webhooks_count", 0)
				stored = len(result.get("stored_webhooks", []))

				if active == stored and active > 0:
					self.webhook_health_status = "Healthy"
				elif active > 0:
					self.webhook_health_status = "Degraded"
				else:
					self.webhook_health_status = "Failed"

				self.webhook_active_count = active
				self.save(ignore_permissions=True)

				return {
					"success": True,
					"status": self.webhook_health_status,
					"active_count": active
				}
			else:
				self.webhook_health_status = "Failed"
				self.save(ignore_permissions=True)
				return {"success": False, "message": result.get("message")}

		except Exception as e:
			self.webhook_health_status = "Failed"
			self.save(ignore_permissions=True)
			frappe.log_error(
				f"Webhook health check failed: {str(e)}",
				"Webhook Health Check"
			)
			return {"success": False, "message": str(e)}
