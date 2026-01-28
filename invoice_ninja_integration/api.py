import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime
import json
from .utils.invoice_ninja_client import InvoiceNinjaClient
from .utils.field_mapper import FieldMapper


@frappe.whitelist()
def get_invoice_ninja_settings():
	"""Get Invoice Ninja settings"""
	settings = frappe.get_single("Invoice Ninja Settings")
	return {
		"enabled": settings.enabled,
		"server_url": settings.invoice_ninja_url,
		"api_token": settings.get_password("api_token") if settings.api_token else None,
		"sync_customers": settings.enable_customer_sync,
		"sync_invoices": settings.enable_invoice_sync,
		"sync_quotes": settings.enable_quote_sync,
		"sync_products": settings.enable_product_sync,
		"sync_payments": settings.enable_payment_sync
	}


def get_client():
	"""Get configured Invoice Ninja client"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.invoice_ninja_url or not settings.api_token:
		frappe.throw(_("Invoice Ninja integration is not properly configured"))

	return InvoiceNinjaClient(settings.invoice_ninja_url, settings.get_password("api_token"))


@frappe.whitelist()
def test_connection():
	"""Test Invoice Ninja API connection"""
	try:
		client = get_client()
		if client.test_connection():
			return {"success": True, "message": "Connection successful"}
		else:
			return {"success": False, "message": "Connection failed"}
	except Exception as e:
		return {"success": False, "message": str(e)}


# Document event handlers for real-time sync
def sync_to_invoice_ninja(doc, method):
	"""Sync customer to Invoice Ninja after insert/update"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_customer_sync:
		return

	try:
		client = get_client()
		customer_data = FieldMapper.map_customer_to_invoice_ninja(doc)

		# Check if customer already exists in Invoice Ninja
		if hasattr(doc, 'invoice_ninja_id') and doc.invoice_ninja_id:
			# Update existing customer
			response = client.update_customer(doc.invoice_ninja_id, customer_data)
		else:
			# Create new customer
			response = client.create_customer(customer_data)
			if response and response.get('data'):
				doc.db_set('invoice_ninja_id', str(response['data'].get('id')))
				doc.db_set('sync_status', 'Synced')

		if response:
			frappe.msgprint(_("Customer synced to Invoice Ninja successfully"))
		else:
			frappe.log_error(f"Failed to sync customer {doc.name} to Invoice Ninja", "Customer Sync Error")

	except Exception as e:
		frappe.log_error(f"Error syncing customer {doc.name}: {str(e)}", "Customer Sync Error")


def sync_invoice_to_invoice_ninja(doc, method):
	"""Sync sales invoice to Invoice Ninja on submit"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_invoice_sync:
		return

	try:
		client = get_client()
		invoice_data = FieldMapper.map_invoice_to_invoice_ninja(doc)

		if hasattr(doc, 'invoice_ninja_id') and doc.invoice_ninja_id:
			# Update existing invoice
			response = client.update_invoice(doc.invoice_ninja_id, invoice_data)
		else:
			# Create new invoice
			response = client.create_invoice(invoice_data)
			if response and response.get('data'):
				doc.db_set('invoice_ninja_id', str(response['data'].get('id')))
				doc.db_set('sync_status', 'Synced')

		if response:
			frappe.msgprint(_("Invoice synced to Invoice Ninja successfully"))
		else:
			frappe.log_error(f"Failed to sync invoice {doc.name} to Invoice Ninja", "Invoice Sync Error")

	except Exception as e:
		frappe.log_error(f"Error syncing invoice {doc.name}: {str(e)}", "Invoice Sync Error")


def sync_quotation_to_invoice_ninja(doc, method):
	"""Sync quotation to Invoice Ninja on submit"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_quote_sync:
		return

	try:
		client = get_client()
		quote_data = FieldMapper.map_quotation_to_invoice_ninja(doc)

		if hasattr(doc, 'invoice_ninja_id') and doc.invoice_ninja_id:
			# Update existing quote
			response = client.update_quote(doc.invoice_ninja_id, quote_data)
		else:
			# Create new quote
			response = client.create_quote(quote_data)
			if response and response.get('data'):
				doc.db_set('invoice_ninja_id', str(response['data'].get('id')))
				doc.db_set('sync_status', 'Synced')

		if response:
			frappe.msgprint(_("Quotation synced to Invoice Ninja successfully"))
		else:
			frappe.log_error(f"Failed to sync quotation {doc.name} to Invoice Ninja", "Quotation Sync Error")

	except Exception as e:
		frappe.log_error(f"Error syncing quotation {doc.name}: {str(e)}", "Quotation Sync Error")


