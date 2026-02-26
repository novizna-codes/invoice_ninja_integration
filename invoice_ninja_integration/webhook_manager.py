"""
Webhook Management API for Invoice Ninja Integration
Handles webhook registration, unregistration, and management
"""

import frappe
from frappe import _
import json


@frappe.whitelist()
def register_webhooks(invoice_ninja_company):
	"""
	Register webhooks for supported entities in Invoice Ninja
	with selective entity registration support

	Args:
		invoice_ninja_company: Name of Invoice Ninja Company doc

	Returns:
		dict: Status and webhook details
	"""
	# try:
		# Get the Invoice Ninja Company doc
	company_doc = frappe.get_doc(
		"Invoice Ninja Company",
		invoice_ninja_company
	)

	if not company_doc.enabled:
		frappe.throw(_("Invoice Ninja Company is disabled"))

	# Initialize client
	from invoice_ninja_integration.utils.invoice_ninja_client import (
		InvoiceNinjaClient
	)
	client = InvoiceNinjaClient(
		invoice_ninja_company=invoice_ninja_company
	)

	# Build webhook target URL with company parameter
	webhook_url = company_doc.webhook_url

	# Get or generate webhook secret for authentication
	if not company_doc.webhook_secret:
		company_doc.generate_webhook_secret()
		company_doc.save(ignore_permissions=True)

	webhook_secret = company_doc.get_password('webhook_secret')

	# Get API credentials from webhook user
	authorization = None
	if company_doc.webhook_user:
		try:
			user_doc = frappe.get_doc("User", company_doc.webhook_user)
			if user_doc.api_key and user_doc.get_password('api_secret'):
				api_key = user_doc.api_key
				api_secret = user_doc.get_password('api_secret')
				authorization = f"token {api_key}:{api_secret}"
			else:
				frappe.msgprint(
					f"Warning: User '{company_doc.webhook_user}' does not have API credentials. "
					f"Webhooks will only use X-API-SECRET authentication.",
					indicator="orange"
				)
		except Exception as e:
			frappe.log_error(f"Failed to get API credentials: {str(e)}", "Webhook Registration")

	# Determine which entities to register based on settings
	entities_to_register = []
	entity_mapping = {
		'enable_customer_webhooks': 'client',
		'enable_invoice_webhooks': 'invoice',
		'enable_quote_webhooks': 'quote',
		'enable_product_webhooks': 'product',
		'enable_payment_webhooks': 'payment'
	}

	for field, entity in entity_mapping.items():
		if company_doc.get(field, 1):  # Default to 1 (enabled)
			entities_to_register.append(entity)

	all_webhooks = []

	for entity in entities_to_register:
		webhooks = client.register_webhooks_for_entity(
			entity,
			webhook_url,
			webhook_secret,  # Pass secret for source verification
			authorization  # Pass API credentials for ERPNext auth
		)
		all_webhooks.extend(webhooks)

	# Store webhook IDs in the company doc
	company_doc.webhook_ids = json.dumps(all_webhooks)
	company_doc.webhooks_registered = 1
	company_doc.webhook_active_count = len(all_webhooks)
	company_doc.webhook_health_status = "Healthy"
	company_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"message": _("Successfully registered {0} webhooks").format(
			len(all_webhooks)
		),
		"webhooks": all_webhooks,
		"webhook_url": webhook_url
	}

	# except Exception as e:
	# 	frappe.log_error(
	# 		f"Error registering webhooks for "
	# 		f"{invoice_ninja_company}: {str(e)}",
	# 		"Webhook Registration Error"
	# 	)
	# 	return {
	# 		"success": False,
	# 		"message": str(e)
	# 	}


@frappe.whitelist()
def unregister_webhooks(invoice_ninja_company):
	"""
	Unregister all webhooks for an Invoice Ninja Company

	Args:
		invoice_ninja_company: Name of Invoice Ninja Company doc

	Returns:
		dict: Status and count of deleted webhooks
	"""
	# try:
	# Get the Invoice Ninja Company doc
	company_doc = frappe.get_doc(
		"Invoice Ninja Company",
		invoice_ninja_company
	)

	# Initialize client
	from invoice_ninja_integration.utils.invoice_ninja_client import (
		InvoiceNinjaClient
	)
	client = InvoiceNinjaClient(
		invoice_ninja_company=invoice_ninja_company
	)

	# Delete all webhooks
	deleted_count = client.unregister_all_webhooks()

	# Clear webhook data from company doc
	company_doc.webhook_ids = None
	# company_doc.webhook_url = None
	company_doc.webhooks_registered = 0
	company_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"message": _("Successfully unregistered {0} webhooks").format(
			deleted_count
		),
		"deleted_count": deleted_count
	}

	# except Exception as e:
	# 	frappe.log_error(
	# 		f"Error unregistering webhooks for "
	# 		f"{invoice_ninja_company}: {str(e)}",
	# 		"Webhook Unregistration Error"
	# 	)
	# 	return {
	# 		"success": False,
	# 		"message": str(e)
	# 	}


@frappe.whitelist()
def get_webhook_status(invoice_ninja_company):
	"""
	Get webhook registration status for an Invoice Ninja Company

	Args:
		invoice_ninja_company: Name of Invoice Ninja Company doc

	Returns:
		dict: Webhook status and details
	"""
	try:
		# Get the Invoice Ninja Company doc
		company_doc = frappe.get_doc(
			"Invoice Ninja Company",
			invoice_ninja_company
		)

		# Parse stored webhook IDs
		webhook_ids = []
		if company_doc.webhook_ids:
			try:
				webhook_ids = json.loads(company_doc.webhook_ids)
			except (json.JSONDecodeError, TypeError):
				webhook_ids = []

		# Initialize client to verify webhooks exist
		from invoice_ninja_integration.utils.invoice_ninja_client import (
			InvoiceNinjaClient
		)
		client = InvoiceNinjaClient(
			invoice_ninja_company=invoice_ninja_company
		)

		# Get current webhooks from Invoice Ninja
		response = client.get_webhooks()
		active_webhooks = []

		if response and not response.get('error'):
			active_webhooks = response.get('data', [])

		return {
			"success": True,
			"registered": company_doc.webhooks_registered,
			"webhook_url": company_doc.webhook_url,
			"stored_webhooks": webhook_ids,
			"active_webhooks_count": len(active_webhooks),
			"active_webhooks": active_webhooks
		}

	except Exception as e:
		frappe.log_error(
			f"Error getting webhook status for {invoice_ninja_company}: {str(e)}",
			"Webhook Status Error"
		)
		return {
			"success": False,
			"message": str(e)
		}


@frappe.whitelist()
def refresh_webhooks(invoice_ninja_company):
	"""
	Refresh webhooks - unregister and re-register

	Args:
		invoice_ninja_company: Name of Invoice Ninja Company doc

	Returns:
		dict: Status and webhook details
	"""
	# try:
		# First unregister existing webhooks
	unregister_result = unregister_webhooks(invoice_ninja_company)

	if not unregister_result.get("success"):
		return unregister_result

	# Then register new webhooks
	register_result = register_webhooks(invoice_ninja_company)

	return register_result

	# except Exception as e:
	# 	frappe.log_error(
	# 		f"Error refreshing webhooks for {invoice_ninja_company}: {str(e)}",
	# 		"Webhook Refresh Error"
	# 	)
	# 	return {
	# 		"success": False,
	# 		"message": str(e)
	# 	}
