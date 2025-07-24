import frappe
import json
from frappe import _
from frappe.utils import get_datetime


def get_context(context):
	"""Handle Invoice Ninja webhook requests"""
	# Get the request data
	try:
		if frappe.request.method == "POST":
			# Get webhook data
			webhook_data = frappe.request.get_json()

			if not webhook_data:
				frappe.throw(_("Invalid webhook data"))

			# Process the webhook
			result = process_invoice_ninja_webhook(webhook_data)

			# Return response
			frappe.response['type'] = 'json'
			frappe.response['message'] = result

		else:
			frappe.throw(_("Only POST requests are allowed"))

	except Exception as e:
		frappe.log_error(f"Webhook processing error: {str(e)}", "Invoice Ninja Webhook Error")
		frappe.response['type'] = 'json'
		frappe.response['message'] = {"success": False, "error": str(e)}


def process_invoice_ninja_webhook(webhook_data):
	"""Process Invoice Ninja webhook data"""
	try:
		# Verify webhook authenticity if secret is configured
		settings = frappe.get_single("Invoice Ninja Settings")
		if settings.webhook_secret:
			if not verify_webhook_signature(webhook_data, settings.webhook_secret):
				return {"success": False, "error": "Invalid webhook signature"}

		# Get event type and data
		event_type = webhook_data.get('event_type')
		entity_data = webhook_data.get('data', {})
		entity_type = webhook_data.get('entity_type')

		if not event_type or not entity_type:
			return {"success": False, "error": "Missing event_type or entity_type"}

		# Process based on entity type and event
		if entity_type == 'client':
			return process_customer_webhook(event_type, entity_data)
		elif entity_type == 'invoice':
			return process_invoice_webhook(event_type, entity_data)
		elif entity_type == 'quote':
			return process_quote_webhook(event_type, entity_data)
		elif entity_type == 'product':
			return process_product_webhook(event_type, entity_data)
		elif entity_type == 'payment':
			return process_payment_webhook(event_type, entity_data)
		else:
			frappe.log_error(f"Unhandled entity type: {entity_type}", "Invoice Ninja Webhook")
			return {"success": True, "message": f"Entity type {entity_type} not handled"}

	except Exception as e:
		frappe.log_error(f"Webhook processing failed: {str(e)}", "Invoice Ninja Webhook Error")
		return {"success": False, "error": str(e)}


def verify_webhook_signature(webhook_data, secret):
	"""Verify webhook signature (implement based on Invoice Ninja's signature method)"""
	# This would need to be implemented based on how Invoice Ninja signs webhooks
	# For now, return True (implement proper verification as needed)
	return True


def process_customer_webhook(event_type, customer_data):
	"""Process customer webhook events"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.enable_customer_sync:
			return {"success": True, "message": "Customer sync disabled"}

		if event_type in ['created', 'updated']:
			from .api import sync_customer_from_invoice_ninja
			sync_customer_from_invoice_ninja(customer_data)
			return {"success": True, "message": f"Customer {event_type} processed"}

		elif event_type == 'deleted':
			# Handle customer deletion
			existing = frappe.db.exists("Customer", {"invoice_ninja_id": str(customer_data.get('id'))})
			if existing:
				# Mark as deleted or remove based on configuration
				customer_doc = frappe.get_doc("Customer", existing)
				customer_doc.db_set('sync_status', 'Deleted in Invoice Ninja')
			return {"success": True, "message": "Customer deletion processed"}

		else:
			return {"success": True, "message": f"Customer event {event_type} not handled"}

	except Exception as e:
		frappe.log_error(f"Customer webhook error: {str(e)}", "Customer Webhook Error")
		return {"success": False, "error": str(e)}


def process_invoice_webhook(event_type, invoice_data):
	"""Process invoice webhook events"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.enable_invoice_sync:
			return {"success": True, "message": "Invoice sync disabled"}

		if event_type in ['created', 'updated']:
			from .api import sync_invoice_from_invoice_ninja
			sync_invoice_from_invoice_ninja(invoice_data)
			return {"success": True, "message": f"Invoice {event_type} processed"}

		elif event_type == 'deleted':
			# Handle invoice deletion
			existing = frappe.db.exists("Sales Invoice", {"invoice_ninja_id": str(invoice_data.get('id'))})
			if existing:
				invoice_doc = frappe.get_doc("Sales Invoice", existing)
				invoice_doc.db_set('sync_status', 'Deleted in Invoice Ninja')
			return {"success": True, "message": "Invoice deletion processed"}

		else:
			return {"success": True, "message": f"Invoice event {event_type} not handled"}

	except Exception as e:
		frappe.log_error(f"Invoice webhook error: {str(e)}", "Invoice Webhook Error")
		return {"success": False, "error": str(e)}


