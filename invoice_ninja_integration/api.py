import frappe
from frappe import _
from .utils.invoice_ninja_client import InvoiceNinjaClient
from .utils.field_mapper import FieldMapper
import json


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
	"""Test Invoice Ninja API connection (deprecated - use test_invoice_ninja_company_connection)"""
	try:
		client = get_client()
		if client.test_connection():
			return {"success": True, "message": "Connection successful"}
		else:
			return {"success": False, "message": "Connection failed"}
	except Exception as e:
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_invoice_ninja_company_connection(invoice_ninja_company):
	"""
	Test connection for a specific Invoice Ninja Company

	Args:
		invoice_ninja_company: Name/ID of Invoice Ninja Company doc
	"""
	try:
		from .utils.invoice_ninja_client import InvoiceNinjaClient

		client = InvoiceNinjaClient(invoice_ninja_company=invoice_ninja_company)
		if client.test_connection():
			return {"success": True, "message": "Connection successful"}
		else:
			return {"success": False, "message": "Connection failed"}
	except Exception as e:
		frappe.log_error(f"Connection test failed for {invoice_ninja_company}: {str(e)}",
						"Invoice Ninja Connection Test")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def manual_sync_customer(customer_name):
	"""Manually sync a customer to Invoice Ninja using SyncManager"""
	try:
		from .utils.sync_manager import SyncManager

		doc = frappe.get_doc("Customer", customer_name)
		sync_manager = SyncManager()
		sync_manager.sync_document_to_invoice_ninja(doc)
		return {"success": True, "message": "Customer sync initiated"}
	except Exception as e:
		frappe.log_error(f"Error in manual_sync_customer: {str(e)}", "Manual Sync Error")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def manual_sync_invoice(invoice_name):
	"""Manually sync an invoice to Invoice Ninja using SyncManager"""
	try:
		from .utils.sync_manager import SyncManager

		doc = frappe.get_doc("Sales Invoice", invoice_name)
		sync_manager = SyncManager()
		sync_manager.sync_document_to_invoice_ninja(doc)
		return {"success": True, "message": "Invoice sync initiated"}
	except Exception as e:
		frappe.log_error(f"Error in manual_sync_invoice: {str(e)}", "Manual Sync Error")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_from_invoice_ninja(doctype, limit=50):
	"""Sync data from Invoice Ninja to ERPNext"""
	settings = frappe.get_single("Invoice Ninja Settings")
	if not settings.enabled:
		return {"success": False, "message": "Invoice Ninja integration is disabled"}

	client = get_client()

	# Get all company mappings
	from .utils.company_mapper import CompanyMapper
	company_mapper = CompanyMapper()
	mappings = company_mapper.get_all_mappings()

	# If no mappings, use default context (None)
	if not mappings:
		mappings = [{"invoice_ninja_company_id": None, "invoice_ninja_company_name": "Default"}]

	total_synced_count = 0

	for mapping in mappings:
		company_id = mapping.get("invoice_ninja_company_id")

		# Set company context
		client.set_company_id(company_id)

		synced_count = 0

		if doctype == "Customer" and settings.enable_customer_sync:
			customers = client.get_customers(per_page=limit)
			if customers and customers.get('data'):
				for customer in customers['data']:
					# Pass company context to sync function if needed, or rely on mapper inside
					# Currently sync_customer_from_invoice_ninja doesn't accept context arg in definition below
					# We should update it to accept context or handle it inside
					# Let's pass the context to the sync function
					sync_customer_from_invoice_ninja(customer) # We need to update this signature next
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

		total_synced_count += synced_count

	return {
		"success": True,
		"message": f"Synced {total_synced_count} {doctype} records from Invoice Ninja across {len(mappings)} companies",
		"synced_count": total_synced_count,
	}


