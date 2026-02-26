"""
Invoice Ninja Webhook Handler
Handles incoming webhooks from Invoice Ninja with proper company detection,
signature verification, and incremental sync support.
"""

import frappe
import json
import hmac
import hashlib
from frappe.utils import now


@frappe.whitelist()
def handle_webhook():
	"""
	Main webhook endpoint for Invoice Ninja
	URL: /api/method/invoice_ninja_integration.webhook_handler.handle_webhook

	Dual authentication:
	1. ERPNext API key (via Authorization header) - handled by @frappe.whitelist()
	2. X-API-SECRET (via custom header) - verified manually below

	Supports company parameter: ?company=Company-Name
	"""
	try:
		# Verify POST request
		if frappe.request.method != "POST":
			return error_response("Only POST requests are allowed")

		# Get webhook payload
		webhook_data = frappe.request.get_json()
		if not webhook_data:
			return error_response("Invalid webhook data")

		# Get company from URL parameter (if provided)
		company_param = frappe.request.args.get('company')

		# Identify Invoice Ninja Company first (needed for secret verification)
		# We need to do a preliminary identification to get the company
		entity_data = webhook_data.get('data', {})
		entity_type = webhook_data.get('entity_type')

		# Get company for secret verification
		invoice_ninja_company_prelim = identify_company(
			entity_data, entity_type, company_param
		)

		# Verify X-API-SECRET header (company-specific)
		if invoice_ninja_company_prelim:
			company_doc = frappe.get_doc(
				"Invoice Ninja Company", invoice_ninja_company_prelim
			)
			expected_secret = company_doc.get_password('webhook_secret')
			received_secret = frappe.request.headers.get('X-API-SECRET')

			if expected_secret and received_secret:
				if received_secret != expected_secret:
					frappe.log_error(
						f"Unauthorized webhook attempt for {invoice_ninja_company_prelim}. "
						f"Invalid X-API-SECRET header.",
						"Webhook Security Error"
					)
					return error_response("Unauthorized webhook request")
			elif expected_secret and not received_secret:
				frappe.log_error(
					f"Missing X-API-SECRET header for {invoice_ninja_company_prelim}",
					"Webhook Security Warning"
				)
				return error_response("Missing authentication header")

		# Extract event details
		event_type = webhook_data.get('event_type')

		if not event_type or not entity_type:
			return error_response("Missing event_type or entity_type")

		# Use the already identified company from security check
		invoice_ninja_company = invoice_ninja_company_prelim

		if not invoice_ninja_company:
			error_msg = (
				f"Could not identify Invoice Ninja Company "
				f"for {entity_type} webhook"
			)
			frappe.log_error(
				error_msg, "Webhook Company Detection Error"
			)
			return error_response(
				"Could not identify Invoice Ninja Company"
			)

		# Process webhook based on entity type
		result = process_webhook_event(
			entity_type,
			event_type,
			entity_data,
			invoice_ninja_company
		)

		# Log webhook event
		log_webhook_event(webhook_data, invoice_ninja_company, result)

		return success_response(result)

	except Exception as e:
		error_trace = f"{str(e)}\n{frappe.get_traceback()}"
		frappe.log_error(
			f"Webhook processing error: {error_trace}",
			"Invoice Ninja Webhook Error"
		)
		return error_response(str(e))


def verify_webhook_signature(payload, signature, secret):
	"""
	Verify Invoice Ninja webhook signature using HMAC SHA-256

	Args:
		payload: Raw request body as string
		signature: Signature from request header
		secret: Webhook secret from settings

	Returns:
		bool: True if signature is valid
	"""
	try:
		# Calculate expected signature
		expected = hmac.new(
			secret.encode('utf-8'),
			payload.encode('utf-8'),
			hashlib.sha256
		).hexdigest()

		# Use constant-time comparison
		return hmac.compare_digest(expected, signature)

	except Exception as e:
		error_msg = f"Signature verification error: {str(e)}"
		frappe.log_error(error_msg, "Webhook Security")
		return False