def sync_item_to_invoice_ninja(doc, method):
	"""Sync item to Invoice Ninja after insert/update"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled or not settings.enable_product_sync:
		return

	try:
		client = get_client()
		product_data = FieldMapper.map_item_to_invoice_ninja(doc)

		if hasattr(doc, 'invoice_ninja_id') and doc.invoice_ninja_id:
			# Update existing product
			response = client.update_product(doc.invoice_ninja_id, product_data)
		else:
			# Create new product
			response = client.create_product(product_data)
			if response and response.get('data'):
				doc.db_set('invoice_ninja_id', str(response['data'].get('id')))
				doc.db_set('sync_status', 'Synced')

		if response:
			frappe.msgprint(_("Item synced to Invoice Ninja successfully"))
		else:
			frappe.log_error(f"Failed to sync item {doc.name} to Invoice Ninja", "Item Sync Error")

	except Exception as e:
		frappe.log_error(f"Error syncing item {doc.name}: {str(e)}", "Item Sync Error")


@frappe.whitelist()
def manual_sync_customer(customer_name):
	"""Manually sync a customer to Invoice Ninja"""
	doc = frappe.get_doc("Customer", customer_name)
	sync_to_invoice_ninja(doc, "manual")
	return {"success": True, "message": "Customer sync initiated"}


@frappe.whitelist()
def manual_sync_invoice(invoice_name):
	"""Manually sync an invoice to Invoice Ninja"""
	doc = frappe.get_doc("Sales Invoice", invoice_name)
	sync_invoice_to_invoice_ninja(doc, "manual")
	return {"success": True, "message": "Invoice sync initiated"}


@frappe.whitelist()
def sync_from_invoice_ninja(doctype, limit=50):
	"""Sync data from Invoice Ninja to ERPNext"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled:
		return {"success": False, "message": "Invoice Ninja integration is disabled"}

	# try:
	client = get_client()
	synced_count = 0

	if doctype == "Customer" and settings.enable_customer_sync:
		customers = client.get_customers(per_page=limit)
		if customers and customers.get('data'):
			for customer in customers['data']:
				sync_customer_from_invoice_ninja(customer)
				synced_count += 1

	elif doctype == "Sales Invoice" and settings.enable_invoice_sync:
		invoices = client.get_invoices(per_page=limit, include='client,line_items')
		if invoices and invoices.get('data'):
			for invoice in invoices['data']:
				sync_invoice_from_invoice_ninja(invoice)
				synced_count += 1

	elif doctype == "Quotation" and settings.enable_quote_sync:
		quotes = client.get_quotes(per_page=limit, include='client,line_items')
		if quotes and quotes.get('data'):
			for quote in quotes['data']:
				sync_quotation_from_invoice_ninja(quote)
				synced_count += 1

	elif doctype == "Item" and settings.enable_product_sync:
		products = client.get_products(per_page=limit)
		if products and products.get('data'):
			for product in products['data']:
				sync_item_from_invoice_ninja(product)
				synced_count += 1

	return {
		"success": True,
		"message": f"Synced {synced_count} {doctype} records from Invoice Ninja",
		"synced_count": synced_count,
	}

	# except Exception as e:
	# 	frappe.log_error(f"Error syncing {doctype} from Invoice Ninja: {str(e)}", "Invoice Ninja Sync Error")
	# 	return {"success": False, "message": str(e)}


def sync_customer_from_invoice_ninja(customer_data):
	"""Create/update ERPNext customer from Invoice Ninja data"""
	try:
		# Check if customer already exists
		existing = frappe.db.exists("Customer", {"invoice_ninja_id": str(customer_data.get('id'))})

		customer_doc_data, address_data = FieldMapper.map_customer_from_invoice_ninja(customer_data)
		if not customer_doc_data:
			return

		if existing:
			# Update existing customer
			doc = frappe.get_doc("Customer", existing)
			for key, value in customer_doc_data.items():
				if key != 'doctype' and hasattr(doc, key):
					setattr(doc, key, value)
			doc.save()
		else:
			# Create new customer
			doc = frappe.get_doc(customer_doc_data)
			doc.insert()

		# Handle address if provided
		if address_data:
			address_data['links'] = [{"link_doctype": "Customer", "link_name": doc.name}]
			existing_address = frappe.db.exists("Address", {"address_title": address_data.get('address_title')})

			if existing_address:
				addr_doc = frappe.get_doc("Address", existing_address)
				for key, value in address_data.items():
					if key not in ['doctype', 'links'] and hasattr(addr_doc, key):
						setattr(addr_doc, key, value)
				addr_doc.save()
			else:
				addr_doc = frappe.get_doc(address_data)
				addr_doc.insert()

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error creating customer from Invoice Ninja: {str(e)}", "Customer Creation Error")