def sync_customer_from_invoice_ninja(customer_data):
	"""Create/update ERPNext customer from Invoice Ninja data"""
	# Check if customer already exists
	existing = frappe.db.exists("Customer", {"invoice_ninja_id": str(customer_data.get('id'))})

	customer_doc_data, address_data, shipping_address_data, contact_data_list = FieldMapper.map_customer_from_invoice_ninja(customer_data)
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

	# Handle contacts
	if contact_data_list:
		for contact_data in contact_data_list:
			existing_contact_name = None

			# 1. Check by Invoice Ninja ID
			if contact_data.get("invoice_ninja_contact_id"):
				existing_contact_name = frappe.db.get_value("Contact",
					{"invoice_ninja_contact_id": contact_data["invoice_ninja_contact_id"]}, "name")

			# 2. Check by Email
			if not existing_contact_name and contact_data.get("email_id"):
				existing_contact_name = frappe.db.get_value("Contact",
					{"email_id": contact_data["email_id"]}, "name")

			# 3. Check by Phone
			if not existing_contact_name and contact_data.get("phone"):
				existing_contact_name = frappe.db.get_value("Contact",
					{"phone": contact_data["phone"]}, "name")

			if existing_contact_name:
				# Link existing contact
				contact_doc = frappe.get_doc("Contact", existing_contact_name)

				# Check for existing link
				is_linked = False
				for link in contact_doc.links:
					if link.link_doctype == "Customer" and link.link_name == doc.name:
						is_linked = True
						break

				if not is_linked:
					contact_doc.append("links", {"link_doctype": "Customer", "link_name": doc.name})
					contact_doc.save()

				# Optionally update Invoice Ninja ID if matched by email/phone
				if not contact_doc.get("invoice_ninja_contact_id") and contact_data.get("invoice_ninja_contact_id"):
					contact_doc.db_set("invoice_ninja_contact_id", contact_data["invoice_ninja_contact_id"])

			else:
				# Create new contact
				# Ensure link points to the correct doc.name
				contact_data["links"] = [{"link_doctype": "Customer", "link_name": doc.name}]
				new_contact = frappe.get_doc(contact_data)
				new_contact.insert()

	frappe.db.commit()


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
	"""
	Fetch companies from Invoice Ninja API (legacy method)
	Use fetch_and_create_invoice_ninja_companies for new implementations
	"""
	return fetch_and_create_invoice_ninja_companies()


@frappe.whitelist()
def fetch_and_create_invoice_ninja_companies():
	"""
	Fetch companies from Invoice Ninja using master credentials
	and create/update Invoice Ninja Company docs

	Returns:
		{
			"success": bool,
			"message": str,
			"companies_created": int,
			"companies_updated": int,
			"companies": [...]
		}
	"""
	try:
		settings = frappe.get_single("Invoice Ninja Settings")

		# Validate master credentials
		if not settings.invoice_ninja_url or not settings.api_token:
			return {
				"success": False,
				"message": "Master credentials not configured. Please enter Invoice Ninja URL and API Token in Settings."
			}

		# Use master credentials for discovery
		client = InvoiceNinjaClient(
			url=settings.invoice_ninja_url,
			token=settings.get_password("api_token")
		)

		# Fetch companies from Invoice Ninja
		response = client._make_request('GET', 'companies')

		if not response or 'data' not in response:
			return {
				"success": False,
				"message": "Failed to fetch companies from Invoice Ninja. Please check your credentials."
			}

		created = 0
		updated = 0
		companies_info = []

		for company_data in response['data']:
			company_id = str(company_data.get('id'))
			company_name = company_data.get('settings', {}).get('name') or f"Company {company_id}"

			# Check if exists
			existing = frappe.db.exists("Invoice Ninja Company", {"company_id": company_id})

			if existing:
				# Update existing
				doc = frappe.get_doc("Invoice Ninja Company", existing)
				doc.company_name = company_name
				doc.invoice_ninja_url = settings.invoice_ninja_url
				# Don't touch api_token - user must set manually
				doc.save(ignore_permissions=True)
				updated += 1
			else:
				# Create new
				doc = frappe.get_doc({
					"doctype": "Invoice Ninja Company",
					"company_id": company_id,
					"company_name": company_name,
					"invoice_ninja_url": settings.invoice_ninja_url,
					# api_token left blank - must be set manually
					"enabled": 0,  # Disabled until token is set
					"connection_status": "Not Tested"
				})
				doc.insert(ignore_permissions=True)
				created += 1

			# Check if password exists before trying to retrieve it
			has_token = False
			if frappe.db.exists("__Auth", {
				"doctype": "Invoice Ninja Company",
				"name": doc.name,
				"fieldname": "api_token"
			}):
				has_token = bool(doc.get_password("api_token"))

			companies_info.append({
				"company_id": company_id,
				"company_name": company_name,
				"doc_name": doc.name,
				"has_token": has_token
			})

		frappe.db.commit()

		return {
			"success": True,
			"message": f"Created {created}, Updated {updated} companies",
			"companies_created": created,
			"companies_updated": updated,
			"companies": companies_info
		}

	except Exception as e:
		frappe.log_error(f"Error fetching Invoice Ninja companies: {str(e)}", "Invoice Ninja API Error")
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