def identify_company(entity_data, entity_type, company_param=None):
	"""
	Identify which Invoice Ninja Company triggered this webhook

	Args:
		entity_data: Entity data from webhook
		entity_type: Type of entity (client, invoice, etc.)
		company_param: Company name from URL parameter (optional)

	Returns:
		str: Invoice Ninja Company document name, or None
	"""
	# Option 1: Use company parameter from URL (most reliable)
	if company_param:
		if frappe.db.exists("Invoice Ninja Company", company_param):
			return company_param

	# Option 2: Check if entity already exists in ERPNext
	entity_id = str(entity_data.get('id'))

	doctype_map = {
		'client': 'Customer',
		'invoice': 'Sales Invoice',
		'quote': 'Quotation',
		'product': 'Item',
		'payment': 'Payment Entry'
	}

	doctype = doctype_map.get(entity_type)
	if doctype:
		try:
			existing_company = frappe.db.get_value(
				doctype,
				{'invoice_ninja_id': entity_id},
				'invoice_ninja_company'
			)
			if existing_company:
				return existing_company
		except Exception:
			pass

	# Option 3: Use company_id from payload (if available)
	company_id = entity_data.get('company_id')
	if company_id:
		try:
			company = frappe.db.get_value(
				'Invoice Ninja Company',
				{'company_id': str(company_id)},
				'name'
			)
			if company:
				return company
		except Exception:
			pass

	# Option 4: If only one enabled company exists, use it
	try:
		companies = frappe.get_all(
			'Invoice Ninja Company',
			filters={'enabled': 1},
			pluck='name'
		)
		if len(companies) == 1:
			return companies[0]
	except Exception:
		pass

	return None


def process_webhook_event(
	entity_type, event_type, entity_data, invoice_ninja_company
):
	"""
	Process webhook event for specific entity type

	Args:
		entity_type: client, invoice, quote, product, payment
		event_type: created, updated, deleted
		entity_data: Entity data from webhook
		invoice_ninja_company: Invoice Ninja Company name

	Returns:
		dict: Processing result
	"""
	settings = frappe.get_single("Invoice Ninja Settings")

	# Route to appropriate handler
	if entity_type == 'client':
		if not settings.enable_customer_sync:
			return {
				"status": "skipped",
				"reason": "Customer sync disabled"
			}
		return process_customer_webhook(
			event_type, entity_data, invoice_ninja_company
		)

	elif entity_type == 'invoice':
		if not settings.enable_invoice_sync:
			return {
				"status": "skipped",
				"reason": "Invoice sync disabled"
			}
		return process_invoice_webhook(
			event_type, entity_data, invoice_ninja_company
		)

	elif entity_type == 'quote':
		if not settings.enable_quote_sync:
			return {
				"status": "skipped",
				"reason": "Quote sync disabled"
			}
		return process_quote_webhook(
			event_type, entity_data, invoice_ninja_company
		)

	elif entity_type == 'product':
		if not settings.enable_product_sync:
			return {
				"status": "skipped",
				"reason": "Product sync disabled"
			}
		return process_product_webhook(
			event_type, entity_data, invoice_ninja_company
		)

	elif entity_type == 'payment':
		if not settings.enable_payment_sync:
			return {
				"status": "skipped",
				"reason": "Payment sync disabled"
			}
		return process_payment_webhook(
			event_type, entity_data, invoice_ninja_company
		)

	else:
		return {
			"status": "skipped",
			"reason": f"Unknown entity type: {entity_type}"
		}


def process_customer_webhook(
	event_type, customer_data, invoice_ninja_company
):
	"""Process customer webhook with incremental sync"""
	try:
		if event_type in ['created', 'updated']:
			from invoice_ninja_integration.api import (
				sync_customer_from_invoice_ninja
			)

			# Use incremental sync - only updates if data changed
			result = sync_customer_from_invoice_ninja(
				customer_data,
				invoice_ninja_company=invoice_ninja_company,
				force_full_sync=False
			)

			return {
				"status": "success",
				"action": result,
				"entity_id": str(customer_data.get('id'))
			}

		elif event_type == 'deleted':
			# Mark customer as deleted
			customer_id = str(customer_data.get('id'))
			existing = frappe.db.exists(
				"Customer", {"invoice_ninja_id": customer_id}
			)

			if existing:
				frappe.db.set_value(
					"Customer", existing, "disabled", 1
				)
				frappe.db.set_value(
					"Customer", existing, "sync_status",
					"Deleted in Invoice Ninja"
				)
				return {
					"status": "success",
					"action": "deleted",
					"entity_id": customer_id
				}

			return {
				"status": "skipped",
				"reason": "Customer not found in ERPNext"
			}

		else:
			return {
				"status": "skipped",
				"reason": f"Unhandled event: {event_type}"
			}

	except Exception as e:
		error_msg = f"Customer webhook error: {str(e)}"
		frappe.log_error(error_msg, "Webhook Processing")
		return {"status": "failed", "error": str(e)}