def process_quote_webhook(event_type, quote_data):
	"""Process quote webhook events"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.enable_quote_sync:
			return {"success": True, "message": "Quote sync disabled"}

		if event_type in ['created', 'updated']:
			from .api import sync_quotation_from_invoice_ninja
			sync_quotation_from_invoice_ninja(quote_data)
			return {"success": True, "message": f"Quote {event_type} processed"}

		elif event_type == 'deleted':
			# Handle quote deletion
			existing = frappe.db.exists("Quotation", {"invoice_ninja_id": str(quote_data.get('id'))})
			if existing:
				quote_doc = frappe.get_doc("Quotation", existing)
				quote_doc.db_set('sync_status', 'Deleted in Invoice Ninja')
			return {"success": True, "message": "Quote deletion processed"}

		else:
			return {"success": True, "message": f"Quote event {event_type} not handled"}

	except Exception as e:
		frappe.log_error(f"Quote webhook error: {str(e)}", "Quote Webhook Error")
		return {"success": False, "error": str(e)}


def process_product_webhook(event_type, product_data):
	"""Process product webhook events"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.enable_product_sync:
			return {"success": True, "message": "Product sync disabled"}

		if event_type in ['created', 'updated']:
			from .api import sync_item_from_invoice_ninja
			sync_item_from_invoice_ninja(product_data)
			return {"success": True, "message": f"Product {event_type} processed"}

		elif event_type == 'deleted':
			# Handle product deletion
			existing = frappe.db.exists("Item", {"invoice_ninja_id": str(product_data.get('id'))})
			if existing:
				item_doc = frappe.get_doc("Item", existing)
				item_doc.db_set('sync_status', 'Deleted in Invoice Ninja')
			return {"success": True, "message": "Product deletion processed"}

		else:
			return {"success": True, "message": f"Product event {event_type} not handled"}

	except Exception as e:
		frappe.log_error(f"Product webhook error: {str(e)}", "Product Webhook Error")
		return {"success": False, "error": str(e)}


def process_payment_webhook(event_type, payment_data):
	"""Process payment webhook events"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.enable_payment_sync:
			return {"success": True, "message": "Payment sync disabled"}

		if event_type in ['created', 'updated']:
			from .tasks import _create_payment_entry_from_invoice_ninja
			_create_payment_entry_from_invoice_ninja(payment_data)
			return {"success": True, "message": f"Payment {event_type} processed"}

		elif event_type == 'deleted':
			# Handle payment deletion
			existing = frappe.db.exists("Payment Entry", {"invoice_ninja_id": str(payment_data.get('id'))})
			if existing:
				payment_doc = frappe.get_doc("Payment Entry", existing)
				payment_doc.db_set('sync_status', 'Deleted in Invoice Ninja')
			return {"success": True, "message": "Payment deletion processed"}

		else:
			return {"success": True, "message": f"Payment event {event_type} not handled"}

	except Exception as e:
		frappe.log_error(f"Payment webhook error: {str(e)}", "Payment Webhook Error")
		return {"success": False, "error": str(e)}
