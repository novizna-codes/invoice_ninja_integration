import requests
import frappe
from frappe.utils import get_datetime, now_datetime
import json


class InvoiceNinjaClient:
	"""Invoice Ninja API Client for ERPNext Integration with Per-Company Credentials"""

	def __init__(self, invoice_ninja_company=None, url=None, token=None):
		"""
		Initialize Invoice Ninja Client with credentials

		Args:
			invoice_ninja_company: Name/ID of Invoice Ninja Company doc
			url: Invoice Ninja URL (if not using invoice_ninja_company)
			token: API Token (if not using invoice_ninja_company)
		"""
		if invoice_ninja_company:
			# Get credentials from Invoice Ninja Company doc
			company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)

			if not company_doc.enabled:
				frappe.throw(f"Invoice Ninja Company {invoice_ninja_company} is disabled")

			# Validate token exists
			self.token = company_doc.get_password("api_token")
			if not self.token:
				frappe.throw(
					f"No API token configured for Invoice Ninja Company '{company_doc.company_name}'. "
					"Please set the token before syncing.",
					title="Token Required"
				)

			self.base_url = company_doc.invoice_ninja_url.rstrip('/')
			self.company_ref = invoice_ninja_company  # Store doc reference
			self.company_id = company_doc.company_id  # Store Invoice Ninja company ID
		elif url and token:
			# Direct credentials provided (backward compatibility)
			self.base_url = url.rstrip('/')
			self.token = token
			self.company_ref = None
			self.company_id = None
		else:
			# Fallback to global settings (for migration period)
			settings = frappe.get_single("Invoice Ninja Settings")
			if not hasattr(settings, 'invoice_ninja_url') or not settings.invoice_ninja_url:
				frappe.throw("No Invoice Ninja credentials configured. Please set up an Invoice Ninja Company.")

			self.base_url = settings.invoice_ninja_url.rstrip('/')
			self.token = settings.get_password("api_token")
			self.company_ref = None
			self.company_id = None
			frappe.log_error(
				"Using deprecated global credentials. Please migrate to per-company credentials.",
				"Invoice Ninja Deprecation Warning"
			)

		self.headers = {
			'X-API-TOKEN': self.token,
			'Content-Type': 'application/json',
			'Accept': 'application/json'
		}

		# Set company context if company_id is available
		if self.company_id:
			self.headers['X-API-COMPANY'] = str(self.company_id)

	@staticmethod
	def get_client_for_company(erpnext_company=None, invoice_ninja_company_id=None):
		"""
		Get client instance for specific company mapping

		Args:
			erpnext_company: ERPNext company name
			invoice_ninja_company_id: Invoice Ninja company ID

		Returns:
			InvoiceNinjaClient instance configured for the specified company
		"""
		from .company_mapper import CompanyMapper

		mapper = CompanyMapper()
		mapping = mapper.get_company_mapping(
			erpnext_company=erpnext_company,
			invoice_ninja_company_id=invoice_ninja_company_id
		)

		if not mapping:
			frappe.throw(f"No mapping found for {erpnext_company or invoice_ninja_company_id}")

		# Get Invoice Ninja Company doc reference
		in_company_doc = frappe.get_value("Invoice Ninja Company",
			{"company_id": mapping["invoice_ninja_company_id"]}, "name")

		if not in_company_doc:
			frappe.throw(f"Invoice Ninja Company not found for company_id {mapping['invoice_ninja_company_id']}")

		return InvoiceNinjaClient(invoice_ninja_company=in_company_doc)

	def set_company_id(self, company_id):
		"""
		Set company context for API requests (deprecated - use invoice_ninja_company in __init__)
		This is kept for backward compatibility during migration
		"""
		self.company_id = company_id
		if company_id:
			self.headers['X-API-COMPANY'] = str(company_id)
		elif 'X-API-COMPANY' in self.headers:
			del self.headers['X-API-COMPANY']

	def _make_request(self, method, endpoint, data=None, params=None):
		"""Make API request to Invoice Ninja"""
		url = f"{self.base_url}/api/v1/{endpoint}"

		try:
			response = requests.request(
				method=method,
				url=url,
				headers=self.headers,
				json=data,
				params=params,
				timeout=30
			)

			if response.status_code in [200, 201]:
				return response.json()
			else:
				error_msg = f"API Error {response.status_code}: {response.text}"
				frappe.log_error(error_msg, "Invoice Ninja API Error")
				# Return error info for better debugging
				return {
					"error": True,
					"status_code": response.status_code,
					"message": error_msg,
					"response_text": response.text[:500]  # Limit length
				}

		except Exception as e:
			error_msg = f"Request failed: {str(e)}"
			frappe.log_error(error_msg, "Invoice Ninja API Error")
			return {
				"error": True,
				"message": error_msg,
				"exception": str(e)
			}

	def get(self, endpoint, params=None):
		"""Generic GET request"""
		return self._make_request('GET', endpoint, params=params)

	def post(self, endpoint, data=None):
		"""Generic POST request"""
		return self._make_request('POST', endpoint, data=data)

	def put(self, endpoint, data=None):
		"""Generic PUT request"""
		return self._make_request('PUT', endpoint, data=data)

	def delete(self, endpoint):
		"""Generic DELETE request"""
		return self._make_request('DELETE', endpoint)

	def test_connection(self):
		"""Test API connection"""
		try:
			result = self._make_request('GET', 'ping')
			return result is not None
		except Exception as e:
			frappe.log_error(f"Connection test failed: {str(e)}", "Invoice Ninja Connection Test")
			return False

	# Company methods
	def get_companies(self):
		"""Get companies from Invoice Ninja"""
		return self.get('companies')

	def get_company(self, company_id):
		"""Get single company"""
		return self.get(f'companies/{company_id}')

	# Client methods	# Customer methods
	def get_customers(self, page=1, per_page=100, include=None):
		"""Get customers from Invoice Ninja"""
		params = {
			'page': page,
			'per_page': per_page,
		}

		if include:
			params['include'] = include

		return self.get('clients', params=params)

	def get_customer(self, customer_id):
		"""Get single customer"""
		return self.get(f'clients/{customer_id}')

	def create_customer(self, customer_data):
		"""Create customer in Invoice Ninja"""
		return self.post('clients', data=customer_data)

	def update_customer(self, customer_id, customer_data):
		"""Update customer in Invoice Ninja"""
		return self.put(f'clients/{customer_id}', data=customer_data)

	# Invoice methods
	def get_invoices(self, page=1, per_page=100, include=None):
		"""Get invoices from Invoice Ninja - include task data by default"""
		params = {
			'page': page,
			'per_page': per_page,
			'include': include or 'client,line_items.task'  # Include nested task data by default
		}
		return self.get('invoices', params=params)

	def get_invoice(self, invoice_id, include=None):
		"""Get single invoice"""
		params = {'include': include} if include else None
		return self.get(f'invoices/{invoice_id}', params=params)

	def create_invoice(self, invoice_data):
		"""Create invoice in Invoice Ninja"""
		return self.post('invoices', data=invoice_data)

	def update_invoice(self, invoice_id, invoice_data):
		"""Update invoice in Invoice Ninja"""
		return self.put(f'invoices/{invoice_id}', data=invoice_data)

	# Quote methods
	def get_quotes(self, page=1, per_page=100, include=None):
		"""Get quotes from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		if include:
			params['include'] = include
		return self.get('quotes', params=params)

	def get_quote(self, quote_id, include=None):
		"""Get single quote"""
		params = {'include': include} if include else None
		return self.get(f'quotes/{quote_id}', params=params)

	def create_quote(self, quote_data):
		"""Create quote in Invoice Ninja"""
		return self.post('quotes', data=quote_data)

	def update_quote(self, quote_id, quote_data):
		"""Update quote in Invoice Ninja"""
		return self.put(f'quotes/{quote_id}', data=quote_data)

	# Product methods
	def get_products(self, page=1, per_page=100):
		"""Get products from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		return self.get('products', params=params)

	def get_product(self, product_id):
		"""Get single product"""
		return self.get(f'products/{product_id}')

	def create_product(self, product_data):
		"""Create product in Invoice Ninja"""
		return self.post('products', data=product_data)

	def update_product(self, product_id, product_data):
		"""Update product in Invoice Ninja"""
		return self.put(f'products/{product_id}', data=product_data)

	# Payment methods
	def get_payments(self, page=1, per_page=100, include=None):
		"""Get payments from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		if include:
			params['include'] = include
		return self.get('payments', params=params)

	def get_payment(self, payment_id, include=None):
		"""Get single payment"""
		params = {'include': include} if include else None
		return self.get(f'payments/{payment_id}', params=params)

	def create_payment(self, payment_data):
		"""Create payment in Invoice Ninja"""
		return self.post('payments', data=payment_data)

	# Tax Rate methods
	def get_tax_rates(self, page=1, per_page=100):
		"""Get tax rates from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		return self.get('tax_rates', params=params)

	# Task methods
	def get_tasks(self, page=1, per_page=100, include=None):
		"""Get tasks from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		if include:
			params['include'] = include
		return self.get('tasks', params=params)

	def get_task(self, task_id):
		"""Get single task"""
		return self.get(f'tasks/{task_id}')

	def create_task(self, task_data):
		"""Create task in Invoice Ninja"""
		return self.post('tasks', data=task_data)

	def update_task(self, task_id, task_data):
		"""Update task in Invoice Ninja"""
		return self.put(f'tasks/{task_id}', data=task_data)

	# File methods
	def download_invoice_pdf(self, invoice_id):
		"""Download invoice PDF"""
		url = f"{self.base_url}/api/v1/invoices/{invoice_id}/download"
		try:
			response = requests.get(url, headers=self.headers, timeout=30)
			if response.status_code == 200:
				return response.content
		except Exception as e:
			frappe.log_error(f"Failed to download PDF: {str(e)}", "Invoice Ninja PDF Download")
		return None

	# Webhook methods
	def get_webhooks(self):
		"""Get all webhooks for this company"""
		return self.get('webhooks')

	def get_webhook(self, webhook_id):
		"""Get single webhook"""
		return self.get(f'webhooks/{webhook_id}')

	def create_webhook(self, webhook_data):
		"""
		Create webhook in Invoice Ninja

		Args:
			webhook_data: Dictionary with webhook configuration
				{
					"target_url": "https://your-site.com/api/method/webhook_handler",
					"event_id": "1",  # Event type ID (create_client, create_invoice, etc.)
					"format": "JSON"
				}

		Returns:
			Response from Invoice Ninja API
		"""
		return self.post('webhooks', data=webhook_data)

	def update_webhook(self, webhook_id, webhook_data):
		"""Update webhook in Invoice Ninja"""
		return self.put(f'webhooks/{webhook_id}', data=webhook_data)

	def delete_webhook(self, webhook_id):
		"""Delete webhook in Invoice Ninja"""
		return self.delete(f'webhooks/{webhook_id}')

	def register_webhooks_for_entity(self, entity_type, target_url):
		"""
		Register webhooks for all events of a specific entity type

		Args:
			entity_type: Type of entity (client, invoice, quote, product, payment)
			target_url: Full URL to receive webhook notifications

		Returns:
			List of created webhook IDs
		"""
		# Invoice Ninja event IDs mapping
		event_map = {
			'client': {
				'create': '1',
				'update': '2',
				'delete': '3',
			},
			'invoice': {
				'create': '4',
				'update': '5',
				'delete': '6',
			},
			'quote': {
				'create': '7',
				'update': '8',
				'delete': '9',
			},
			'payment': {
				'create': '10',
				'update': '11',
				'delete': '12',
			},
			'product': {
				'create': '16',
				'update': '17',
				'delete': '18',
			},
		}

		if entity_type not in event_map:
			frappe.throw(f"Unsupported entity type: {entity_type}")

		created_webhooks = []
		events = event_map[entity_type]

		for event_name, event_id in events.items():
			webhook_data = {
				"target_url": target_url,
				"event_id": event_id,
				"format": "JSON"
			}

			try:
				result = self.create_webhook(webhook_data)
				if result and not result.get('error'):
					webhook_id = result.get('data', {}).get('id')
					if webhook_id:
						created_webhooks.append({
							'id': webhook_id,
							'entity': entity_type,
							'event': event_name,
							'event_id': event_id
						})
						frappe.logger().info(
							f"Created webhook for {entity_type}.{event_name} (ID: {webhook_id})"
						)
				else:
					frappe.log_error(
						f"Failed to create webhook for {entity_type}.{event_name}: {result}",
						"Webhook Registration Error"
					)
			except Exception as e:
				frappe.log_error(
					f"Exception creating webhook for {entity_type}.{event_name}: {str(e)}",
					"Webhook Registration Exception"
				)

		return created_webhooks

	def unregister_all_webhooks(self):
		"""
		Delete all webhooks for this company

		Returns:
			Number of webhooks deleted
		"""
		try:
			webhooks_response = self.get_webhooks()
			if not webhooks_response or webhooks_response.get('error'):
				return 0

			webhooks = webhooks_response.get('data', [])
			deleted_count = 0

			for webhook in webhooks:
				webhook_id = webhook.get('id')
				if webhook_id:
					result = self.delete_webhook(webhook_id)
					if result and not result.get('error'):
						deleted_count += 1
						frappe.logger().info(f"Deleted webhook ID: {webhook_id}")

			return deleted_count

		except Exception as e:
			frappe.log_error(
				f"Error unregistering webhooks: {str(e)}",
				"Webhook Unregistration Error"
			)
			return 0