def process_invoice_webhook(
	event_type, invoice_data, invoice_ninja_company
):
	"""Process invoice webhook with incremental sync"""
	try:
		if event_type in ['created', 'updated']:
			from invoice_ninja_integration.api import (
				sync_invoice_from_invoice_ninja
			)

			# Use incremental sync
			result = sync_invoice_from_invoice_ninja(
				invoice_data,
				invoice_ninja_company=invoice_ninja_company,
				force_full_sync=False
			)

			return {
				"status": "success",
				"action": result,
				"entity_id": str(invoice_data.get('id'))
			}

		elif event_type == 'deleted':
			invoice_id = str(invoice_data.get('id'))
			existing = frappe.db.exists(
				"Sales Invoice", {"invoice_ninja_id": invoice_id}
			)

			if existing:
				frappe.db.set_value(
					"Sales Invoice", existing, "sync_status",
					"Deleted in Invoice Ninja"
				)
				return {
					"status": "success",
					"action": "deleted",
					"entity_id": invoice_id
				}

			return {
				"status": "skipped",
				"reason": "Invoice not found in ERPNext"
			}

		else:
			return {
				"status": "skipped",
				"reason": f"Unhandled event: {event_type}"
			}

	except Exception as e:
		error_msg = f"Invoice webhook error: {str(e)}"
		frappe.log_error(error_msg, "Webhook Processing")
		return {"status": "failed", "error": str(e)}


def process_quote_webhook(
	event_type, quote_data, invoice_ninja_company
):
	"""Process quotation webhook with incremental sync"""
	try:
		if event_type in ['created', 'updated']:
			from invoice_ninja_integration.api import (
				sync_quotation_from_invoice_ninja
			)

			result = sync_quotation_from_invoice_ninja(
				quote_data,
				invoice_ninja_company=invoice_ninja_company,
				force_full_sync=False
			)

			return {
				"status": "success",
				"action": result,
				"entity_id": str(quote_data.get('id'))
			}

		elif event_type == 'deleted':
			quote_id = str(quote_data.get('id'))
			existing = frappe.db.exists(
				"Quotation", {"invoice_ninja_id": quote_id}
			)

			if existing:
				frappe.db.set_value(
					"Quotation", existing, "sync_status",
					"Deleted in Invoice Ninja"
				)
				return {
					"status": "success",
					"action": "deleted",
					"entity_id": quote_id
				}

			return {
				"status": "skipped",
				"reason": "Quotation not found in ERPNext"
			}

		else:
			return {
				"status": "skipped",
				"reason": f"Unhandled event: {event_type}"
			}

	except Exception as e:
		error_msg = f"Quote webhook error: {str(e)}"
		frappe.log_error(error_msg, "Webhook Processing")
		return {"status": "failed", "error": str(e)}


def process_product_webhook(
	event_type, product_data, invoice_ninja_company
):
	"""Process product webhook with incremental sync"""
	try:
		if event_type in ['created', 'updated']:
			from invoice_ninja_integration.api import (
				sync_item_from_invoice_ninja
			)

			result = sync_item_from_invoice_ninja(
				product_data,
				invoice_ninja_company=invoice_ninja_company,
				force_full_sync=False
			)

			return {
				"status": "success",
				"action": result,
				"entity_id": str(product_data.get('id'))
			}

		elif event_type == 'deleted':
			product_id = str(product_data.get('id'))
			existing = frappe.db.exists(
				"Item", {"invoice_ninja_id": product_id}
			)

			if existing:
				frappe.db.set_value(
					"Item", existing, "disabled", 1
				)
				frappe.db.set_value(
					"Item", existing, "sync_status",
					"Deleted in Invoice Ninja"
				)
				return {
					"status": "success",
					"action": "deleted",
					"entity_id": product_id
				}

			return {
				"status": "skipped",
				"reason": "Item not found in ERPNext"
			}

		else:
			return {
				"status": "skipped",
				"reason": f"Unhandled event: {event_type}"
			}

	except Exception as e:
		error_msg = f"Product webhook error: {str(e)}"
		frappe.log_error(error_msg, "Webhook Processing")
		return {"status": "failed", "error": str(e)}


