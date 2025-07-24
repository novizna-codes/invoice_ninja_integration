import requests
import frappe
from frappe.utils import get_datetime, now_datetime
import json


class InvoiceNinjaClient:
	"""Invoice Ninja API Client for ERPNext Integration"""

	def __init__(self, url, token):
		self.base_url = url.rstrip('/')
		self.token = token
		self.headers = {
			'X-API-TOKEN': token,
			'Content-Type': 'application/json',
			'Accept': 'application/json'
		}

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
				return None

		except Exception as e:
			error_msg = f"Request failed: {str(e)}"
			frappe.log_error(error_msg, "Invoice Ninja API Error")
			return None

	def test_connection(self):
		"""Test API connection"""
		response = self._make_request('GET', 'ping')
		return response is not None

	# Customer methods
	def get_customers(self, page=1, per_page=100):
		"""Get customers from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		return self._make_request('GET', 'clients', params=params)

	def get_customer(self, customer_id):
		"""Get single customer"""
		return self._make_request('GET', f'clients/{customer_id}')

	def create_customer(self, customer_data):
		"""Create customer in Invoice Ninja"""
		return self._make_request('POST', 'clients', data=customer_data)

	def update_customer(self, customer_id, customer_data):
		"""Update customer in Invoice Ninja"""
		return self._make_request('PUT', f'clients/{customer_id}', data=customer_data)

	# Invoice methods
	def get_invoices(self, page=1, per_page=100, include=None):
		"""Get invoices from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		if include:
			params['include'] = include
		return self._make_request('GET', 'invoices', params=params)

	def get_invoice(self, invoice_id, include=None):
		"""Get single invoice"""
		params = {'include': include} if include else None
		return self._make_request('GET', f'invoices/{invoice_id}', params=params)

	def create_invoice(self, invoice_data):
		"""Create invoice in Invoice Ninja"""
		return self._make_request('POST', 'invoices', data=invoice_data)

	def update_invoice(self, invoice_id, invoice_data):
		"""Update invoice in Invoice Ninja"""
		return self._make_request('PUT', f'invoices/{invoice_id}', data=invoice_data)

	# Quote methods
	def get_quotes(self, page=1, per_page=100, include=None):
		"""Get quotes from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		if include:
			params['include'] = include
		return self._make_request('GET', 'quotes', params=params)

	def get_quote(self, quote_id, include=None):
		"""Get single quote"""
		params = {'include': include} if include else None
		return self._make_request('GET', f'quotes/{quote_id}', params=params)

	def create_quote(self, quote_data):
		"""Create quote in Invoice Ninja"""
		return self._make_request('POST', 'quotes', data=quote_data)

	def update_quote(self, quote_id, quote_data):
		"""Update quote in Invoice Ninja"""
		return self._make_request('PUT', f'quotes/{quote_id}', data=quote_data)

	# Product methods
	def get_products(self, page=1, per_page=100):
		"""Get products from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		return self._make_request('GET', 'products', params=params)

	def get_product(self, product_id):
		"""Get single product"""
		return self._make_request('GET', f'products/{product_id}')

	def create_product(self, product_data):
		"""Create product in Invoice Ninja"""
		return self._make_request('POST', 'products', data=product_data)

	def update_product(self, product_id, product_data):
		"""Update product in Invoice Ninja"""
		return self._make_request('PUT', f'products/{product_id}', data=product_data)

	# Payment methods
	def get_payments(self, page=1, per_page=100, include=None):
		"""Get payments from Invoice Ninja"""
		params = {'page': page, 'per_page': per_page}
		if include:
			params['include'] = include
		return self._make_request('GET', 'payments', params=params)

	def get_payment(self, payment_id, include=None):
		"""Get single payment"""
		params = {'include': include} if include else None
		return self._make_request('GET', f'payments/{payment_id}', params=params)

	def create_payment(self, payment_data):
		"""Create payment in Invoice Ninja"""
		return self._make_request('POST', 'payments', data=payment_data)

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