def sync_invoice_from_invoice_ninja(invoice_data):
	"""Create/update ERPNext sales invoice from Invoice Ninja data"""
	try:
		# Check if invoice already exists
		existing = frappe.db.exists("Sales Invoice", {"invoice_ninja_id": str(invoice_data.get('id'))})

		if existing:
			# Skip if already exists to avoid duplicates
			return

		invoice_doc_data = FieldMapper.map_invoice_from_invoice_ninja(invoice_data)
		if not invoice_doc_data:
			return

		doc = frappe.get_doc(invoice_doc_data)
		doc.insert()
		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error creating invoice from Invoice Ninja: {str(e)}", "Invoice Creation Error")


def sync_quotation_from_invoice_ninja(quote_data):
	"""Create/update ERPNext quotation from Invoice Ninja data"""
	try:
		# Check if quotation already exists
		existing = frappe.db.exists("Quotation", {"invoice_ninja_id": str(quote_data.get('id'))})

		if existing:
			# Skip if already exists to avoid duplicates
			return

		quotation_doc_data = FieldMapper.map_quotation_from_invoice_ninja(quote_data)
		if not quotation_doc_data:
			return

		doc = frappe.get_doc(quotation_doc_data)
		doc.insert()
		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error creating quotation from Invoice Ninja: {str(e)}", "Quotation Creation Error")


def sync_item_from_invoice_ninja(product_data):
	"""Create/update ERPNext item from Invoice Ninja data"""
	try:
		# Check if item already exists
		existing = frappe.db.exists("Item", {"invoice_ninja_id": str(product_data.get('id'))})

		item_doc_data = FieldMapper.map_item_from_invoice_ninja(product_data)
		if not item_doc_data:
			return

		if existing:
			# Update existing item
			doc = frappe.get_doc("Item", existing)
			for key, value in item_doc_data.items():
				if key != 'doctype' and hasattr(doc, key):
					setattr(doc, key, value)
			doc.save()
		else:
			# Create new item
			doc = frappe.get_doc(item_doc_data)
			doc.insert()

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error creating item from Invoice Ninja: {str(e)}", "Item Creation Error")


@frappe.whitelist()
def get_invoice_ninja_companies(settings_name=None):
	"""Fetch companies from Invoice Ninja API"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")

		if not settings.invoice_ninja_url or not settings.api_token:
			return {"success": False, "error": "Invoice Ninja URL and API Token are required"}

		# Initialize client
		client = InvoiceNinjaClient(settings.invoice_ninja_url, settings.get_password("api_token"))

		# Fetch companies from Invoice Ninja
		response = client._make_request('GET', 'companies')

		if response and 'data' in response:
			companies = []
			for company in response['data']:
				# Create or update local Invoice Ninja Company doc
				existing_company = frappe.db.get_all("Invoice Ninja Company", filters={"company_id": str(company.get('id'))}, limit=1)

				if existing_company:
					company_doc = frappe.get_doc("Invoice Ninja Company", existing_company[0].name)
					company_doc.company_name = company.get('settings').get('name', f"Company {company.get('id')}")
					company_doc.save(ignore_permissions=True)
					companies.append(company_doc.as_dict())
					continue

				company_doc = frappe.get_doc({
					"doctype": "Invoice Ninja Company",
					"company_id": str(company.get('id')),
					"company_name": company.get('settings').get('name', f"Company {company.get('id')}"),
				})

				company_doc.save(ignore_permissions=True)
				companies.append(company_doc.as_dict())

			return {"success": True, "companies": companies}
		else:
			return {"success": False, "error": "Failed to fetch companies from Invoice Ninja"}

	except Exception as e:
		frappe.log_error(f"Error fetching Invoice Ninja companies: {str(e)}", "Invoice Ninja API Error")
		return {"success": False, "error": str(e)}


# Dashboard API Methods
@frappe.whitelist()
def get_configuration():
	"""Get Invoice Ninja integration configuration for dashboard"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")

		return {
			"apiUrl": settings.invoice_ninja_url or "",
			"apiToken": bool(settings.api_token),  # Don't expose actual token
			"isConnected": settings.enabled and bool(settings.api_token),
			"autoSync": settings.enable_realtime_sync if hasattr(settings, 'enable_realtime_sync') else False,
			"syncInterval": 60  # Default sync interval
		}
	except Exception as e:
		frappe.log_error(f"Error getting configuration: {str(e)}")
		return {
			"apiUrl": "",
			"apiToken": False,
			"isConnected": False,
			"autoSync": False,
			"syncInterval": 60
		}


