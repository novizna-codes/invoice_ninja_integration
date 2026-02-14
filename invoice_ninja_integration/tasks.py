import frappe
from frappe.utils import add_days, now_datetime
from .api import get_client


def sync_from_invoice_ninja():
	"""Hourly scheduled task to sync data from Invoice Ninja to ERPNext"""
	from .api import sync_company_entities

	# Get all enabled companies
	companies = frappe.get_all(
		"Invoice Ninja Company",
		filters={"enabled": 1},
		fields=["name"]
	)

	if not companies:
		frappe.log_error("No enabled Invoice Ninja companies found", "Scheduled Sync")
		return

	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled:
		return

	# Sync each company's data
	total_synced = 0
	for company in companies:
		try:
			# Sync each entity type that's enabled in settings
			if settings.enable_customer_sync:
				result = sync_company_entities(company.name, "Customer", limit=100)
				total_synced += result.get("synced_count", 0)

			if settings.enable_invoice_sync:
				result = sync_company_entities(company.name, "Sales Invoice", limit=100)
				total_synced += result.get("synced_count", 0)

			if settings.enable_quote_sync:
				result = sync_company_entities(company.name, "Quotation", limit=100)
				total_synced += result.get("synced_count", 0)

			if settings.enable_product_sync:
				result = sync_company_entities(company.name, "Item", limit=100)
				total_synced += result.get("synced_count", 0)

			if settings.enable_payment_sync:
				result = sync_company_entities(company.name, "Payment Entry", limit=100)
				total_synced += result.get("synced_count", 0)

		except Exception as e:
			frappe.log_error(
				f"Scheduled sync error for {company.name}: {str(e)}",
				"Scheduled Sync Error"
			)

	if total_synced > 0:
		frappe.log_error(
			f"Hourly sync completed successfully: {total_synced} records synced across {len(companies)} companies",
			"Invoice Ninja Sync Success"
		)




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

		# Check if auto-submit is enabled
		settings = frappe.get_single("Invoice Ninja Settings")
		if settings.get("auto_submit_payments"):
			doc.submit()

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error creating payment entry from Invoice Ninja: {str(e)}", "Payment Creation Error")


def check_unpaid_invoices_for_payments():
	"""
	Daily task to check unpaid Invoice Ninja invoices for new payments

	This task finds submitted invoices from Invoice Ninja that:
	- Have outstanding amounts
	- Haven't been checked in the last 24 hours (or never checked)
	- And checks if payments are now available in Invoice Ninja
	"""
	try:
		from frappe.utils import add_to_date

		# Get invoices that need payment check
		cutoff_time = add_to_date(now_datetime(), hours=-24)

		invoices = frappe.db.sql("""
			SELECT
				name,
				invoice_ninja_id,
				invoice_ninja_company,
				outstanding_amount
			FROM `tabSales Invoice`
			WHERE invoice_ninja_id IS NOT NULL
			AND invoice_ninja_id != ''
			AND invoice_ninja_company IS NOT NULL
			AND invoice_ninja_company != ''
			AND docstatus = 1
			AND outstanding_amount > 0
			AND (
				invoice_ninja_last_payment_check IS NULL
				OR invoice_ninja_last_payment_check < %s
			)
			ORDER BY modified DESC
			LIMIT 100
		""", (cutoff_time,), as_dict=True)

		if not invoices:
			frappe.logger().info("No unpaid invoices to check for payments")
			return

		checked_count = 0
		synced_count = 0

		for invoice in invoices:
			try:
				# Queue payment sync for this invoice
				frappe.enqueue(
					method='invoice_ninja_integration.api.sync_payments_for_invoice',
					queue='default',
					invoice_doc_name=invoice.name,
					invoice_ninja_id=invoice.invoice_ninja_id,
					invoice_ninja_company=invoice.invoice_ninja_company,
					timeout=300,
					is_async=True
				)
				checked_count += 1

			except Exception as e:
				frappe.log_error(
					f"Error queuing payment check for invoice {invoice.name}: {str(e)}",
					"Payment Check Queue Error"
				)

		frappe.logger().info(
			f"Queued payment checks for {checked_count} unpaid invoices"
		)

	except Exception as e:
		frappe.log_error(
			f"Error in check_unpaid_invoices_for_payments: {str(e)}",
			"Unpaid Invoice Payment Check Error"
		)