# Company-Specific Sync API Methods
@frappe.whitelist()
def sync_company_entities(invoice_ninja_company, entity_type, limit=100):
	"""
	Sync specific entity type for a single Invoice Ninja Company

	Args:
		invoice_ninja_company: Name of Invoice Ninja Company doc
		entity_type: Customer, Sales Invoice, Quotation, Item, Payment Entry
		limit: Number of records to sync

	Returns:
		{success, message, synced_count, failed_count, logs}
	"""
	from .utils.sync_manager import SyncManager
	from datetime import datetime

	start_time = datetime.now()

	try:
		# Validate company
		company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)
		if not company_doc.enabled:
			return {"success": False, "message": "Company is disabled"}

		# Get company mapping
		sync_manager = SyncManager()
		mapping = sync_manager.company_mapper.get_company_mapping(
			invoice_ninja_company_id=company_doc.name
		)


		if not mapping:
			return {"success": False, "message": "No company mapping found for this Invoice Ninja Company"}

		# Perform sync
		result = sync_manager.fetch_entities_for_company(
			entity_type,
			invoice_ninja_company_id=company_doc.name,
			page=1,
			per_page=int(limit)
		)

		duration = (datetime.now() - start_time).total_seconds()

		# Update company sync stats
		if result.get("success"):
			update_company_sync_stats(
				invoice_ninja_company,
				entity_type,
				result.get("total_fetched", 0),
				"Success",
				duration
			)
		else:
			update_company_sync_stats(
				invoice_ninja_company,
				entity_type,
				0,
				"Failed",
				duration
			)

		return result

	except Exception as e:
		duration = (datetime.now() - start_time).total_seconds()
		frappe.log_error(f"Company sync failed: {str(e)}", "Company Sync Error")

		update_company_sync_stats(
			invoice_ninja_company,
			entity_type,
			0,
			"Failed",
			duration
		)

		return {
			"success": False,
			"message": f"Sync failed: {str(e)}"
		}


@frappe.whitelist()
def sync_company_all_entities(invoice_ninja_company, entity_types=None, limit=100):
	"""Sync multiple entity types for a single company"""
	if not entity_types:
		entity_types = ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]

	if isinstance(entity_types, str):
		import json
		entity_types = json.loads(entity_types)

	results = {}
	total_synced = 0
	total_failed = 0

	for entity_type in entity_types:
		result = sync_company_entities(invoice_ninja_company, entity_type, limit)
		results[entity_type] = result
		if result.get("success"):
			total_synced += result.get("total_fetched", 0)
		else:
			total_failed += 1

	return {
		"success": total_failed == 0,
		"message": f"Synced {total_synced} records across {len(entity_types)} entity types",
		"total_synced": total_synced,
		"total_failed": total_failed,
		"details": results
	}


