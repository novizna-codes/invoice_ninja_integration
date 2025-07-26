import frappe
from frappe.utils import flt, cint, get_datetime, nowdate
import re


class FieldMapper:
	"""Field mapping utility for Invoice Ninja to ERPNext conversion"""

	@staticmethod
	def map_customer_from_invoice_ninja(in_customer):
		"""Map Invoice Ninja customer to ERPNext customer"""
		try:
			# Get company mapping for this customer
			company_mapping = FieldMapper.get_company_mapping(
				invoice_ninja_company_id=in_customer.get('company_id')
			)
			
			if not company_mapping:
				frappe.log_error(
					f"No company mapping found for Invoice Ninja company ID: {in_customer.get('company_id')}", 
					"Customer Mapping Error"
				)
				return None, None
			
			# Basic customer mapping
			customer_data = {
				'doctype': 'Customer',
				'customer_name': in_customer.get('name') or in_customer.get('display_name') or f"Customer {in_customer.get('id')}",
				'customer_type': 'Company' if in_customer.get('is_company') else 'Individual',
				'customer_group': 'Commercial',  # Default group
				'territory': 'All Territories',  # Default territory
				'invoice_ninja_id': str(in_customer.get('id')),
				'invoice_ninja_sync_status': 'Synced',
				'company': company_mapping.erpnext_company  # Set the mapped company
			}

			# Contact information
			if in_customer.get('email'):
				customer_data['email_id'] = in_customer.get('email')

			if in_customer.get('phone'):
				customer_data['mobile_no'] = in_customer.get('phone')

			if in_customer.get('website'):
				customer_data['website'] = in_customer.get('website')

			# Tax information
			if in_customer.get('vat_number'):
				customer_data['tax_id'] = in_customer.get('vat_number')

			# Currency
			if in_customer.get('currency_id'):
				currency_code = FieldMapper.get_currency_code(in_customer.get('currency_id'))
				if currency_code:
					customer_data['default_currency'] = currency_code

			# Additional fields
			if in_customer.get('public_notes'):
				customer_data['customer_details'] = in_customer.get('public_notes')

			# Create address if available
			address_data = FieldMapper.map_customer_address(in_customer)

			return customer_data, address_data

		except Exception as e:
			frappe.log_error(f"Error mapping customer {in_customer.get('id')}: {str(e)}", "Customer Mapping Error")
			return None, None

	@staticmethod
	def map_customer_address(in_customer):
		"""Map customer address from Invoice Ninja"""
		if not any([in_customer.get('address1'), in_customer.get('city'), in_customer.get('state')]):
			return None

		address_data = {
			'doctype': 'Address',
			'address_title': in_customer.get('name') or 'Primary',
			'address_type': 'Billing',
			'address_line1': in_customer.get('address1') or '',
			'address_line2': in_customer.get('address2') or '',
			'city': in_customer.get('city') or '',
			'state': in_customer.get('state') or '',
			'pincode': in_customer.get('postal_code') or '',
			'country': FieldMapper.get_country_name(in_customer.get('country_id')),
			'is_primary_address': 1,
			'is_shipping_address': 1
		}

		return address_data

	@staticmethod
	def map_invoice_from_invoice_ninja(in_invoice):
		"""Map Invoice Ninja invoice to ERPNext sales invoice"""
		try:
			# Get company mapping for this invoice
			company_mapping = FieldMapper.get_company_mapping(
				invoice_ninja_company_id=in_invoice.get('company_id')
			)
			
			if not company_mapping:
				frappe.log_error(
					f"No company mapping found for Invoice Ninja company ID: {in_invoice.get('company_id')}", 
					"Invoice Mapping Error"
				)
				return None
			
			# Get customer reference
			customer_name = FieldMapper.get_customer_by_invoice_ninja_id(in_invoice.get('client_id'))
			if not customer_name:
				frappe.log_error(f"Customer not found for Invoice Ninja client_id: {in_invoice.get('client_id')}", "Invoice Mapping Error")
				return None

			# Basic invoice mapping
			invoice_data = {
				'doctype': 'Sales Invoice',
				'customer': customer_name,
				'company': company_mapping.erpnext_company,  # Set the mapped company
				'posting_date': FieldMapper.parse_date(in_invoice.get('date')) or nowdate(),
				'due_date': FieldMapper.parse_date(in_invoice.get('due_date')),
				'currency': FieldMapper.get_currency_code(in_invoice.get('currency_id')) or 'USD',
				'conversion_rate': flt(in_invoice.get('exchange_rate')) or 1.0,
				'selling_price_list': 'Standard Selling',
				'invoice_ninja_id': str(in_invoice.get('id')),
				'invoice_ninja_sync_status': 'Synced',
				'invoice_ninja_number': in_invoice.get('number'),
				'status': FieldMapper.map_invoice_status(in_invoice.get('status_id')),
				'items': []
			}

			# Invoice number
			if in_invoice.get('number'):
				invoice_data['naming_series'] = 'INV-'
				# ERPNext will auto-generate, we store IN number in custom field

			# Terms and conditions
			if in_invoice.get('terms'):
				invoice_data['tc_name'] = 'Standard Terms'
				invoice_data['terms'] = in_invoice.get('terms')

			# Notes
			if in_invoice.get('public_notes'):
				invoice_data['other_charges_calculation'] = in_invoice.get('public_notes')

			# Map line items
			line_items = in_invoice.get('line_items', [])
			for idx, item in enumerate(line_items, 1):
				item_data = FieldMapper.map_invoice_item(item, idx)
				if item_data:
					invoice_data['items'].append(item_data)

			# Map taxes if available
			taxes = FieldMapper.map_invoice_taxes(in_invoice)
			if taxes:
				invoice_data['taxes'] = taxes

			return invoice_data

		except Exception as e:
			frappe.log_error(f"Error mapping invoice {in_invoice.get('id')}: {str(e)}", "Invoice Mapping Error")
			return None

	@staticmethod
	def map_invoice_item(in_item, idx):
		"""Map Invoice Ninja line item to ERPNext item"""
		try:
			# Get or create item
			item_code = FieldMapper.get_or_create_item(in_item)

			item_data = {
				'doctype': 'Sales Invoice Item',
				'idx': idx,
				'item_code': item_code,
				'item_name': in_item.get('notes') or in_item.get('product_key') or 'Service Item',
				'description': in_item.get('notes') or '',
				'qty': flt(in_item.get('quantity')) or 1.0,
				'rate': flt(in_item.get('cost')) or 0.0,
				'amount': flt(in_item.get('quantity', 1)) * flt(in_item.get('cost', 0)),
				'uom': 'Nos'
			}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping line item: {str(e)}", "Item Mapping Error")
			return None

	@staticmethod
	def map_quote_from_invoice_ninja(in_quote):
		"""Map Invoice Ninja quote to ERPNext quotation"""
		try:
			# Get company mapping for this quote
			company_mapping = FieldMapper.get_company_mapping(
				invoice_ninja_company_id=in_quote.get('company_id')
			)
			
			if not company_mapping:
				frappe.log_error(
					f"No company mapping found for Invoice Ninja company ID: {in_quote.get('company_id')}", 
					"Quote Mapping Error"
				)
				return None
			
			# Get customer reference
			customer_name = FieldMapper.get_customer_by_invoice_ninja_id(in_quote.get('client_id'))
			if not customer_name:
				return None

			quote_data = {
				'doctype': 'Quotation',
				'party_name': customer_name,
				'quotation_to': 'Customer',
				'company': company_mapping.erpnext_company,  # Set the mapped company
				'transaction_date': FieldMapper.parse_date(in_quote.get('date')) or nowdate(),
				'valid_till': FieldMapper.parse_date(in_quote.get('due_date')),
				'currency': FieldMapper.get_currency_code(in_quote.get('currency_id')) or 'USD',
				'selling_price_list': 'Standard Selling',
				'invoice_ninja_id': str(in_quote.get('id')),
				'invoice_ninja_sync_status': 'Synced',
				'invoice_ninja_number': in_quote.get('number'),
				'status': FieldMapper.map_quote_status(in_quote.get('status_id')),
				'items': []
			}

			# Map line items
			line_items = in_quote.get('line_items', [])
			for idx, item in enumerate(line_items, 1):
				item_data = FieldMapper.map_quotation_item(item, idx)
				if item_data:
					quote_data['items'].append(item_data)

			return quote_data

		except Exception as e:
			frappe.log_error(f"Error mapping quote {in_quote.get('id')}: {str(e)}", "Quote Mapping Error")
			return None

	@staticmethod
	def map_quotation_item(in_item, idx):
		"""Map Invoice Ninja quote item to ERPNext quotation item"""
		try:
			item_code = FieldMapper.get_or_create_item(in_item)

			item_data = {
				'doctype': 'Quotation Item',
				'idx': idx,
				'item_code': item_code,
				'item_name': in_item.get('notes') or in_item.get('product_key') or 'Service Item',
				'description': in_item.get('notes') or '',
				'qty': flt(in_item.get('quantity')) or 1.0,
				'rate': flt(in_item.get('cost')) or 0.0,
				'amount': flt(in_item.get('quantity', 1)) * flt(in_item.get('cost', 0)),
				'uom': 'Nos'
			}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping quotation item: {str(e)}", "Quote Item Mapping Error")
			return None

	@staticmethod
	def map_product_from_invoice_ninja(in_product):
		"""Map Invoice Ninja product to ERPNext item"""
		try:
			item_data = {
				'doctype': 'Item',
				'item_code': in_product.get('product_key') or f"IN-PROD-{in_product.get('id')}",
				'item_name': in_product.get('notes') or in_product.get('product_key') or 'Unknown Item',
				'item_group': 'Products',
				'stock_uom': 'Nos',
				'is_stock_item': 0,
				'is_sales_item': 1,
				'is_purchase_item': 0,
				'include_item_in_manufacturing': 0,
				'description': in_product.get('notes') or '',
				'invoice_ninja_id': str(in_product.get('id')),
				'sync_status': 'Synced'
			}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping product {in_product.get('id')}: {str(e)}", "Product Mapping Error")
			return None

	@staticmethod
	def get_or_create_item(in_item):
		"""Get existing item or create item code for line item"""
		# Try to find existing item by product_key
		if in_item.get('product_key'):
			existing_item = frappe.db.get_value('Item',
				{'item_code': in_item.get('product_key')}, 'name')
			if existing_item:
				return existing_item

		# Create new item code
		item_code = in_item.get('product_key') or f"IN-ITEM-{frappe.generate_hash(length=8)}"

		# Ensure item code is unique
		if frappe.db.exists('Item', item_code):
			item_code = f"{item_code}-{frappe.generate_hash(length=4)}"

		return item_code

	@staticmethod
	def get_customer_by_invoice_ninja_id(client_id):
		"""Get ERPNext customer name by Invoice Ninja client ID"""
		if not client_id:
			return None

		customer = frappe.db.get_value('Customer',
			{'invoice_ninja_id': str(client_id)}, 'name')
		return customer

	@staticmethod
	def get_currency_code(currency_id):
		"""Map Invoice Ninja currency ID to currency code"""
		currency_map = {
			1: 'USD', 2: 'EUR', 3: 'GBP', 4: 'AUD', 5: 'CAD',
			6: 'JPY', 7: 'CHF', 8: 'SEK', 9: 'NOK', 10: 'DKK'
		}
		return currency_map.get(int(currency_id)) if currency_id else 'USD'

	@staticmethod
	def get_country_name(country_id):
		"""Map Invoice Ninja country ID to country name"""
		# This would need a proper mapping table
		# For now, return a default
		return 'United States' if not country_id else None

	@staticmethod
	def map_invoice_status(status_id):
		"""Map Invoice Ninja invoice status to ERPNext status"""
		status_map = {
			'1': 'Draft',
			'2': 'Submitted',
			'3': 'Paid',
			'4': 'Cancelled',
			'5': 'Overdue'
		}
		return status_map.get(str(status_id), 'Draft')

	@staticmethod
	def map_quote_status(status_id):
		"""Map Invoice Ninja quote status to ERPNext status"""
		status_map = {
			'1': 'Draft',
			'2': 'Open',
			'3': 'Ordered',
			'4': 'Expired',
			'5': 'Cancelled'
		}
		return status_map.get(str(status_id), 'Draft')

	@staticmethod
	def parse_date(date_string):
		"""Parse date string to ERPNext format"""
		if not date_string:
			return None
		try:
			if isinstance(date_string, str):
				# Handle various date formats
				date_string = date_string.split(' ')[0]  # Remove time part
				return get_datetime(date_string).date()
			return date_string
		except:
			return None

	@staticmethod
	def map_invoice_taxes(in_invoice):
		"""Map Invoice Ninja taxes to ERPNext taxes"""
		taxes = []

		# This would need proper tax mapping based on your setup
		tax_amount = flt(in_invoice.get('tax_amount', 0))
		if tax_amount > 0:
			tax_data = {
				'doctype': 'Sales Taxes and Charges',
				'charge_type': 'On Net Total',
				'account_head': 'VAT - Company',  # Adjust based on your chart of accounts
				'rate': 0,  # Calculate rate if needed
				'tax_amount': tax_amount,
				'description': 'Tax from Invoice Ninja'
			}
			taxes.append(tax_data)

		return taxes

	@staticmethod
	def map_customer_to_invoice_ninja(customer_doc):
		"""Map ERPNext customer to Invoice Ninja format"""
		# Validate and get company mapping
		company_mapping = FieldMapper.validate_company_mapping(customer_doc)
		
		customer_data = {
			'name': customer_doc.customer_name,
			'display_name': customer_doc.customer_name,
			'email': customer_doc.email_id or '',
			'phone': customer_doc.mobile_no or '',
			'website': customer_doc.website or '',
			'vat_number': customer_doc.tax_id or '',
			'public_notes': customer_doc.customer_details or '',
			'is_company': 1 if customer_doc.customer_type == 'Company' else 0,
			'company_id': company_mapping.invoice_ninja_company_id  # Add company mapping
		}

		# Add address information
		address = frappe.db.get_value("Address",
			{"link_doctype": "Customer", "link_name": customer_doc.name, "is_primary_address": 1},
			["address_line1", "address_line2", "city", "state", "pincode", "country"], as_dict=True)

		if address:
			customer_data.update({
				'address1': address.address_line1 or '',
				'address2': address.address_line2 or '',
				'city': address.city or '',
				'state': address.state or '',
				'postal_code': address.pincode or '',
				'country_id': FieldMapper.get_country_id(address.country)
			})

		return customer_data

	@staticmethod
	def map_invoice_to_invoice_ninja(invoice_doc):
		"""Map ERPNext sales invoice to Invoice Ninja format"""
		# Validate and get company mapping
		company_mapping = FieldMapper.validate_company_mapping(invoice_doc)
		
		# Get customer's Invoice Ninja ID
		client_id = frappe.db.get_value("Customer", invoice_doc.customer, "invoice_ninja_id")
		if not client_id:
			frappe.throw(f"Customer {invoice_doc.customer} not synced to Invoice Ninja")

		invoice_data = {
			'client_id': client_id,
			'company_id': company_mapping.invoice_ninja_company_id,  # Add company mapping
			'date': str(invoice_doc.posting_date),
			'due_date': str(invoice_doc.due_date) if invoice_doc.due_date else None,
			'number': invoice_doc.name,
			'public_notes': invoice_doc.remarks or '',
			'terms': invoice_doc.terms or '',
			'currency_id': FieldMapper.get_currency_id(invoice_doc.currency),
			'exchange_rate': invoice_doc.conversion_rate or 1.0,
			'line_items': []
		}

		# Add line items
		for item in invoice_doc.items:
			line_item = {
				'product_key': item.item_code,
				'notes': item.description or item.item_name,
				'qty': item.qty,
				'cost': item.rate,
				'discount': item.discount_percentage or 0
			}
			invoice_data['line_items'].append(line_item)

		return invoice_data

	@staticmethod
	def map_quotation_to_invoice_ninja(quotation_doc):
		"""Map ERPNext quotation to Invoice Ninja format"""
		# Validate and get company mapping
		company_mapping = FieldMapper.validate_company_mapping(quotation_doc)
		
		# Get customer's Invoice Ninja ID
		client_id = frappe.db.get_value("Customer", quotation_doc.party_name, "invoice_ninja_id")
		if not client_id:
			frappe.throw(f"Customer {quotation_doc.party_name} not synced to Invoice Ninja")

		quote_data = {
			'client_id': client_id,
			'company_id': company_mapping.invoice_ninja_company_id,  # Add company mapping
			'date': str(quotation_doc.transaction_date),
			'valid_until': str(quotation_doc.valid_till) if quotation_doc.valid_till else None,
			'number': quotation_doc.name,
			'public_notes': quotation_doc.terms or '',
			'currency_id': FieldMapper.get_currency_id(quotation_doc.currency),
			'exchange_rate': quotation_doc.conversion_rate or 1.0,
			'line_items': []
		}

		# Add line items
		for item in quotation_doc.items:
			line_item = {
				'product_key': item.item_code,
				'notes': item.description or item.item_name,
				'qty': item.qty,
				'cost': item.rate,
				'discount': item.discount_percentage or 0
			}
			quote_data['line_items'].append(line_item)

		return quote_data

	@staticmethod
	def map_item_to_invoice_ninja(item_doc):
		"""Map ERPNext item to Invoice Ninja product format"""
		product_data = {
			'product_key': item_doc.item_code,
			'notes': item_doc.description or item_doc.item_name,
			'cost': item_doc.standard_rate or 0,
			'price': item_doc.standard_rate or 0,
			'tax_name': '',  # Map tax template if needed
			'tax_rate': 0    # Map tax rate if needed
		}

		return product_data

	@staticmethod
	def map_quotation_from_invoice_ninja(in_quote):
		"""Map Invoice Ninja quote to ERPNext quotation"""
		try:
			# Get customer reference
			customer_name = FieldMapper.get_customer_by_invoice_ninja_id(in_quote.get('client_id'))
			if not customer_name:
				frappe.log_error(f"Customer not found for Invoice Ninja client_id: {in_quote.get('client_id')}", "Quote Mapping Error")
				return None

			quotation_data = {
				'doctype': 'Quotation',
				'quotation_to': 'Customer',
				'party_name': customer_name,
				'transaction_date': FieldMapper.parse_date(in_quote.get('date')) or nowdate(),
				'valid_till': FieldMapper.parse_date(in_quote.get('valid_until')),
				'currency': FieldMapper.get_currency_code(in_quote.get('currency_id')) or 'USD',
				'conversion_rate': flt(in_quote.get('exchange_rate')) or 1.0,
				'selling_price_list': 'Standard Selling',
				'invoice_ninja_id': str(in_quote.get('id')),
				'sync_status': 'Synced',
				'terms': in_quote.get('public_notes') or '',
				'items': []
			}

			# Add line items
			for line_item in in_quote.get('line_items', []):
				item_data = {
					'doctype': 'Quotation Item',
					'item_code': FieldMapper.get_item_code(line_item.get('product_key')),
					'item_name': line_item.get('notes') or line_item.get('product_key'),
					'description': line_item.get('notes') or line_item.get('product_key'),
					'qty': flt(line_item.get('qty', 1)),
					'rate': flt(line_item.get('cost', 0)),
					'discount_percentage': flt(line_item.get('discount', 0))
				}
				quotation_data['items'].append(item_data)

			return quotation_data

		except Exception as e:
			frappe.log_error(f"Error mapping quotation {in_quote.get('id')}: {str(e)}", "Quotation Mapping Error")
			return None

	@staticmethod
	def map_item_from_invoice_ninja(in_product):
		"""Map Invoice Ninja product to ERPNext item"""
		try:
			item_data = {
				'doctype': 'Item',
				'item_code': in_product.get('product_key') or f"IN-{in_product.get('id')}",
				'item_name': in_product.get('notes') or in_product.get('product_key'),
				'description': in_product.get('notes') or in_product.get('product_key'),
				'item_group': 'Products',  # Default item group
				'stock_uom': 'Nos',  # Default UOM
				'is_stock_item': 0,  # Assume service item by default
				'is_sales_item': 1,
				'standard_rate': flt(in_product.get('price', 0)),
				'invoice_ninja_id': str(in_product.get('id')),
				'sync_status': 'Synced'
			}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping item {in_product.get('id')}: {str(e)}", "Item Mapping Error")
			return None

	@staticmethod
	def map_payment_from_invoice_ninja(in_payment):
		"""Map Invoice Ninja payment to ERPNext payment entry"""
		try:
			# Get related invoice
			invoice_id = in_payment.get('invoice_id')
			if not invoice_id:
				return None

			invoice_name = frappe.db.get_value("Sales Invoice", {"invoice_ninja_id": str(invoice_id)}, "name")
			if not invoice_name:
				frappe.log_error(f"Invoice not found for Invoice Ninja payment: {in_payment.get('id')}", "Payment Mapping Error")
				return None

			invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)

			payment_data = {
				'doctype': 'Payment Entry',
				'payment_type': 'Receive',
				'party_type': 'Customer',
				'party': invoice_doc.customer,
				'posting_date': FieldMapper.parse_date(in_payment.get('date')) or nowdate(),
				'paid_amount': flt(in_payment.get('amount', 0)),
				'received_amount': flt(in_payment.get('amount', 0)),
				'source_exchange_rate': 1.0,
				'target_exchange_rate': 1.0,
				'reference_no': in_payment.get('transaction_reference') or '',
				'reference_date': FieldMapper.parse_date(in_payment.get('date')),
				'invoice_ninja_id': str(in_payment.get('id')),
				'sync_status': 'Synced',
				'references': [{
					'doctype': 'Payment Entry Reference',
					'reference_doctype': 'Sales Invoice',
					'reference_name': invoice_name,
					'allocated_amount': flt(in_payment.get('amount', 0))
				}]
			}

			# Set default accounts (adjust based on your setup)
			payment_data['paid_from'] = frappe.db.get_value("Account", {"account_type": "Receivable", "is_group": 0}, "name")
			payment_data['paid_to'] = frappe.db.get_value("Account", {"account_type": "Cash", "is_group": 0}, "name")

			return payment_data

		except Exception as e:
			frappe.log_error(f"Error mapping payment {in_payment.get('id')}: {str(e)}", "Payment Mapping Error")
			return None

	@staticmethod
	def get_currency_id(currency_code):
		"""Get Invoice Ninja currency ID from code"""
		# This is a simplified mapping - you'd need the actual currency IDs from Invoice Ninja
		currency_map = {
			'USD': 1,
			'EUR': 3,
			'GBP': 2,
			'AUD': 12,
			'CAD': 4
		}
		return currency_map.get(currency_code, 1)  # Default to USD

	@staticmethod
	def get_country_id(country_name):
		"""Get Invoice Ninja country ID from name"""
		# This is a simplified mapping - you'd need the actual country IDs from Invoice Ninja
		if not country_name:
			return 840  # Default to US

		country_map = {
			'United States': 840,
			'United Kingdom': 826,
			'Canada': 124,
			'Australia': 36,
			'Germany': 276,
			'France': 250
		}
		return country_map.get(country_name, 840)
	
	@staticmethod
	def get_company_mapping(erpnext_company=None, invoice_ninja_company_id=None):
		"""Get company mapping between ERPNext and Invoice Ninja"""
		settings = frappe.get_single("Invoice Ninja Settings")
		
		if not settings.company_mappings:
			return None
		
		for mapping in settings.company_mappings:
			if not mapping.enabled:
				continue
				
			if erpnext_company and mapping.erpnext_company == erpnext_company:
				return mapping
			elif invoice_ninja_company_id and str(mapping.invoice_ninja_company_id) == str(invoice_ninja_company_id):
				return mapping
		
		# Return default mapping if no specific match found
		for mapping in settings.company_mappings:
			if mapping.enabled and mapping.is_default:
				return mapping
		
		return None
	
	@staticmethod
	def get_erpnext_company(invoice_ninja_company_id):
		"""Get ERPNext company name from Invoice Ninja company ID"""
		mapping = FieldMapper.get_company_mapping(invoice_ninja_company_id=invoice_ninja_company_id)
		return mapping.erpnext_company if mapping else None
	
	@staticmethod
	def get_invoice_ninja_company_id(erpnext_company):
		"""Get Invoice Ninja company ID from ERPNext company name"""
		mapping = FieldMapper.get_company_mapping(erpnext_company=erpnext_company)
		return mapping.invoice_ninja_company_id if mapping else None
	
	@staticmethod
	def validate_company_mapping(doc):
		"""Validate that document has proper company mapping"""
		company = None
		
		# Get company from document
		if hasattr(doc, 'company'):
			company = doc.company
		elif hasattr(doc, 'customer') and doc.customer:
			# Get company from customer's default company
			customer_doc = frappe.get_doc("Customer", doc.customer)
			if hasattr(customer_doc, 'default_company'):
				company = customer_doc.default_company
		
		if not company:
			# Use default company
			company = frappe.db.get_single_value("Global Defaults", "default_company")
		
		if not company:
			frappe.throw("Cannot determine company for document. Please ensure company mappings are configured.")
		
		# Check if company mapping exists
		mapping = FieldMapper.get_company_mapping(erpnext_company=company)
		if not mapping:
			frappe.throw(f"No company mapping found for ERPNext company '{company}'. Please configure company mappings in Invoice Ninja Settings.")
		
		return mapping