def process_payment_webhook(
	event_type, payment_data, invoice_ninja_company
):
	"""Process payment webhook with incremental sync"""
	try:
		if event_type in ['created', 'updated']:
			from invoice_ninja_integration.api import (
				sync_payment_from_invoice_ninja
			)

			# Use the correct function with incremental sync
			result = sync_payment_from_invoice_ninja(
				payment_data,
				invoice_ninja_company=invoice_ninja_company,
				force_full_sync=False
			)

			return {
				"status": "success",
				"action": result,
				"entity_id": str(payment_data.get('id'))
			}

		elif event_type == 'deleted':
			payment_id = str(payment_data.get('id'))
			existing = frappe.db.exists(
				"Payment Entry", {"invoice_ninja_id": payment_id}
			)

			if existing:
				frappe.db.set_value(
					"Payment Entry", existing, "sync_status",
					"Deleted in Invoice Ninja"
				)
				return {
					"status": "success",
					"action": "deleted",
					"entity_id": payment_id
				}

			return {
				"status": "skipped",
				"reason": "Payment not found in ERPNext"
			}

		else:
			return {
				"status": "skipped",
				"reason": f"Unhandled event: {event_type}"
			}

	except Exception as e:
		error_msg = f"Payment webhook error: {str(e)}"
		frappe.log_error(error_msg, "Webhook Processing")
		return {"status": "failed", "error": str(e)}


def log_webhook_event(webhook_data, invoice_ninja_company, result):
	"""
	Log webhook event for auditing and debugging

	Args:
		webhook_data: Full webhook payload
		invoice_ninja_company: Invoice Ninja Company name
		result: Processing result
	"""
	try:
		status = (
			"Success" if result.get('status') == 'success'
			else "Failed"
		)
		log_doc = frappe.get_doc({
			"doctype": "Invoice Ninja Sync Logs",
			"sync_type": "Webhook",
			"sync_direction": "Invoice Ninja to ERPNext",
			"record_type": webhook_data.get('entity_type', 'Unknown'),
			"status": status,
			"message": json.dumps(result),
			"invoice_ninja_id": str(
				webhook_data.get('data', {}).get('id', '')
			),
			"invoice_ninja_company": invoice_ninja_company,
			"webhook_triggered": True,
			"sync_timestamp": now()
		})
		log_doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		# Don't fail webhook if logging fails
		error_msg = f"Failed to log webhook event: {str(e)}"
		frappe.log_error(error_msg, "Webhook Logging")


def success_response(result):
	"""Return success response"""
	frappe.response['type'] = 'json'
	frappe.response['message'] = {
		"success": True,
		"result": result
	}
	return frappe.response['message']


def error_response(message):
	"""Return error response"""
	frappe.response['type'] = 'json'
	frappe.response['http_status_code'] = 400
	frappe.response['message'] = {
		"success": False,
		"error": message
	}
	return frappe.response['message']


@frappe.whitelist()
def test_webhook(
	entity_type='client',
	event_type='updated',
	invoice_ninja_company=None
):
	"""
	Test webhook handler with mock data

	Args:
		entity_type: client, invoice, quote, product, payment
		event_type: created, updated, deleted
		invoice_ninja_company: Invoice Ninja Company to test with

	Returns:
		dict: Test result
	"""
	# Mock webhook data
	mock_data = {
		"event_type": event_type,
		"entity_type": entity_type,
		"data": {
			"id": "test-123",
			"name": "Test Entity",
			"company_id": "1"
		}
	}

	if not invoice_ninja_company:
		# Get first enabled company
		companies = frappe.get_all(
			"Invoice Ninja Company",
			filters={"enabled": 1},
			pluck="name",
			limit=1
		)
		if companies:
			invoice_ninja_company = companies[0]

	if not invoice_ninja_company:
		return {
			"success": False,
			"error": "No enabled Invoice Ninja Company found"
		}

	result = process_webhook_event(
		entity_type,
		event_type,
		mock_data['data'],
		invoice_ninja_company
	)

	return {
		"success": True,
		"test_data": mock_data,
		"result": result
	}