@frappe.whitelist()
def get_company_sync_statistics(invoice_ninja_company, days=7):
	"""Get sync statistics for a specific company"""
	from frappe.utils import add_days, now_datetime

	start_date = add_days(now_datetime(), -int(days))

	# Get sync logs for this company
	logs = frappe.get_all(
		"Invoice Ninja Sync Logs",
		filters={
			"invoice_ninja_company": invoice_ninja_company,
			"sync_timestamp": [">=", start_date]
		},
		fields=["status", "duration", "record_type"]
	)

	stats = {
		"successful_syncs": len([l for l in logs if l.status == "Success"]),
		"failed_syncs": len([l for l in logs if l.status == "Failed"]),
		"total_records": len(logs),
		"avg_duration": round(sum([l.duration or 0 for l in logs]) / len(logs) if logs else 0, 2),
		"by_entity": {}
	}

	# Group by entity type
	for log in logs:
		entity = log.record_type
		if entity not in stats["by_entity"]:
			stats["by_entity"][entity] = {"success": 0, "failed": 0}

		if log.status == "Success":
			stats["by_entity"][entity]["success"] += 1
		elif log.status == "Failed":
			stats["by_entity"][entity]["failed"] += 1

	return stats


def update_company_sync_stats(invoice_ninja_company, entity_type, count, status, duration):
	"""Update sync statistics on Invoice Ninja Company doc"""
	try:
		company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)

		# Update last sync info
		company_doc.last_sync_time = frappe.utils.now()
		company_doc.last_sync_status = status

		# Update entity-specific counters
		entity_field_map = {
			"Customer": "customers_synced",
			"Sales Invoice": "invoices_synced",
			"Quotation": "quotations_synced",
			"Item": "items_synced",
			"Payment Entry": "payments_synced"
		}

		if entity_type in entity_field_map:
			field = entity_field_map[entity_type]
			current = company_doc.get(field) or 0
			company_doc.set(field, current + count)

		# Update total
		company_doc.total_synced_records = (company_doc.total_synced_records or 0) + count

		# Update failed count if applicable
		if status == "Failed":
			company_doc.failed_syncs_count = (company_doc.failed_syncs_count or 0) + 1

		company_doc.save(ignore_permissions=True)
		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error updating company sync stats: {str(e)}", "Sync Stats Update Error")


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


