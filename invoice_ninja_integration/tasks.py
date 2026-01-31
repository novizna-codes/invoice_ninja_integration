import frappe
from frappe.utils import add_days, now_datetime
from .api import get_client


def sync_from_invoice_ninja():
	"""Hourly scheduled task to sync data from Invoice Ninja to ERPNext"""
	from .api import sync_from_invoice_ninja as api_sync

	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled:
		return

	try:
		# Sync all enabled entity types
		if settings.enable_customer_sync:
			api_sync("Customer", limit=100)

		if settings.enable_invoice_sync:
			api_sync("Sales Invoice", limit=100)

		if settings.enable_quote_sync:
			api_sync("Quotation", limit=100)

		if settings.enable_product_sync:
			api_sync("Item", limit=100)

		frappe.log_error("Hourly sync completed successfully", "Invoice Ninja Sync Success")

	except Exception as e:
		frappe.log_error(f"Hourly sync failed: {str(e)}", "Invoice Ninja Sync Error")




def cleanup_sync_logs():
	"""Daily cleanup of old sync logs"""
	try:
		# Delete sync logs older than 30 days
		cutoff_date = add_days(now_datetime(), -30)

		# Delete old error logs related to Invoice Ninja
		frappe.db.sql("""
			DELETE FROM `tabError Log`
			WHERE creation < %s
			AND error LIKE '%%Invoice Ninja%%'
		""", cutoff_date)

		frappe.db.commit()
		frappe.log_error("Sync logs cleanup completed", "Invoice Ninja Cleanup")

	except Exception as e:
		frappe.log_error(f"Sync logs cleanup failed: {str(e)}", "Invoice Ninja Cleanup Error")


def sync_payments_from_invoice_ninja():
	"""Sync payments from Invoice Ninja (can be called separately)"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_payment_sync:
		return

	try:
		client = get_client()
		page = 1
		synced_count = 0

		while True:
			payments = client.get_payments(page=page, per_page=100, include='invoice')
			if not payments or not payments.get('data'):
				break

			for payment in payments['data']:
				# Check if payment already exists
				existing = frappe.db.exists("Payment Entry", {"invoice_ninja_id": str(payment.get('id'))})
				if not existing:
					_create_payment_entry_from_invoice_ninja(payment)
					synced_count += 1

			# Check if there are more pages
			if not payments.get('meta', {}).get('pagination', {}).get('links', {}).get('next'):
				break
			page += 1

		frappe.log_error(f"Synced {synced_count} payments from Invoice Ninja", "Payment Sync Success")

	except Exception as e:
		frappe.log_error(f"Payment sync failed: {str(e)}", "Payment Sync Error")


def _create_payment_entry_from_invoice_ninja(payment_data):
	"""Create ERPNext payment entry from Invoice Ninja payment data"""
	try:
		from .utils.field_mapper import FieldMapper

		payment_doc_data = FieldMapper.map_payment_from_invoice_ninja(payment_data)
		if not payment_doc_data:
			return

		doc = frappe.get_doc(payment_doc_data)
		doc.insert()
		doc.submit()  # Auto-submit payment entries
		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error creating payment entry from Invoice Ninja: {str(e)}", "Payment Creation Error")
