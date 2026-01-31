import frappe

from invoice_ninja_integration.utils.base_integration_service import BaseIntegrationService
from invoice_ninja_integration.utils.company_mapper import CompanyMapper
from invoice_ninja_integration.utils.field_mapper import FieldMapper
from invoice_ninja_integration.utils.invoice_ninja_client import InvoiceNinjaClient


class SyncManager(BaseIntegrationService):
	"""
	Invoice Ninja Integration Service

	Extends BaseIntegrationService with Invoice Ninja specific implementations.
	Manages bidirectional synchronization between Invoice Ninja and ERPNext
	with proper company mapping support.
	"""

	# Settings DocType for this integration
	SETTINGS_DOCTYPE = "Invoice Ninja Settings"

	# Entity type configuration for generic fetch/sync operations
	ENTITY_CONFIG = {
		"Customer": {
			"invoice_ninja_endpoint": "clients",
			"invoice_ninja_method": "get_customers",
			"erpnext_doctype": "Customer",
			"include_params": "contacts,group_settings"
		},
		"Sales Invoice": {
			"invoice_ninja_endpoint": "invoices",
			"invoice_ninja_method": "get_invoices",
			"erpnext_doctype": "Sales Invoice",
			"include_params": "client,line_items"
		},
		"Quotation": {
			"invoice_ninja_endpoint": "quotes",
			"invoice_ninja_method": "get_quotes",
			"erpnext_doctype": "Quotation",
			"include_params": "client,line_items"
		},
		"Item": {
			"invoice_ninja_endpoint": "products",
			"invoice_ninja_method": "get_products",
			"erpnext_doctype": "Item",
			"include_params": None
		},
		"Payment Entry": {
			"invoice_ninja_endpoint": "payments",
			"invoice_ninja_method": "get_payments",
			"erpnext_doctype": "Payment Entry",
			"include_params": "invoice,client"
		}
	}

	def _init_components(self):
		"""Initialize Invoice Ninja specific components"""
		# Don't initialize a single client - create per company as needed
		self.mapper = FieldMapper()
		self.company_mapper = CompanyMapper()
		self.clients = {}  # Cache of clients per Invoice Ninja Company doc

	def get_client_for_mapping(self, mapping):
		"""
		Get or create client for specific company mapping

		Args:
			mapping: Company mapping dict with invoice_ninja_company_id

		Returns:
			tuple: (InvoiceNinjaClient instance, Invoice Ninja Company doc name)
		"""
		in_company_doc = mapping.get("invoice_ninja_company_id")

		if not in_company_doc:
			frappe.throw(f"Invoice Ninja Company not found for company_id {in_company_doc}")

		# Cache the client per doc to avoid recreating
		if in_company_doc not in self.clients:
			self.clients[in_company_doc] = InvoiceNinjaClient(
				invoice_ninja_company=in_company_doc
			)

		return self.clients[in_company_doc], in_company_doc

	def get_sync_direction(self, doc_type):
		"""Get sync direction for a specific document type"""
		field_map = {
			"Customer": "customer_sync_direction",
			"Sales Invoice": "invoice_sync_direction",
			"Quotation": "quote_sync_direction",
			"Item": "product_sync_direction",
			"Payment Entry": "payment_sync_direction",
		}

		field_name = field_map.get(doc_type)
		if not field_name:
			return None

		return self.settings.get(field_name, "Invoice Ninja to ERPNext")

	def should_sync_from_erpnext(self, doc_type):
		"""Check if document should be synced from ERPNext to Invoice Ninja"""
		direction = self.get_sync_direction(doc_type)
		return direction in ["ERPNext to Invoice Ninja", "Bidirectional"]

	def should_sync_from_invoice_ninja(self, doc_type):
		"""Check if document should be synced from Invoice Ninja to ERPNext"""
		direction = self.get_sync_direction(doc_type)
		return direction in ["Invoice Ninja to ERPNext", "Bidirectional"]

	def is_sync_enabled(self, doc_type):
		"""Check if sync is enabled for a document type"""
		enable_map = {
			"Customer": "enable_customer_sync",
			"Sales Invoice": "enable_invoice_sync",
			"Quotation": "enable_quote_sync",
			"Item": "enable_product_sync",
			"Payment Entry": "enable_payment_sync",
		}

		field_name = enable_map.get(doc_type)
		if not field_name:
			return False

		return self.settings.get(field_name, 0)

	def sync_document_to_invoice_ninja(self, doc):
		"""
		Sync ERPNext document to Invoice Ninja with per-company credentials
		"""
		if not self.is_sync_enabled(doc.doctype):
			frappe.logger().info(f"Sync disabled for {doc.doctype}")
			return

		if not self.should_sync_from_erpnext(doc.doctype):
			frappe.logger().info(f"ERPNext to Invoice Ninja sync disabled for {doc.doctype}")
			return

		# Check company mapping
		if not self.company_mapper.should_sync_document(doc):
			frappe.logger().info(f"Document {doc.name} skipped - no valid company mapping")
			return

		try:
			# Get company mapping
			erpnext_company = getattr(doc, 'company', None)
			mapping = self.company_mapper.get_company_mapping(erpnext_company=erpnext_company)

			if not mapping:
				frappe.throw(f"No company mapping found for {erpnext_company}")

			# Get client for this company
			client, in_company_doc = self.get_client_for_mapping(mapping)

			# Get company context (for backward compatibility with sync methods)
			company_context = self.company_mapper.set_company_context(doc)
			company_context["invoice_ninja_company_doc"] = in_company_doc

			if doc.doctype == "Customer":
				return self._sync_customer_to_invoice_ninja(doc, company_context, client)
			elif doc.doctype == "Sales Invoice":
				return self._sync_invoice_to_invoice_ninja(doc, company_context, client)
			elif doc.doctype == "Quotation":
				return self._sync_quote_to_invoice_ninja(doc, company_context, client)
			elif doc.doctype == "Item":
				return self._sync_product_to_invoice_ninja(doc, company_context, client)
			elif doc.doctype == "Payment Entry":
				return self._sync_payment_to_invoice_ninja(doc, company_context, client)

		except Exception as e:
			frappe.logger().error(f"Error syncing {doc.doctype} {doc.name} to Invoice Ninja: {e!s}")
			self._log_sync_error(doc, "ERPNext to Invoice Ninja", str(e))

	def sync_document_from_invoice_ninja(self, invoice_ninja_data, doc_type):
		"""
		Sync Invoice Ninja data to ERPNext with company mapping
		"""
		if not self.is_sync_enabled(doc_type):
			frappe.logger().info(f"Sync disabled for {doc_type}")
			return

		if not self.should_sync_from_invoice_ninja(doc_type):
			frappe.logger().info(f"Invoice Ninja to ERPNext sync disabled for {doc_type}")
			return

		# try:
		# Get company context from Invoice Ninja data
		company_context = self.company_mapper.set_company_context(None, invoice_ninja_data)

		if not company_context.get("erpnext_company"):
			frappe.logger().error(
				f"No ERPNext company mapping found for Invoice Ninja company {invoice_ninja_data.get('company_id')}"
			)
			return

		if doc_type == "Customer":
			return self._sync_customer_from_invoice_ninja(invoice_ninja_data, company_context)
		elif doc_type == "Sales Invoice":
			return self._sync_invoice_from_invoice_ninja(invoice_ninja_data)
		elif doc_type == "Quotation":
			return self._sync_quote_from_invoice_ninja(invoice_ninja_data)
		elif doc_type == "Item":
			return self._sync_product_from_invoice_ninja(invoice_ninja_data)
		elif doc_type == "Payment Entry":
			return self._sync_payment_from_invoice_ninja(invoice_ninja_data)

		# except Exception as e:
		# 	frappe.logger().error(f"Error syncing {doc_type} from Invoice Ninja: {e!s}")
		# 	self._log_sync_error(None, "Invoice Ninja to ERPNext", str(e), invoice_ninja_data)

	def _sync_customer_to_invoice_ninja(self, customer, company_context):
		"""Sync ERPNext Customer to Invoice Ninja with company context"""
		# Check if customer already exists in Invoice Ninja
		in_customer_id = customer.get("custom_invoice_ninja_id")

		# Map ERPNext customer to Invoice Ninja format with company context
		customer_data = self.mapper.map_customer_to_invoice_ninja(customer)

		# Add company context to customer data
		if company_context.get("invoice_ninja_company_id"):
			customer_data["company_id"] = company_context["invoice_ninja_company_id"]

		if in_customer_id:
			# Update existing customer
			result = self.client.update_customer(in_customer_id, customer_data)
		else:
			# Create new customer
			result = self.client.create_customer(customer_data)
			if result.get("id"):
				# Update ERPNext with Invoice Ninja ID
				customer.db_set("custom_invoice_ninja_id", result["id"])

		self._log_sync_success(
			customer,
			"ERPNext to Invoice Ninja",
			f"Customer synced to company {company_context.get('invoice_ninja_company_name', 'Unknown')}",
		)
		return result

	def _sync_customer_from_invoice_ninja(self, customer_data, company_context):
		"""Sync Invoice Ninja Customer to ERPNext with company context"""
		# Check if customer already exists
		existing_customer = frappe.db.get_value(
			"Customer", {"invoice_ninja_id": customer_data.get("id")}, "name"
		)

		# Map Invoice Ninja customer to ERPNext format (returns customer, address, shipping_address, contacts)
		mapped_data = self.mapper.map_customer_from_invoice_ninja(customer_data)

		frappe.logger().info(mapped_data)

		if not mapped_data or not mapped_data[0]:
			frappe.logger().error(
				f"Failed to map customer data for Invoice Ninja customer {customer_data.get('id')}"
			)
			return None

		erpnext_customer_data, address_data, shipping_address_data, contact_data_list = mapped_data

		# Set the correct ERPNext company from mapping
		if company_context.get("erpnext_company"):
			erpnext_customer_data["company"] = company_context["erpnext_company"]

		customer_doc = None
		if existing_customer:
			# Update existing customer
			customer_doc = frappe.get_doc("Customer", existing_customer)
			customer_doc.update(erpnext_customer_data)
			customer_doc.save()
		else:
			# Create new customer
			erpnext_customer_data["invoice_ninja_id"] = customer_data.get("id")
			customer_doc = frappe.get_doc(erpnext_customer_data)
			customer_doc.insert()

		# Handle billing address
		if address_data:
			self._create_or_update_address(address_data, customer_doc.name, "Customer")

		# Handle shipping address (if different from billing)
		if shipping_address_data:
			self._create_or_update_address(shipping_address_data, customer_doc.name, "Customer")

		# Handle contacts
		if contact_data_list:
			for contact_data in contact_data_list:
				self._create_or_update_contact(contact_data, customer_doc.name, "Customer")

		self._log_sync_success(
			customer_doc,
			"Invoice Ninja to ERPNext",
			f"Customer synced from company {company_context.get('invoice_ninja_company_name', 'Unknown')}",
		)
		return customer_doc

	def _create_or_update_address(self, address_data, link_name, link_doctype):
		"""Create or update address for a customer/supplier"""
		if not address_data:
			return None

		try:
			# Check if address already exists based on address_title or address fields
			existing_address = None
			if address_data.get("address_title"):
				existing_address = frappe.db.get_value(
					"Address",
					{
						"address_title": address_data["address_title"],
						"link_doctype": link_doctype,
						"link_name": link_name,
					},
					"name",
				)

			if existing_address:
				# Update existing address
				address_doc = frappe.get_doc("Address", existing_address)
				address_doc.update(address_data)
				address_doc.save()
			else:
				# Create new address
				address_doc = frappe.new_doc("Address")
				address_doc.update(address_data)

				# Add link to customer/supplier
				address_doc.append("links", {"link_doctype": link_doctype, "link_name": link_name})

				address_doc.insert()

			return address_doc

		except Exception as e:
			frappe.logger().error(f"Error creating/updating address for {link_name}: {e!s}")
			return None

	def _create_or_update_contact(self, contact_data, link_name, link_doctype):
		"""Create or update contact for a customer/supplier"""
		if not contact_data:
			return None

		try:
			# Check if contact already exists based on email or phone
			existing_contact = None
			if contact_data.get("email_id"):
				existing_contact = frappe.db.get_value(
					"Contact",
					{
						"email_id": contact_data["email_id"],
						"link_doctype": link_doctype,
						"link_name": link_name,
					},
					"name",
				)
			elif contact_data.get("phone"):
				existing_contact = frappe.db.get_value(
					"Contact",
					{"phone": contact_data["phone"], "link_doctype": link_doctype, "link_name": link_name},
					"name",
				)

			if existing_contact:
				# Update existing contact
				contact_doc = frappe.get_doc("Contact", existing_contact)
				contact_doc.update(contact_data)
				contact_doc.save()
			else:
				# Create new contact
				contact_doc = frappe.new_doc("Contact")
				contact_doc.update(contact_data)

				# Add link to customer/supplier
				contact_doc.append("links", {"link_doctype": link_doctype, "link_name": link_name})

				contact_doc.insert()

			return contact_doc

		except Exception as e:
			frappe.logger().error(f"Error creating/updating contact for {link_name}: {e!s}")
			return None

	def _sync_invoice_to_invoice_ninja(self, invoice, company_context):
		"""Sync ERPNext Sales Invoice to Invoice Ninja with company context"""
		# Map ERPNext invoice to Invoice Ninja format
		invoice_data = self.mapper.map_invoice_to_invoice_ninja(invoice)

		# Add company context to invoice data
		if company_context.get("invoice_ninja_company_id"):
			invoice_data["company_id"] = company_context["invoice_ninja_company_id"]

		in_invoice_id = invoice.get("custom_invoice_ninja_id")
		if in_invoice_id:
			result = self.client.update_invoice(in_invoice_id, invoice_data)
		else:
			result = self.client.create_invoice(invoice_data)
			if result.get("id"):
				invoice.db_set("custom_invoice_ninja_id", result["id"])

		self._log_sync_success(
			invoice,
			"ERPNext to Invoice Ninja",
			f"Invoice synced to company {company_context.get('invoice_ninja_company_name', 'Unknown')}",
		)
		return result

	def _sync_invoice_from_invoice_ninja(self, invoice_data, company_context):
		"""Sync Invoice Ninja Invoice to ERPNext with company context"""
		# Check if invoice already exists
		existing_invoice = frappe.db.get_value(
			"Sales Invoice", {"custom_invoice_ninja_id": invoice_data.get("id")}, "name"
		)

		erpnext_data = self.mapper.map_invoice_from_invoice_ninja(invoice_data)

		if existing_invoice:
			invoice_doc = frappe.get_doc("Sales Invoice", existing_invoice)
			invoice_doc.update(erpnext_data)
			invoice_doc.save()
		else:
			invoice_doc = frappe.new_doc("Sales Invoice")
			invoice_doc.update(erpnext_data)
			invoice_doc.custom_invoice_ninja_id = invoice_data.get("id")
			invoice_doc.insert()

		return invoice_doc

	def _sync_quote_to_invoice_ninja(self, quote):
		"""Sync ERPNext Quotation to Invoice Ninja"""
		quote_data = self.mapper.map_quote_to_invoice_ninja(quote)

		in_quote_id = quote.get("custom_invoice_ninja_id")
		if in_quote_id:
			result = self.client.update_quote(in_quote_id, quote_data)
		else:
			result = self.client.create_quote(quote_data)
			if result.get("id"):
				frappe.db.set_value("Quotation", quote.name, "custom_invoice_ninja_id", result["id"])
				frappe.db.commit()

		return result

	def _sync_quote_from_invoice_ninja(self, quote_data):
		"""Sync Invoice Ninja Quote to ERPNext"""
		existing_quote = frappe.db.get_value(
			"Quotation", {"custom_invoice_ninja_id": quote_data.get("id")}, "name"
		)

		erpnext_data = self.mapper.map_quote_from_invoice_ninja(quote_data)

		if existing_quote:
			quote_doc = frappe.get_doc("Quotation", existing_quote)
			quote_doc.update(erpnext_data)
			quote_doc.save()
		else:
			quote_doc = frappe.new_doc("Quotation")
			quote_doc.update(erpnext_data)
			quote_doc.custom_invoice_ninja_id = quote_data.get("id")
			quote_doc.insert()

		return quote_doc

	def _sync_product_to_invoice_ninja(self, item):
		"""Sync ERPNext Item to Invoice Ninja"""
		product_data = self.mapper.map_product_to_invoice_ninja(item)

		in_product_id = item.get("custom_invoice_ninja_id")
		if in_product_id:
			result = self.client.update_product(in_product_id, product_data)
		else:
			result = self.client.create_product(product_data)
			if result.get("id"):
				frappe.db.set_value("Item", item.name, "custom_invoice_ninja_id", result["id"])
				frappe.db.commit()

		return result

	def _sync_product_from_invoice_ninja(self, product_data):
		"""Sync Invoice Ninja Product to ERPNext"""
		existing_item = frappe.db.get_value(
			"Item", {"custom_invoice_ninja_id": product_data.get("id")}, "name"
		)

		erpnext_data = self.mapper.map_product_from_invoice_ninja(product_data)

		if existing_item:
			item_doc = frappe.get_doc("Item", existing_item)
			item_doc.update(erpnext_data)
			item_doc.save()
		else:
			item_doc = frappe.new_doc("Item")
			item_doc.update(erpnext_data)
			item_doc.custom_invoice_ninja_id = product_data.get("id")
			item_doc.insert()

		return item_doc

	def _sync_payment_to_invoice_ninja(self, payment):
		"""Sync ERPNext Payment Entry to Invoice Ninja"""
		payment_data = self.mapper.map_payment_to_invoice_ninja(payment)

		in_payment_id = payment.get("custom_invoice_ninja_id")
		if in_payment_id:
			result = self.client.update_payment(in_payment_id, payment_data)
		else:
			result = self.client.create_payment(payment_data)
			if result.get("id"):
				frappe.db.set_value("Payment Entry", payment.name, "custom_invoice_ninja_id", result["id"])
				frappe.db.commit()

		return result

	def _sync_payment_from_invoice_ninja(self, payment_data):
		"""Sync Invoice Ninja Payment to ERPNext"""
		existing_payment = frappe.db.get_value(
			"Payment Entry", {"custom_invoice_ninja_id": payment_data.get("id")}, "name"
		)

		erpnext_data = self.mapper.map_payment_from_invoice_ninja(payment_data)

		if existing_payment:
			payment_doc = frappe.get_doc("Payment Entry", existing_payment)
			payment_doc.update(erpnext_data)
			payment_doc.save()
		else:
			payment_doc = frappe.new_doc("Payment Entry")
			payment_doc.update(erpnext_data)
			payment_doc.custom_invoice_ninja_id = payment_data.get("id")
			payment_doc.insert()

		return payment_doc

	def _log_sync_error(self, doc, direction, error_message, invoice_ninja_data=None):
		"""Log synchronization errors for troubleshooting"""
		error_log = frappe.new_doc("Error Log")
		error_log.method = f"invoice_ninja_integration.sync_manager.{direction.lower().replace(' ', '_')}"
		error_log.error = error_message

		if doc:
			error_log.reference_doctype = doc.doctype
			error_log.reference_name = doc.name

		error_log.insert(ignore_permissions=True)

		# Send error notification if enabled
		if self.settings.send_error_notifications and self.settings.notification_email:
			self._send_error_notification(doc, direction, error_message, invoice_ninja_data)

	def _send_error_notification(self, doc, direction, error_message, invoice_ninja_data=None):
		"""Send error notification email"""
		subject = f"Invoice Ninja Integration Error - {direction}"

		message = f"""
        An error occurred during {direction} synchronization:

        Error: {error_message}

        Document: {doc.doctype if doc else "Unknown"} - {doc.name if doc else "N/A"}
        Direction: {direction}
        Time: {frappe.utils.now()}

        Please check the Error Log for more details.
        """

		frappe.sendmail(recipients=[self.settings.notification_email], subject=subject, message=message)

	def get_sync_configuration_summary(self):
		"""Get a summary of current sync configuration"""
		summary = {"enabled_syncs": [], "sync_directions": {}, "potential_issues": []}

		doc_types = ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]

		for doc_type in doc_types:
			if self.is_sync_enabled(doc_type):
				direction = self.get_sync_direction(doc_type)
				summary["enabled_syncs"].append(doc_type)
				summary["sync_directions"][doc_type] = direction

				# Check for potential bidirectional loop issues
				if direction == "Bidirectional":
					summary["potential_issues"].append(
						f"{doc_type}: Bidirectional sync may cause loops if not configured properly"
					)

		return summary

	def validate_sync_configuration(self):
		"""Validate sync configuration and return warnings/errors"""
		issues = []

		# Check if any sync is enabled but API not configured
		if any(
			self.is_sync_enabled(dt)
			for dt in ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]
		):
			if not self.settings.invoice_ninja_url or not self.settings.api_token:
				issues.append("ERROR: Sync enabled but Invoice Ninja URL or API token not configured")

		# Check webhook configuration for Invoice Ninja → ERPNext sync
		needs_webhooks = False
		for doc_type in ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]:
			if self.is_sync_enabled(doc_type) and self.should_sync_from_invoice_ninja(doc_type):
				needs_webhooks = True
				break

		if needs_webhooks and not self.settings.enable_webhooks:
			issues.append("WARNING: Invoice Ninja to ERPNext sync enabled but webhooks not enabled")

		# Check for all bidirectional syncs (potential loop risk)
		bidirectional_count = 0
		for doc_type in ["Customer", "Sales Invoice", "Quotation", "Item", "Payment Entry"]:
			if self.is_sync_enabled(doc_type) and self.get_sync_direction(doc_type) == "Bidirectional":
				bidirectional_count += 1

		if bidirectional_count > 2:
			issues.append("WARNING: Multiple bidirectional syncs enabled - risk of sync loops")

		return issues

	def sync_single_record_from_invoice_ninja(self, sync_type, record_id):
		"""Sync a single record from Invoice Ninja to ERPNext"""
		try:
			# Map sync types to Invoice Ninja API endpoints
			endpoint_map = {
				"Customer": "clients",
				"Invoice": "invoices",
				"Quote": "quotes",
				"Product": "products",
				"Payment": "payments",
			}

			endpoint = endpoint_map.get(sync_type)
			if not endpoint:
				raise Exception(f"Invalid sync type: {sync_type}")

			# Fetch record from Invoice Ninja
			data = self.client.get(f"{endpoint}/{record_id}")
			if not data:
				raise Exception(f"Record not found in Invoice Ninja: {record_id}")

			# Map to ERPNext doctype
			doctype_map = {
				"Customer": "Customer",
				"Invoice": "Sales Invoice",
				"Quote": "Quotation",
				"Product": "Item",
				"Payment": "Payment Entry",
			}

			doc_type = doctype_map[sync_type]
			result = self.sync_document_from_invoice_ninja(data, doc_type)

			return {"synced": 1, "record": result.name if result else None}

		except Exception as e:
			frappe.log_error(f"Single record sync failed: {e!s}", "Single Record Sync Error")
			raise e

	def sync_all_records_from_invoice_ninja(self, sync_type, limit=100):
		"""Sync all records of a type from Invoice Ninja to ERPNext"""
		try:
			# Map sync types to Invoice Ninja API endpoints
			endpoint_map = {
				"Customer": "clients",
				"Invoice": "invoices",
				"Quote": "quotes",
				"Product": "products",
				"Payment": "payments",
			}

			endpoint = endpoint_map.get(sync_type)
			if not endpoint:
				raise Exception(f"Invalid sync type: {sync_type}")

			# Fetch records from Invoice Ninja
			data = self.client.get(f"{endpoint}?per_page={limit}")
			if not data or not data.get("data"):
				return {"synced": 0, "message": "No records found"}

			# Map to ERPNext doctype
			doctype_map = {
				"Customer": "Customer",
				"Invoice": "Sales Invoice",
				"Quote": "Quotation",
				"Product": "Item",
				"Payment": "Payment Entry",
			}

			doc_type = doctype_map[sync_type]
			synced_count = 0

			for record in data["data"]:
				try:
					result = self.sync_document_from_invoice_ninja(record, doc_type)
					if result:
						synced_count += 1
				except Exception as e:
					frappe.log_error(
						f"Failed to sync {sync_type} {record.get('id')}: {e!s}", "Record Sync Error"
					)
					continue

			return {"synced": synced_count, "total": len(data["data"])}

		except Exception as e:
			frappe.log_error(f"Bulk sync failed: {e!s}", "Bulk Sync Error")
			raise e

	def sync_all_records_to_invoice_ninja(self, doc_type, limit=100):
		"""Sync all records of a type from ERPNext to Invoice Ninja"""
		try:
			# Get all records of this doctype that don't have Invoice Ninja ID yet
			filters = {"custom_invoice_ninja_id": ["is", "not set"]}

			# Add additional filters based on doctype
			if doc_type == "Sales Invoice":
				filters["docstatus"] = 1  # Only submitted invoices
			elif doc_type == "Quotation":
				filters["status"] = ["!=", "Cancelled"]
			elif doc_type == "Payment Entry":
				filters["docstatus"] = 1  # Only submitted payments

			records = frappe.get_list(doc_type, filters=filters, limit=limit, fields=["name"])

			if not records:
				return {"synced": 0, "message": "No records to sync"}

			synced_count = 0

			for record in records:
				try:
					doc = frappe.get_doc(doc_type, record.name)
					result = self.sync_document_to_invoice_ninja(doc)
					if result:
						synced_count += 1
				except Exception as e:
					frappe.log_error(f"Failed to sync {doc_type} {record.name}: {e!s}", "Record Sync Error")
					continue

			return {"synced": synced_count, "total": len(records)}

		except Exception as e:
			frappe.log_error(f"Bulk sync to Invoice Ninja failed: {e!s}", "Bulk Sync Error")
			raise e

	def _log_sync_success(self, doc, sync_direction, message):
		"""Log successful sync operation"""
		try:
			log_doc = frappe.get_doc(
				{
					"doctype": "Invoice Ninja Sync Logs",
					"sync_type": "Manual" if sync_direction else "Automatic",
					"entity_type": doc.doctype,
					"entity_name": doc.name,
					"status": "Success",
					"message": message,
					"sync_direction": sync_direction,
				}
			)
			log_doc.insert()
		except Exception as e:
			frappe.log_error(f"Failed to log sync success: {e!s}")

	def _log_sync_error(self, doc, sync_direction, error_message, invoice_ninja_data=None):
		"""Log sync error"""
		try:
			entity_name = doc.name if doc else invoice_ninja_data.get("id", "Unknown")
			entity_type = doc.doctype if doc else "Unknown"

			log_doc = frappe.get_doc(
				{
					"doctype": "Invoice Ninja Sync Logs",
					"sync_type": "Manual" if sync_direction else "Automatic",
					"entity_type": entity_type,
					"entity_name": entity_name,
					"status": "Failed",
					"message": error_message,
					"sync_direction": sync_direction,
				}
			)
			log_doc.insert()
		except Exception as e:
			frappe.log_error(f"Failed to log sync error: {e!s}")

	# ============================================================================
	# FETCH OPERATIONS - Generic methods for fetching entities from Invoice Ninja
	# ============================================================================

	def fetch_entities_for_mapped_companies(self, entity_type, page=1, per_page=100, filters=None):
		"""
		Generic method to fetch entities from Invoice Ninja for all mapped companies

		Args:
			entity_type: Type of entity (Customer, Sales Invoice, Quotation, Item, Payment Entry)
			page: Page number for pagination
			per_page: Number of records per page
			filters: Optional filters to apply

		Returns:
			dict: {
				"success": bool,
				"companies": [
					{
						"erpnext_company": str,
						"invoice_ninja_company_id": str,
						"invoice_ninja_company_name": str,
						"entities": [...],
						"entity_count": int,
						"is_default": bool
					}
				],
				"total_entities": int,
				"entity_type": str,
				"message": str
			}
		"""
		try:
			# Validate entity type
			if entity_type not in self.ENTITY_CONFIG:
				return {
					"success": False,
					"message": f"Invalid entity type: {entity_type}. Valid types: {list(self.ENTITY_CONFIG.keys())}",
					"companies": [],
					"total_entities": 0
				}

			# Check if integration is enabled
			if not self.settings.enabled:
				return {
					"success": False,
					"message": "Invoice Ninja integration is not enabled",
					"companies": [],
					"total_entities": 0
				}

			# Get entity configuration
			entity_config = self.ENTITY_CONFIG[entity_type]

			# Get all company mappings
			mappings = self.company_mapper.get_all_mappings()

			if not mappings:
				return {
					"success": False,
					"message": "No company mappings found. Please configure company mappings in Invoice Ninja Settings.",
					"companies": [],
					"total_entities": 0
				}

			# Fetch entities for each company
			companies_data = []
			total_entities = 0

			for mapping in mappings:
				company_id = mapping.get("invoice_ninja_company_id")
				company_name = mapping.get("invoice_ninja_company_name")
				erpnext_company = mapping.get("erpnext_company")

				# Get client for this company
				client, in_company_doc = self.get_client_for_mapping(mapping)

				# Fetch entities for this company using the client method
				method_name = entity_config["invoice_ninja_method"]
				client_method = getattr(client, method_name)

				# Build params
				params = {"page": int(page), "per_page": int(per_page)}
				if entity_config["include_params"]:
					params["include"] = entity_config["include_params"]

				# Call the appropriate client method
				if "include" in params:
					entities_response = client_method(page=params["page"], per_page=params["per_page"], include=params["include"])
				else:
					entities_response = client_method(page=params["page"], per_page=params["per_page"])

				entities = []
				entity_count = 0

				if entities_response and entities_response.get('data'):
					entities = entities_response['data']
					entity_count = len(entities)
					total_entities += entity_count

				companies_data.append({
					"erpnext_company": erpnext_company,
					"invoice_ninja_company_id": company_id,
					"invoice_ninja_company_name": company_name,
					"invoice_ninja_company_doc": in_company_doc,  # Doc reference for linking
					"entities": entities,
					"entity_count": entity_count,
					"is_default": mapping.get("is_default", False)
				})

			return {
				"success": True,
				"companies": companies_data,
				"total_entities": total_entities,
				"entity_type": entity_type,
				"message": f"Successfully fetched {total_entities} {entity_type} records from {len(mappings)} mapped companies"
			}

		except Exception as e:
			error_msg = f"Error fetching {entity_type} for mapped companies: {str(e)}"
			frappe.log_error(error_msg, "Entity Fetch Error")
			return {
				"success": False,
				"message": error_msg,
				"companies": [],
				"total_entities": 0
			}

	def fetch_entities_for_company(self, entity_type, erpnext_company=None,
									invoice_ninja_company_id=None, page=1, per_page=100, filters=None):
		"""
		Generic method to fetch entities from Invoice Ninja for a specific company

		Args:
			entity_type: Type of entity (Customer, Sales Invoice, Quotation, Item, Payment Entry)
			erpnext_company: ERPNext company name (optional)
			invoice_ninja_company_id: Invoice Ninja company ID (optional)
			page: Page number for pagination
			per_page: Number of records per page
			filters: Optional filters to apply

		Returns:
			dict: {
				"success": bool,
				"erpnext_company": str,
				"invoice_ninja_company_id": str,
				"invoice_ninja_company_name": str,
				"entities": [...],
				"entity_count": int,
				"entity_type": str,
				"message": str
			}
		"""
		try:
			# Validate entity type
			if entity_type not in self.ENTITY_CONFIG:
				return {
					"success": False,
					"message": f"Invalid entity type: {entity_type}. Valid types: {list(self.ENTITY_CONFIG.keys())}"
				}

			# Check if integration is enabled
			if not self.settings.enabled:
				return {
					"success": False,
					"message": "Invoice Ninja integration is not enabled"
				}

			# Get entity configuration
			entity_config = self.ENTITY_CONFIG[entity_type]

			# Get company mapping
			mapping = self.company_mapper.get_company_mapping(
				erpnext_company=erpnext_company,
				invoice_ninja_company_id=invoice_ninja_company_id
			)

			if not mapping:
				return {
					"success": False,
					"message": f"No company mapping found for {erpnext_company or invoice_ninja_company_id}"
				}

			# Get client for this company
			client, in_company_doc = self.get_client_for_mapping(mapping)

			# Fetch entities for this company
			method_name = entity_config["invoice_ninja_method"]
			client_method = getattr(client, method_name)

			# Build params
			params = {"page": int(page), "per_page": int(per_page)}
			if entity_config["include_params"]:
				params["include"] = entity_config["include_params"]

			# Call the appropriate client method
			if "include" in params:
				entities_response = client_method(page=params["page"], per_page=params["per_page"], include=params["include"])
			else:
				entities_response = client_method(page=params["page"], per_page=params["per_page"])

			entities = []
			entity_count = 0

			if entities_response and entities_response.get('data'):
				entities = entities_response['data']
				entity_count = len(entities)

			return {
				"success": True,
				"erpnext_company": mapping["erpnext_company"],
				"invoice_ninja_company_id": mapping["invoice_ninja_company_id"],
				"invoice_ninja_company_name": mapping["invoice_ninja_company_name"],
				"invoice_ninja_company_doc": in_company_doc,  # Doc reference for linking
				"entities": entities,
				"entity_count": entity_count,
				"entity_type": entity_type,
				"message": f"Successfully fetched {entity_count} {entity_type} records for {mapping['invoice_ninja_company_name']}"
			}

		except Exception as e:
			error_msg = f"Error fetching {entity_type} for company: {str(e)}"
			frappe.log_error(error_msg, "Entity Fetch Error")
			return {
				"success": False,
				"message": error_msg
			}

	def fetch_entity_by_id(self, entity_type, entity_id, erpnext_company=None,
							invoice_ninja_company_id=None):
		"""
		Fetch a single entity by Invoice Ninja ID

		Args:
			entity_type: Type of entity (Customer, Sales Invoice, Quotation, Item, Payment Entry)
			entity_id: Invoice Ninja entity ID
			erpnext_company: ERPNext company name (optional, for company context)
			invoice_ninja_company_id: Invoice Ninja company ID (optional, for company context)

		Returns:
			dict: {
				"success": bool,
				"entity": {...},
				"entity_type": str,
				"message": str
			}
		"""
		try:
			# Validate entity type
			if entity_type not in self.ENTITY_CONFIG:
				return {
					"success": False,
					"message": f"Invalid entity type: {entity_type}. Valid types: {list(self.ENTITY_CONFIG.keys())}"
				}

			# Check if integration is enabled
			if not self.settings.enabled:
				return {
					"success": False,
					"message": "Invoice Ninja integration is not enabled"
				}

			# Get entity configuration
			entity_config = self.ENTITY_CONFIG[entity_type]

			# If company is specified, set company context
			if erpnext_company or invoice_ninja_company_id:
				mapping = self.company_mapper.get_company_mapping(
					erpnext_company=erpnext_company,
					invoice_ninja_company_id=invoice_ninja_company_id
				)
				if mapping:
					self.client.set_company_id(mapping["invoice_ninja_company_id"])

			# Fetch entity using the endpoint
			endpoint = entity_config["invoice_ninja_endpoint"]
			entity_data = self.client.get(f"{endpoint}/{entity_id}")

			if not entity_data or not entity_data.get('data'):
				return {
					"success": False,
					"message": f"{entity_type} with ID {entity_id} not found"
				}

			return {
				"success": True,
				"entity": entity_data.get('data'),
				"entity_type": entity_type,
				"message": f"Successfully fetched {entity_type} with ID {entity_id}"
			}

		except Exception as e:
			error_msg = f"Error fetching {entity_type} by ID {entity_id}: {str(e)}"
			frappe.log_error(error_msg, "Entity Fetch Error")
			return {
				"success": False,
				"message": error_msg
			}

	# ============================================================================
	# CONVENIENCE METHODS - Entity-specific wrappers for common operations
	# ============================================================================

	# Customer methods
	def fetch_customers_for_mapped_companies(self, page=1, per_page=100):
		"""Fetch customers from all mapped companies"""
		return self.fetch_entities_for_mapped_companies("Customer", page, per_page)

	def fetch_customers_for_company(self, erpnext_company=None, invoice_ninja_company_id=None,
									page=1, per_page=100):
		"""Fetch customers for a specific company"""
		return self.fetch_entities_for_company("Customer", erpnext_company,
											  invoice_ninja_company_id, page, per_page)

	def fetch_customer_by_id(self, customer_id, erpnext_company=None, invoice_ninja_company_id=None):
		"""Fetch a single customer by ID"""
		return self.fetch_entity_by_id("Customer", customer_id, erpnext_company, invoice_ninja_company_id)

	# Invoice methods
	def fetch_invoices_for_mapped_companies(self, page=1, per_page=100):
		"""Fetch invoices from all mapped companies"""
		return self.fetch_entities_for_mapped_companies("Sales Invoice", page, per_page)

	def fetch_invoices_for_company(self, erpnext_company=None, invoice_ninja_company_id=None,
								   page=1, per_page=100):
		"""Fetch invoices for a specific company"""
		return self.fetch_entities_for_company("Sales Invoice", erpnext_company,
											  invoice_ninja_company_id, page, per_page)

	def fetch_invoice_by_id(self, invoice_id, erpnext_company=None, invoice_ninja_company_id=None):
		"""Fetch a single invoice by ID"""
		return self.fetch_entity_by_id("Sales Invoice", invoice_id, erpnext_company, invoice_ninja_company_id)

	# Quotation methods
	def fetch_quotations_for_mapped_companies(self, page=1, per_page=100):
		"""Fetch quotations from all mapped companies"""
		return self.fetch_entities_for_mapped_companies("Quotation", page, per_page)

	def fetch_quotations_for_company(self, erpnext_company=None, invoice_ninja_company_id=None,
									 page=1, per_page=100):
		"""Fetch quotations for a specific company"""
		return self.fetch_entities_for_company("Quotation", erpnext_company,
											  invoice_ninja_company_id, page, per_page)

	def fetch_quotation_by_id(self, quotation_id, erpnext_company=None, invoice_ninja_company_id=None):
		"""Fetch a single quotation by ID"""
		return self.fetch_entity_by_id("Quotation", quotation_id, erpnext_company, invoice_ninja_company_id)

	# Item methods
	def fetch_items_for_mapped_companies(self, page=1, per_page=100):
		"""Fetch items from all mapped companies"""
		return self.fetch_entities_for_mapped_companies("Item", page, per_page)

	def fetch_items_for_company(self, erpnext_company=None, invoice_ninja_company_id=None,
								page=1, per_page=100):
		"""Fetch items for a specific company"""
		return self.fetch_entities_for_company("Item", erpnext_company,
											  invoice_ninja_company_id, page, per_page)

	def fetch_item_by_id(self, item_id, erpnext_company=None, invoice_ninja_company_id=None):
		"""Fetch a single item by ID"""
		return self.fetch_entity_by_id("Item", item_id, erpnext_company, invoice_ninja_company_id)

	# Payment methods
	def fetch_payments_for_mapped_companies(self, page=1, per_page=100):
		"""Fetch payments from all mapped companies"""
		return self.fetch_entities_for_mapped_companies("Payment Entry", page, per_page)

	def fetch_payments_for_company(self, erpnext_company=None, invoice_ninja_company_id=None,
								   page=1, per_page=100):
		"""Fetch payments for a specific company"""
		return self.fetch_entities_for_company("Payment Entry", erpnext_company,
											  invoice_ninja_company_id, page, per_page)

	def fetch_payment_by_id(self, payment_id, erpnext_company=None, invoice_ninja_company_id=None):
		"""Fetch a single payment by ID"""
		return self.fetch_entity_by_id("Payment Entry", payment_id, erpnext_company, invoice_ninja_company_id)
