import frappe
from frappe.utils import get_datetime, now_datetime, add_days
from .api import sync_from_invoice_ninja, get_client
from .utils.invoice_ninja_client import InvoiceNinjaClient


def sync_invoice_ninja_data():
	"""Hourly sync task to pull data from Invoice Ninja"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled:
		return

	try:
		# Sync customers
		if settings.enable_customer_sync:
			sync_from_invoice_ninja("Customer", limit=100)

		# Sync invoices
		if settings.enable_invoice_sync:
			sync_from_invoice_ninja("Sales Invoice", limit=100)

		# Sync quotes
		if settings.enable_quote_sync:
			sync_from_invoice_ninja("Quotation", limit=100)

		# Sync products
		if settings.enable_product_sync:
			sync_from_invoice_ninja("Item", limit=100)

		# Log successful sync
		frappe.log_error("Hourly sync completed successfully", "Invoice Ninja Sync Success")

	except Exception as e:
		frappe.log_error(f"Hourly sync failed: {str(e)}", "Invoice Ninja Sync Error")


def full_sync_check():
	"""Daily task to perform full sync check and sync missing data"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled:
		return

	try:
		client = get_client()

		# Check for customers that exist in Invoice Ninja but not in ERPNext
		if settings.enable_customer_sync:
			_sync_missing_customers(client)

		# Check for invoices that exist in Invoice Ninja but not in ERPNext
		if settings.enable_invoice_sync:
			_sync_missing_invoices(client)

		# Check for quotes that exist in Invoice Ninja but not in ERPNext
		if settings.enable_quote_sync:
			_sync_missing_quotes(client)

		# Check for products that exist in Invoice Ninja but not in ERPNext
		if settings.enable_product_sync:
			_sync_missing_products(client)

		frappe.log_error("Daily full sync check completed", "Invoice Ninja Full Sync")

	except Exception as e:
		frappe.log_error(f"Daily full sync check failed: {str(e)}", "Invoice Ninja Full Sync Error")


def _sync_missing_customers(client):
	"""Sync customers that exist in Invoice Ninja but not in ERPNext"""
	page = 1
	while True:
		customers = client.get_customers(page=page, per_page=100)
		if not customers or not customers.get('data'):
			break

		for customer in customers['data']:
			existing = frappe.db.exists("Customer", {"invoice_ninja_id": str(customer.get('id'))})
			if not existing:
				from .api import sync_customer_from_invoice_ninja
				sync_customer_from_invoice_ninja(customer)

		# Check if there are more pages
		if not customers.get('meta', {}).get('pagination', {}).get('links', {}).get('next'):
			break
		page += 1


def _sync_missing_invoices(client):
	"""Sync invoices that exist in Invoice Ninja but not in ERPNext"""
	page = 1
	while True:
		invoices = client.get_invoices(page=page, per_page=100, include='client,line_items')
		if not invoices or not invoices.get('data'):
			break

		for invoice in invoices['data']:
			existing = frappe.db.exists("Sales Invoice", {"invoice_ninja_id": str(invoice.get('id'))})
			if not existing:
				from .api import sync_invoice_from_invoice_ninja
				sync_invoice_from_invoice_ninja(invoice)

		# Check if there are more pages
		if not invoices.get('meta', {}).get('pagination', {}).get('links', {}).get('next'):
			break
		page += 1


def _sync_missing_quotes(client):
	"""Sync quotes that exist in Invoice Ninja but not in ERPNext"""
	page = 1
	while True:
		quotes = client.get_quotes(page=page, per_page=100, include='client,line_items')
		if not quotes or not quotes.get('data'):
			break

		for quote in quotes['data']:
			existing = frappe.db.exists("Quotation", {"invoice_ninja_id": str(quote.get('id'))})
			if not existing:
				from .api import sync_quotation_from_invoice_ninja
				sync_quotation_from_invoice_ninja(quote)

		# Check if there are more pages
		if not quotes.get('meta', {}).get('pagination', {}).get('links', {}).get('next'):
			break
		page += 1


def _sync_missing_products(client):
	"""Sync products that exist in Invoice Ninja but not in ERPNext"""
	page = 1
	while True:
		products = client.get_products(page=page, per_page=100)
		if not products or not products.get('data'):
			break

		for product in products['data']:
			existing = frappe.db.exists("Item", {"invoice_ninja_id": str(product.get('id'))})
			if not existing:
				from .api import sync_item_from_invoice_ninja
				sync_item_from_invoice_ninja(product)

		# Check if there are more pages
		if not products.get('meta', {}).get('pagination', {}).get('links', {}).get('next'):
			break
		page += 1


def sync_from_invoice_ninja():
	"""Hourly sync task - wrapper function called by scheduler"""
	sync_invoice_ninja_data()


def sync_customers_from_invoice_ninja():
	"""Sync customers from Invoice Ninja to ERPNext"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_customer_sync:
		return {"success": False, "message": "Customer sync is disabled"}

	try:
		from .api import sync_from_invoice_ninja
		result = sync_from_invoice_ninja("Customer", limit=100)
		return {"success": True, "message": f"Customer sync completed: {result}"}
	except Exception as e:
		frappe.log_error(f"Error syncing customers: {str(e)}", "Customer Sync Error")
		return {"success": False, "message": str(e)}


def sync_invoices_from_invoice_ninja():
	"""Sync invoices from Invoice Ninja to ERPNext"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_invoice_sync:
		return {"success": False, "message": "Invoice sync is disabled"}

	try:
		from .api import sync_from_invoice_ninja
		result = sync_from_invoice_ninja("Sales Invoice", limit=100)
		return {"success": True, "message": f"Invoice sync completed: {result}"}
	except Exception as e:
		frappe.log_error(f"Error syncing invoices: {str(e)}", "Invoice Sync Error")
		return {"success": False, "message": str(e)}


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


def weekly_sync_report():
	"""Weekly sync report generation"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.enabled or not settings.send_sync_reports:
			return

		# Count synced records in the last week
		week_ago = add_days(now_datetime(), -7)

		customer_count = frappe.db.count("Customer", {
			"invoice_ninja_id": ["!=", ""],
			"creation": [">=", week_ago]
		})

		invoice_count = frappe.db.count("Sales Invoice", {
			"invoice_ninja_id": ["!=", ""],
			"creation": [">=", week_ago]
		})

		quote_count = frappe.db.count("Quotation", {
			"invoice_ninja_id": ["!=", ""],
			"creation": [">=", week_ago]
		})

		item_count = frappe.db.count("Item", {
			"invoice_ninja_id": ["!=", ""],
			"creation": [">=", week_ago]
		})

		# Count sync errors in the last week
		error_count = frappe.db.count("Error Log", {
			"error": ["like", "%Invoice Ninja%"],
			"creation": [">=", week_ago]
		})

		# Generate report
		report_content = f"""
		Invoice Ninja Integration - Weekly Sync Report

		Synced Records (Last 7 days):
		- Customers: {customer_count}
		- Invoices: {invoice_count}
		- Quotations: {quote_count}
		- Items: {item_count}

		Sync Errors: {error_count}

		Report generated on: {now_datetime()}
		"""

		# Send email report if configured
		if settings.report_recipients:
			recipients = [email.strip() for email in settings.report_recipients.split(',')]
			frappe.sendmail(
				recipients=recipients,
				subject="Invoice Ninja Integration - Weekly Sync Report",
				message=report_content
			)

		# Log the report
		frappe.log_error(report_content, "Invoice Ninja Weekly Report")

	except Exception as e:
		frappe.log_error(f"Weekly sync report failed: {str(e)}", "Invoice Ninja Report Error")


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