@frappe.whitelist()
def get_dashboard_stats():
	"""Get dashboard statistics"""
	try:
		# Count synced invoices
		total_invoices = frappe.db.count("Sales Invoice", {
			"invoice_ninja_id": ["!=", ""]
		})

		# Count synced customers
		total_clients = frappe.db.count("Customer", {
			"invoice_ninja_id": ["!=", ""]
		})

		# Count pending payments (unpaid invoices)
		pending_payments = frappe.db.count("Sales Invoice", {
			"invoice_ninja_id": ["!=", ""],
			"status": ["in", ["Draft", "Unpaid", "Partially Paid"]]
		})

		# Count overdue invoices
		overdue_invoices = frappe.db.count("Sales Invoice", {
			"invoice_ninja_id": ["!=", ""],
			"status": ["in", ["Unpaid", "Partially Paid"]],
			"due_date": ["<", frappe.utils.today()]
		})

		# Get last sync time
		last_sync_log = frappe.db.get_value(
			"Invoice Ninja Sync Logs",
			{"status": "Success"},
			"creation",
			order_by="creation desc"
		)

		return {
			"totalInvoices": total_invoices,
			"totalClients": total_clients,
			"pendingPayments": pending_payments,
			"overdueInvoices": overdue_invoices,
			"lastSyncTime": last_sync_log,
			"syncStatus": "idle"
		}
	except Exception as e:
		frappe.log_error(f"Error getting dashboard stats: {str(e)}")
		return {
			"totalInvoices": 0,
			"totalClients": 0,
			"pendingPayments": 0,
			"overdueInvoices": 0,
			"lastSyncTime": None,
			"syncStatus": "error"
		}


@frappe.whitelist()
def get_recent_activity(limit=10):
	"""Get recent sync activity"""
	try:
		# Get recent sync logs
		activities = frappe.db.get_all(
			"Invoice Ninja Sync Logs",
			fields=["name", "sync_type", "entity_type", "status", "message", "creation"],
			order_by="creation desc",
			limit=int(limit)
		)

		return [{
			"id": activity.name,
			"type": f"{activity.sync_type}_{activity.entity_type}".lower() if activity.sync_type and activity.entity_type else "sync",
			"description": activity.message or f"Synchronized {activity.entity_type or 'data'}",
			"status": activity.status.lower() if activity.status else "unknown",
			"created_at": activity.creation
		} for activity in activities]

	except Exception as e:
		frappe.log_error(f"Error getting recent activity: {str(e)}")
		return []


@frappe.whitelist()
def get_sync_logs(limit=5):
	"""Get sync logs"""
	try:
		logs = frappe.db.get_all(
			"Invoice Ninja Sync Logs",
			fields=["name", "sync_type", "entity_type", "status", "message", "creation"],
			order_by="creation desc",
			limit=int(limit)
		)

		return [{
			"id": log.name,
			"sync_type": log.sync_type or "manual",
			"entity_type": log.entity_type or "unknown",
			"status": log.status.lower() if log.status else "unknown",
			"message": log.message or f"Synchronized {log.entity_type or 'data'}",
			"created_at": log.creation
		} for log in logs]

	except Exception as e:
		frappe.log_error(f"Error getting sync logs: {str(e)}")
		return []