@frappe.whitelist()
def get_customers_for_mapped_companies(page=1, per_page=100):
	"""
	Get customers from Invoice Ninja for all mapped companies - uses centralized SyncManager

	Args:
		page: Page number for pagination (default: 1)
		per_page: Number of customers per page (default: 100)

	Returns:
		dict: {
			"success": bool,
			"companies": [
				{
					"erpnext_company": str,
					"invoice_ninja_company_id": str,
					"invoice_ninja_company_name": str,
					"customers": [...],
					"customer_count": int
				}
			],
			"total_customers": int,
			"message": str
		}
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_customers_for_mapped_companies(
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain backward compatibility (entities -> customers)
		if result.get("success") and "companies" in result:
			for company in result["companies"]:
				company["customers"] = company.pop("entities", [])
				company["customer_count"] = company.pop("entity_count", 0)
			result["total_customers"] = result.pop("total_entities", 0)

		return result

	except Exception as e:
		error_msg = f"Error fetching customers for mapped companies: {str(e)}"
		frappe.log_error(error_msg, "Invoice Ninja Customer Fetch Error")
		return {
			"success": False,
			"message": error_msg,
			"companies": [],
			"total_customers": 0
		}


@frappe.whitelist()
def get_customers_for_company(erpnext_company=None, invoice_ninja_company_id=None, page=1, per_page=100):
	"""
	Get customers from Invoice Ninja for a specific company - uses centralized SyncManager

	Args:
		erpnext_company: ERPNext company name (optional)
		invoice_ninja_company_id: Invoice Ninja company ID (optional)
		page: Page number for pagination (default: 1)
		per_page: Number of customers per page (default: 100)

	Returns:
		dict: {
			"success": bool,
			"erpnext_company": str,
			"invoice_ninja_company_id": str,
			"invoice_ninja_company_name": str,
			"customers": [...],
			"customer_count": int,
			"message": str
		}
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_customers_for_company(
			erpnext_company=erpnext_company,
			invoice_ninja_company_id=invoice_ninja_company_id,
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain backward compatibility (entities -> customers)
		if result.get("success") and "entities" in result:
			result["customers"] = result.pop("entities", [])
			result["customer_count"] = result.pop("entity_count", 0)

		return result

	except Exception as e:
		error_msg = f"Error fetching customers for company: {str(e)}"
		frappe.log_error(error_msg, "Invoice Ninja Customer Fetch Error")
		return {
			"success": False,
			"message": error_msg
		}


# ============================================================================
# INVOICE API METHODS
# ============================================================================

@frappe.whitelist()
def get_invoices_for_mapped_companies(page=1, per_page=100):
	"""
	Get invoices from Invoice Ninja for all mapped companies - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_invoices_for_mapped_companies(
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> invoices)
		if result.get("success") and "companies" in result:
			for company in result["companies"]:
				company["invoices"] = company.pop("entities", [])
				company["invoice_count"] = company.pop("entity_count", 0)
			result["total_invoices"] = result.pop("total_entities", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching invoices: {str(e)}", "Invoice Fetch Error")
		return {"success": False, "message": str(e), "companies": [], "total_invoices": 0}


@frappe.whitelist()
def get_invoices_for_company(erpnext_company=None, invoice_ninja_company_id=None, page=1, per_page=100):
	"""
	Get invoices from Invoice Ninja for a specific company - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_invoices_for_company(
			erpnext_company=erpnext_company,
			invoice_ninja_company_id=invoice_ninja_company_id,
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> invoices)
		if result.get("success") and "entities" in result:
			result["invoices"] = result.pop("entities", [])
			result["invoice_count"] = result.pop("entity_count", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching invoices: {str(e)}", "Invoice Fetch Error")
		return {"success": False, "message": str(e)}


# ============================================================================
# QUOTATION API METHODS
# ============================================================================

@frappe.whitelist()
def get_quotations_for_mapped_companies(page=1, per_page=100):
	"""
	Get quotations from Invoice Ninja for all mapped companies - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_quotations_for_mapped_companies(
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> quotations)
		if result.get("success") and "companies" in result:
			for company in result["companies"]:
				company["quotations"] = company.pop("entities", [])
				company["quotation_count"] = company.pop("entity_count", 0)
			result["total_quotations"] = result.pop("total_entities", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching quotations: {str(e)}", "Quotation Fetch Error")
		return {"success": False, "message": str(e), "companies": [], "total_quotations": 0}


@frappe.whitelist()
def get_quotations_for_company(erpnext_company=None, invoice_ninja_company_id=None, page=1, per_page=100):
	"""
	Get quotations from Invoice Ninja for a specific company - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_quotations_for_company(
			erpnext_company=erpnext_company,
			invoice_ninja_company_id=invoice_ninja_company_id,
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> quotations)
		if result.get("success") and "entities" in result:
			result["quotations"] = result.pop("entities", [])
			result["quotation_count"] = result.pop("entity_count", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching quotations: {str(e)}", "Quotation Fetch Error")
		return {"success": False, "message": str(e)}


# ============================================================================
# ITEM API METHODS
# ============================================================================

@frappe.whitelist()
def get_items_for_mapped_companies(page=1, per_page=100):
	"""
	Get items from Invoice Ninja for all mapped companies - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_items_for_mapped_companies(
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> items)
		if result.get("success") and "companies" in result:
			for company in result["companies"]:
				company["items"] = company.pop("entities", [])
				company["item_count"] = company.pop("entity_count", 0)
			result["total_items"] = result.pop("total_entities", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching items: {str(e)}", "Item Fetch Error")
		return {"success": False, "message": str(e), "companies": [], "total_items": 0}


@frappe.whitelist()
def get_items_for_company(erpnext_company=None, invoice_ninja_company_id=None, page=1, per_page=100):
	"""
	Get items from Invoice Ninja for a specific company - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_items_for_company(
			erpnext_company=erpnext_company,
			invoice_ninja_company_id=invoice_ninja_company_id,
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> items)
		if result.get("success") and "entities" in result:
			result["items"] = result.pop("entities", [])
			result["item_count"] = result.pop("entity_count", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching items: {str(e)}", "Item Fetch Error")
		return {"success": False, "message": str(e)}


# ============================================================================
# PAYMENT API METHODS
# ============================================================================

@frappe.whitelist()
def get_payments_for_mapped_companies(page=1, per_page=100):
	"""
	Get payments from Invoice Ninja for all mapped companies - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_payments_for_mapped_companies(
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> payments)
		if result.get("success") and "companies" in result:
			for company in result["companies"]:
				company["payments"] = company.pop("entities", [])
				company["payment_count"] = company.pop("entity_count", 0)
			result["total_payments"] = result.pop("total_entities", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching payments: {str(e)}", "Payment Fetch Error")
		return {"success": False, "message": str(e), "companies": [], "total_payments": 0}


@frappe.whitelist()
def get_payments_for_company(erpnext_company=None, invoice_ninja_company_id=None, page=1, per_page=100):
	"""
	Get payments from Invoice Ninja for a specific company - uses centralized SyncManager
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()
		result = sync_manager.fetch_payments_for_company(
			erpnext_company=erpnext_company,
			invoice_ninja_company_id=invoice_ninja_company_id,
			page=int(page),
			per_page=int(per_page)
		)

		# Transform result to maintain consistency (entities -> payments)
		if result.get("success") and "entities" in result:
			result["payments"] = result.pop("entities", [])
			result["payment_count"] = result.pop("entity_count", 0)

		return result

	except Exception as e:
		frappe.log_error(f"Error fetching payments: {str(e)}", "Payment Fetch Error")
		return {"success": False, "message": str(e)}


# ============================================================================
# GENERIC API ENDPOINT
# ============================================================================

@frappe.whitelist()
def fetch_entities(entity_type, scope="all_companies", company_identifier=None, page=1, per_page=100):
	"""
	Generic endpoint to fetch any entity type from Invoice Ninja

	Args:
		entity_type: Customer, Sales Invoice, Quotation, Item, Payment Entry
		scope: "all_companies" or "single_company" (default: "all_companies")
		company_identifier: ERPNext company name or Invoice Ninja company ID (required if scope="single_company")
		page: Page number for pagination (default: 1)
		per_page: Number of records per page (default: 100)

	Returns:
		dict: Result with entities/companies data based on scope

	Example:
		# Fetch all customers from all companies
		fetch_entities("Customer", "all_companies")

		# Fetch invoices for specific company
		fetch_entities("Sales Invoice", "single_company", "Company A")
	"""
	try:
		from .utils.sync_manager import SyncManager

		sync_manager = SyncManager()

		# Validate entity type
		if entity_type not in sync_manager.ENTITY_CONFIG:
			return {
				"success": False,
				"message": f"Invalid entity type: {entity_type}. Valid types: {list(sync_manager.ENTITY_CONFIG.keys())}"
			}

		# Fetch based on scope
		if scope == "all_companies":
			result = sync_manager.fetch_entities_for_mapped_companies(
				entity_type,
				page=int(page),
				per_page=int(per_page)
			)
		elif scope == "single_company":
			if not company_identifier:
				return {
					"success": False,
					"message": "company_identifier is required when scope is 'single_company'"
				}

			# Determine if company_identifier is ERPNext company or Invoice Ninja ID
			# Simple heuristic: if it's all digits, assume it's Invoice Ninja ID
			if company_identifier.isdigit():
				result = sync_manager.fetch_entities_for_company(
					entity_type,
					invoice_ninja_company_id=company_identifier,
					page=int(page),
					per_page=int(per_page)
				)
			else:
				result = sync_manager.fetch_entities_for_company(
					entity_type,
					erpnext_company=company_identifier,
					page=int(page),
					per_page=int(per_page)
				)
		else:
			return {
				"success": False,
				"message": f"Invalid scope: {scope}. Valid scopes: 'all_companies', 'single_company'"
			}

		return result

	except Exception as e:
		error_msg = f"Error in fetch_entities: {str(e)}"
		frappe.log_error(error_msg, "Generic Entity Fetch Error")
		return {
			"success": False,
			"message": error_msg
		}