@frappe.whitelist()
def trigger_manual_sync(sync_type="all"):
	"""Trigger manual synchronization with company mapping support"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		results = []
		results_objects = []

		if sync_type == "customers" or sync_type == "all":
			result = sync_from_invoice_ninja("Customer", limit=100)
			results.append(f"Customers: {result}")
			results_objects.append(result)

		if sync_type == "invoices" or sync_type == "all":
			result = sync_from_invoice_ninja("Sales Invoice", limit=100)
			results.append(f"Invoices: {result}")
			results_objects.append(result)

		if sync_type == "payments" or sync_type == "all":
			# Use the existing sync_payments_from_invoice_ninja from tasks
			from .tasks import sync_payments_from_invoice_ninja
			result = sync_payments_from_invoice_ninja()
			results.append(f"Payments: {result}")
			results_objects.append(result)

		if sync_type == "quotations" or sync_type == "all":
			result = sync_from_invoice_ninja("Quotation", limit=100)
			results.append(f"Quotations: {result}")
			results_objects.append(result)

		if sync_type == "items" or sync_type == "all":
			result = sync_from_invoice_ninja("Item", limit=100)
			results.append(f"Items: {result}")
			results_objects.append(result)

		return {
			"success": True,
			"results": results_objects,
			"message": f"Manual {sync_type} sync completed: {'; '.join(results)}"
		}

	except Exception as e:
		frappe.log_error(f"Error during manual sync: {str(e)}")
		return {
			"success": False,
			"message": f"Sync failed: {str(e)}"
		}


@frappe.whitelist()
def get_company_mappings():
	"""Get all company mappings for dashboard"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")
		mappings = []

		if settings.company_mappings:
			for mapping in settings.company_mappings:
				if mapping.enabled:
					mappings.append({
						"erpnext_company": mapping.erpnext_company,
						"invoice_ninja_company_id": mapping.invoice_ninja_company_id,
						"invoice_ninja_company_name": mapping.invoice_ninja_company_name,
						"is_default": mapping.is_default,
						"enabled": mapping.enabled
					})

		return {"success": True, "mappings": mappings}
	except Exception as e:
		frappe.log_error(f"Error getting company mappings: {str(e)}")
		return {"success": False, "mappings": []}


@frappe.whitelist()
def sync_company_mappings_from_invoice_ninja():
	"""Fetch and sync company mappings from Invoice Ninja"""
	try:
		from .utils.company_mapper import CompanyMapper

		# Get Invoice Ninja companies
		companies_response = get_invoice_ninja_companies()
		if not companies_response.get("success"):
			return companies_response

		settings = frappe.get_single("Invoice Ninja Settings")
		companies = companies_response.get("companies", [])

		# Get existing mappings
		existing_mappings = {}
		if settings.company_mappings:
			for mapping in settings.company_mappings:
				existing_mappings[mapping.invoice_ninja_company_id] = mapping

		# Update or create mappings
		updated_count = 0
		for company in companies:
			company_id = str(company.get("id"))
			if company_id in existing_mappings:
				# Update existing mapping name
				existing_mappings[company_id].invoice_ninja_company_name = company.get("name")
				updated_count += 1

		settings.save()

		return {
			"success": True,
			"message": f"Updated {updated_count} company mappings",
			"companies": companies
		}

	except Exception as e:
		frappe.log_error(f"Error syncing company mappings: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_invoice_ninja_customer_groups(settings_name=None):
	"""Fetch customer groups from Invoice Ninja API"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")

		if not settings.invoice_ninja_url or not settings.api_token:
			return {"success": False, "error": "Invoice Ninja URL and API Token are required"}

		# Initialize client
		client = InvoiceNinjaClient(settings.invoice_ninja_url, settings.get_password("api_token"))

		# Fetch group settings from Invoice Ninja
		response = client._make_request('GET', 'group_settings')

		if response and 'data' in response:
			customer_groups = []
			for group in response['data']:
				# Create or update local Invoice Ninja Customer Group doc
				existing_group = frappe.db.get_all("Invoice Ninja Customer Group", filters={"group_id": str(group.get('id'))}, limit=1)

				if existing_group:
					group_doc = frappe.get_doc("Invoice Ninja Customer Group", existing_group[0].name)
					group_doc.group_name = group.get('name', f"Group {group.get('id')}")
					group_doc.save(ignore_permissions=True)
					customer_groups.append(group_doc.as_dict())
					continue

				group_doc = frappe.get_doc({
					"doctype": "Invoice Ninja Customer Group",
					"group_id": str(group.get('id')),
					"group_name": group.get('name', f"Group {group.get('id')}"),
				})

				group_doc.save(ignore_permissions=True)
				customer_groups.append(group_doc.as_dict())

			return {"success": True, "customer_groups": customer_groups}
		else:
			return {"success": False, "error": "Failed to fetch customer groups from Invoice Ninja"}

	except Exception as e:
		frappe.log_error(f"Error fetching Invoice Ninja customer groups: {str(e)}", "Invoice Ninja API Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_customer_groups_to_doctype(settings_name=None):
	"""Sync customer groups from Invoice Ninja and store in DocType"""
	try:
		# The get_invoice_ninja_customer_groups function already creates the DocType records
		result = get_invoice_ninja_customer_groups(settings_name)

		if not result.get("success"):
			return result

		# Count the customer groups that were processed
		customer_groups = result.get("customer_groups", [])
		synced_count = len(customer_groups)

		return {"success": True, "synced_count": synced_count}

	except Exception as e:
		frappe.log_error(f"Error syncing customer groups: {str(e)}", "Invoice Ninja Sync Error")
		return {"success": False, "error": str(e)}

