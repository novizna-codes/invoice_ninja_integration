import re

import frappe
from frappe.utils import cint, flt, get_datetime, now_datetime, nowdate
import json
from erpnext.setup.utils import get_exchange_rate


class FieldMapper:
	"""Field mapping utility for Invoice Ninja to ERPNext conversion"""

	@staticmethod
	def get_conversion_rate_for_transaction(invoice_currency, company_currency, posting_date, in_exchange_rate=None):
		"""
		Get conversion rate with automatic API fetching if not found in Currency Exchange table

		Args:
			invoice_currency: Currency from Invoice Ninja invoice
			company_currency: ERPNext company's currency
			posting_date: Transaction posting date
			in_exchange_rate: Exchange rate from Invoice Ninja (fallback)

		Returns:
			float: Conversion rate
		"""
		# If currencies are the same, no conversion needed
		if invoice_currency == company_currency:
			return 1.0

		try:
			# Use ERPNext's get_exchange_rate - it automatically:
			# 1. Checks Currency Exchange table for existing rate on this date
			# 2. Falls back to API (frankfurter.dev, etc.) if not found
			# 3. Creates Currency Exchange record automatically
			# 4. Respects Currency Exchange Settings configuration
			conversion_rate = get_exchange_rate(
				from_currency=invoice_currency,
				to_currency=company_currency,
				transaction_date=posting_date,
				args=None
			)

			# If ERPNext returns a valid rate, use it
			if conversion_rate and conversion_rate > 0:
				frappe.logger().info(
					f"Using exchange rate {conversion_rate} for {invoice_currency} to {company_currency} on {posting_date}"
				)
				return flt(conversion_rate)

			# If ERPNext returns 0 or None, it means API is disabled or failed
			# Fall back to Invoice Ninja's rate if provided
			if in_exchange_rate and flt(in_exchange_rate) > 0:
				frappe.logger().warning(
					f"ERPNext exchange rate API unavailable. Using Invoice Ninja rate {in_exchange_rate} "
					f"for {invoice_currency} to {company_currency} on {posting_date}"
				)
				return flt(in_exchange_rate)

			# Last resort: use 1.0 but log warning
			frappe.logger().error(
				f"No exchange rate found for {invoice_currency} to {company_currency} on {posting_date}. "
				"Defaulting to 1.0. Please create Currency Exchange record manually or enable API fetching."
			)
			return 1.0

		except Exception as e:
			# If any error occurs, fall back to Invoice Ninja's rate
			frappe.log_error(
				f"Error fetching exchange rate for {invoice_currency} to {company_currency}: {str(e)}",
				"Exchange Rate Fetch Error"
			)

			if in_exchange_rate and flt(in_exchange_rate) > 0:
				return flt(in_exchange_rate)

			return 1.0

	@staticmethod
	def map_customer_from_invoice_ninja(in_customer, invoice_ninja_company=None):
		"""
		Map Invoice Ninja customer to ERPNext customer

		Args:
			in_customer: Invoice Ninja customer data
			invoice_ninja_company: Invoice Ninja Company doc name for linking
		"""
		# Get company mapping - use Invoice Ninja Company from sync context
		if invoice_ninja_company:
			company_mapping = FieldMapper.get_company_mapping_by_invoice_ninja_company_doc(
				invoice_ninja_company
			)
		else:
			# Fallback for legacy sync (shouldn't happen in new flow)
			company_mapping = FieldMapper.get_company_mapping(
				invoice_ninja_company_id=in_customer.get("company_id")
			)

		if not company_mapping:
			frappe.log_error(
				f"No company mapping found for Invoice Ninja customer ID: {in_customer.get('id')}",
				"Customer Mapping Error",
			)
			return None, None, None, None

		# Get customer group mapping based on Invoice Ninja customer group
		customer_group_mapping = None
		default_customer_group = "Commercial"  # Default fallback

		# Check if customer has a group setting from Invoice Ninja
		if in_customer.get("group_settings_id"):
			customer_group_mapping = FieldMapper.get_customer_group_mapping(
				invoice_ninja_company=invoice_ninja_company,  # Pass company context
				invoice_ninja_customer_group_id=in_customer.get("group_settings_id")
			)

		# If no specific mapping found, try to get default mapping
		if not customer_group_mapping:
			customer_group_mapping = FieldMapper.get_customer_group_mapping(
				invoice_ninja_company=invoice_ninja_company  # Pass company context
			)

		# Use mapped customer group or fallback to default
		if customer_group_mapping:
			default_customer_group = customer_group_mapping.customer_group

		# Determine customer type based on classification or name
		customer_type = "Company"
		if in_customer.get("classification"):
			customer_type = (
				"Company" if in_customer.get(
					"classification").lower() == "company" else "Individual"
			)
		elif not in_customer.get("name") or len(in_customer.get("name", "").split()) <= 2:
			customer_type = "Individual"

		# Get primary contact for email/phone
		primary_contact = None
		contacts = in_customer.get("contacts", [])
		if contacts:
			primary_contact = next((c for c in contacts if c.get("is_primary")), contacts[0])

		# Get currency from settings if available
		currency_code = "USD"  # Default
		settings = in_customer.get("settings", {})
		if settings.get("currency_id"):
			currency_code = FieldMapper.get_currency_code(settings.get("currency_id"))

		# Basic customer mapping
		customer_data = {
			"doctype": "Customer",
			"customer_name": in_customer.get("display_name")
							 or in_customer.get("name")
							 or f"Customer {in_customer.get('id')}",
			"customer_type": customer_type,
			"customer_group": default_customer_group,
			"territory": "All Territories",  # Default territory
			"invoice_ninja_id": str(in_customer.get("id")),
			"invoice_ninja_company": invoice_ninja_company,  # Link to IN Company doc
			"invoice_ninja_sync_status": "Synced",
			"company": company_mapping.erpnext_company,  # Set the mapped company
			"default_currency": currency_code,
		}

		# Contact information from primary contact
		if primary_contact:
			if primary_contact.get("email"):
				customer_data["email_id"] = primary_contact.get("email")
			if primary_contact.get("phone"):
				customer_data["mobile_no"] = primary_contact.get("phone")

		# Website and other details
		if in_customer.get("website"):
			customer_data["website"] = in_customer.get("website")

		# Tax information
		if in_customer.get("vat_number"):
			customer_data["tax_id"] = in_customer.get("vat_number")
		elif in_customer.get("id_number"):
			customer_data["tax_id"] = in_customer.get("id_number")

		# Additional fields
		if in_customer.get("public_notes"):
			customer_data["customer_details"] = in_customer.get("public_notes")
		elif in_customer.get("private_notes"):
			customer_data["customer_details"] = in_customer.get("private_notes")

		# Set credit limit if balance information available
		if in_customer.get("credit_balance"):
			customer_data["credit_limit"] = flt(in_customer.get("credit_balance"))

		# Create address if available
		address_data = FieldMapper.map_customer_address(in_customer)

		# Create shipping address if different from billing
		shipping_address_data = FieldMapper.map_customer_shipping_address(in_customer)

		# Create contact data for ERPNext contacts
		contact_data_list = FieldMapper.map_customer_contacts(in_customer,
															  customer_data["customer_name"])

		return customer_data, address_data, shipping_address_data, contact_data_list

	@staticmethod
	def map_customer_address(in_customer):
		"""Map customer address from Invoice Ninja"""
		if not any(
			[in_customer.get("address1"), in_customer.get("city"), in_customer.get("state")]):
			return None

		address_data = {
			"doctype": "Address",
			"address_title": in_customer.get("display_name") or in_customer.get(
				"name") or "Primary",
			"address_type": "Billing",
			"address_line1": in_customer.get("address1") or "",
			"address_line2": in_customer.get("address2") or "",
			"city": in_customer.get("city") or "",
			"state": in_customer.get("state") or "",
			"pincode": in_customer.get("postal_code") or "",
			"country": FieldMapper.get_country_name(in_customer.get("country_id")),
			"is_primary_address": 1,
			"is_shipping_address": 0,
		}

		return address_data

	@staticmethod
	def map_customer_shipping_address(in_customer):
		"""Map customer shipping address from Invoice Ninja"""
		# Check if shipping address exists and is different from billing
		if not any(
			[
				in_customer.get("shipping_address1"),
				in_customer.get("shipping_city"),
				in_customer.get("shipping_state"),
			]
		):
			return None

		# Check if shipping address is different from billing address
		shipping_same_as_billing = (
			in_customer.get("shipping_address1") == in_customer.get("address1")
			and in_customer.get("shipping_city") == in_customer.get("city")
			and in_customer.get("shipping_state") == in_customer.get("state")
			and in_customer.get("shipping_postal_code") == in_customer.get("postal_code")
		)

		if shipping_same_as_billing:
			return None

		address_data = {
			"doctype": "Address",
			"address_title": f"{in_customer.get('display_name') or in_customer.get('name') or 'Customer'} - Shipping",
			"address_type": "Shipping",
			"address_line1": in_customer.get("shipping_address1") or "",
			"address_line2": in_customer.get("shipping_address2") or "",
			"city": in_customer.get("shipping_city") or "",
			"state": in_customer.get("shipping_state") or "",
			"pincode": in_customer.get("shipping_postal_code") or "",
			"country": FieldMapper.get_country_name(in_customer.get("shipping_country_id")),
			"is_primary_address": 0,
			"is_shipping_address": 1,
		}

		return address_data

	@staticmethod
	def map_customer_contacts(in_customer, customer_name):
		"""Map Invoice Ninja customer contacts to ERPNext contacts"""
		contacts = in_customer.get("contacts", [])
		if not contacts:
			return []

		contact_data_list = []

		for idx, contact in enumerate(contacts):
			# Skip if no meaningful contact data
			if not any(
				[
					contact.get("email"),
					contact.get("phone"),
					contact.get("first_name"),
					contact.get("last_name"),
				]
			):
				continue

			contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
			if not contact_name:
				contact_name = f"Contact {idx + 1}"

			contact_data = {
				"doctype": "Contact",
				"first_name": contact.get("first_name") or contact_name,
				"last_name": contact.get("last_name") or "",
				"email_id": contact.get("email") or "",
				"phone": contact.get("phone") or "",
				"is_primary_contact": 1 if contact.get("is_primary") else 0,
				"invoice_ninja_contact_id": str(contact.get("id")),
				# "invoice_ninja_company": invoice_ninja_company,
				"links": [{"link_doctype": "Customer", "link_name": customer_name}],
			}

			# Add custom values if available
			for i in range(1, 5):
				custom_field = f"custom_value{i}"
				if contact.get(custom_field):
					contact_data[f"custom_{custom_field}"] = contact.get(custom_field)

			contact_data_list.append(contact_data)

		return contact_data_list

	@staticmethod
	def map_invoice_from_invoice_ninja(in_invoice, invoice_ninja_company=None):
		"""
		Map Invoice Ninja invoice to ERPNext sales invoice

		Args:
			in_invoice: Invoice Ninja invoice data
			invoice_ninja_company: Invoice_Ninja Company doc name for linking
		"""
		# Get company mapping - use Invoice Ninja Company from sync context
		if invoice_ninja_company:
			company_mapping = FieldMapper.get_company_mapping_by_invoice_ninja_company_doc(
				invoice_ninja_company
			)
		else:
			# Fallback for legacy sync (shouldn't happen in new flow)
			company_mapping = FieldMapper.get_company_mapping(
				invoice_ninja_company_id=in_invoice.get("company_id")
			)

		if not company_mapping:
			frappe.log_error(
				f"No company mapping found for Invoice Ninja company ID: {in_invoice.get('company_id')}",
				"Invoice Mapping Error",
			)
			return None

		# Get customer reference
		customer_name = FieldMapper.get_customer_by_invoice_ninja_id(in_invoice.get("client_id"))
		if not customer_name:
			frappe.log_error(
				f"Customer not found for Invoice Ninja client_id: {in_invoice.get('client_id')}",
				"Invoice Mapping Error",
			)
			return None

		# Get invoice currency
		invoice_currency = FieldMapper.get_currency_code(in_invoice.get("currency_id")) or "USD"

		# Parse dates
		posting_date = FieldMapper.parse_date(in_invoice.get("date")) or nowdate()
		due_date = FieldMapper.parse_date(in_invoice.get("due_date"))

		# Ensure due_date is not before posting_date
		if due_date and due_date < posting_date:
			due_date = posting_date
		elif not due_date:
			# If no due_date provided, set it to posting_date to avoid validation issues
			due_date = posting_date

		# Get company currency for conversion rate calculation
		company_currency = frappe.get_cached_value("Company", company_mapping.erpnext_company, "default_currency")

		# Get conversion rate with automatic API fetching if needed
		conversion_rate = FieldMapper.get_conversion_rate_for_transaction(
			invoice_currency=invoice_currency,
			company_currency=company_currency,
			posting_date=posting_date,
			in_exchange_rate=in_invoice.get("exchange_rate")
		)

		# Basic invoice mapping
		invoice_data = {
			"doctype": "Sales Invoice",
			"customer": customer_name,
			"company": company_mapping.erpnext_company,  # Set the mapped company
			"posting_date": posting_date,
			"posting_time": get_datetime(now_datetime()).time(),
			"set_posting_time": True,
			"due_date": due_date,
			"currency": invoice_currency,
			"conversion_rate": conversion_rate,
			"selling_price_list": "Standard Selling",
			"invoice_ninja_id": str(in_invoice.get("id")),
			"invoice_ninja_company": invoice_ninja_company,
			"invoice_ninja_sync_status": "Synced",
			"invoice_ninja_number": in_invoice.get("number"),
			"status": FieldMapper.map_invoice_status(in_invoice.get("status_id")),
			"items": [],
		}

		print('invoice_data', invoice_data)

		# Set receivable account based on currency mapping (ONLY for Sales Invoices)
		receivable_account = FieldMapper.get_receivable_account_for_currency(
			invoice_ninja_company,
			invoice_currency,
			company_mapping.erpnext_company
		)
		if receivable_account:
			invoice_data["debit_to"] = receivable_account

		# Invoice number
		if in_invoice.get("number"):
			invoice_data["naming_series"] = "INV-"
		# ERPNext will auto-generate, we store IN number in custom field

		# Terms and conditions
		if in_invoice.get("terms"):
			invoice_data["tc_name"] = "Standard Terms"
			invoice_data["terms"] = in_invoice.get("terms")

		# Notes
		if in_invoice.get("public_notes"):
			invoice_data["other_charges_calculation"] = in_invoice.get("public_notes")

		# Map line items
		line_items = in_invoice.get("line_items", [])
		for idx, item in enumerate(line_items, 1):
			item_data = FieldMapper.map_invoice_item(item, idx, invoice_ninja_company)
			if item_data:
				invoice_data["items"].append(item_data)

		# Map taxes if available
		taxes = FieldMapper.map_invoice_taxes(in_invoice, invoice_ninja_company)
		if taxes:
			invoice_data["taxes"] = taxes

		return invoice_data

	@staticmethod
	def map_invoice_item(in_item, idx, invoice_ninja_company=None):
		"""Map Invoice Ninja line item to ERPNext item - supports task-based items"""
		try:
			# Get default UOM for this company
			default_uom = FieldMapper.get_default_product_uom(invoice_ninja_company)

			# Check if this line item is task-based
			task_id = in_item.get('task_id')

			if task_id:
				# Create/sync task inline if it doesn't exist
				task_data = in_item.get('task')  # Invoice Ninja can include task data
				if task_data:
					FieldMapper.sync_task_inline(task_data, invoice_ninja_company)

				# Map line item with task reference
				item_code = FieldMapper.get_or_create_item(in_item)

				# If item doesn't exist, create it
				if not frappe.db.exists("Item", item_code):
					item_doc = frappe.get_doc({
						"doctype": "Item",
						"item_code": item_code,
						"item_name": in_item.get("notes") or in_item.get("product_key") or "Unknown Item",
						"item_group": "Products",
						"stock_uom": default_uom,
						"is_stock_item": 0
					})
					item_doc.insert(ignore_permissions=True)
					frappe.db.commit()

				item_data = {
					"doctype": "Sales Invoice Item",
					"idx": idx,
					"item_code": item_code,
					"item_name": in_item.get("notes") or in_item.get("product_key") or "Service Item",
					"description": in_item.get("notes") or "",
					"qty": flt(in_item.get("quantity")) or 1.0,
					"rate": flt(in_item.get("cost")) or 0.0,
					"amount": flt(in_item.get("quantity", 1)) * flt(in_item.get("cost", 0)),
					"uom": default_uom,
					"invoice_ninja_task_id": str(task_id),
					"custom_is_task_based": 1,
				}
			else:
				# Regular product-based line item
				item_code = FieldMapper.get_or_create_item(in_item)

				# If item doesn't exist, create it
				if not frappe.db.exists("Item", item_code):
					item_doc = frappe.get_doc({
						"doctype": "Item",
						"item_code": item_code,
						"item_name": in_item.get("notes") or in_item.get("product_key") or "Unknown Item",
						"item_group": "Products",
						"stock_uom": default_uom,
						"is_stock_item": 0
					})
					item_doc.insert(ignore_permissions=True)
					frappe.db.commit()

				item_data = {
					"doctype": "Sales Invoice Item",
					"idx": idx,
					"item_code": item_code,
					"item_name": in_item.get("notes") or in_item.get("product_key") or "Service Item",
					"description": in_item.get("notes") or "",
					"qty": flt(in_item.get("quantity")) or 1.0,
					"rate": flt(in_item.get("cost")) or 0.0,
					"amount": flt(in_item.get("quantity", 1)) * flt(in_item.get("cost", 0)),
					"uom": default_uom,
				}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping line item: {e!s}", "Item Mapping Error")
			return None

	@staticmethod
	def map_quote_from_invoice_ninja(in_quote, invoice_ninja_company=None):
		"""
		Map Invoice Ninja quote to ERPNext quotation

		Args:
			in_quote: Invoice Ninja quote data
			invoice_ninja_company: Invoice Ninja Company doc name for linking
		"""
		# Get company mapping - use Invoice Ninja Company from sync context
		if invoice_ninja_company:
			company_mapping = FieldMapper.get_company_mapping_by_invoice_ninja_company_doc(
				invoice_ninja_company
			)
		else:
			# Fallback for legacy sync (shouldn't happen in new flow)
			company_mapping = FieldMapper.get_company_mapping(
				invoice_ninja_company_id=in_quote.get("company_id")
			)

		if not company_mapping:
			frappe.log_error(
				f"No company mapping found for Invoice Ninja company ID: {in_quote.get('company_id')}",
				"Quote Mapping Error",
			)
			return None

		# Get customer reference
		customer_name = FieldMapper.get_customer_by_invoice_ninja_id(in_quote.get("client_id"))
		if not customer_name:
			return None

		# Get quote currency
		quote_currency = FieldMapper.get_currency_code(in_quote.get("currency_id")) or "USD"

		# Get transaction date
		transaction_date = FieldMapper.parse_date(in_quote.get("date")) or nowdate()

		# Get company currency for conversion rate calculation
		company_currency = frappe.get_cached_value("Company", company_mapping.erpnext_company, "default_currency")

		# Get conversion rate with automatic API fetching if needed
		conversion_rate = FieldMapper.get_conversion_rate_for_transaction(
			invoice_currency=quote_currency,
			company_currency=company_currency,
			posting_date=transaction_date,
			in_exchange_rate=in_quote.get("exchange_rate")
		)

		quote_data = {
			"doctype": "Quotation",
			"party_name": customer_name,
			"quotation_to": "Customer",
			"company": company_mapping.erpnext_company,  # Set the mapped company
			"transaction_date": transaction_date,
			"valid_till": FieldMapper.parse_date(in_quote.get("due_date")),
			"currency": quote_currency,
			"conversion_rate": conversion_rate,
			"selling_price_list": "Standard Selling",
			"invoice_ninja_id": str(in_quote.get("id")),
			"invoice_ninja_company": invoice_ninja_company,
			"invoice_ninja_sync_status": "Synced",
			"invoice_ninja_number": in_quote.get("number"),
			"status": FieldMapper.map_quote_status(in_quote.get("status_id")),
			"items": [],
		}

		# Map line items
		line_items = in_quote.get("line_items", [])
		for idx, item in enumerate(line_items, 1):
			item_data = FieldMapper.map_quotation_item(item, idx, invoice_ninja_company)
			if item_data:
				quote_data["items"].append(item_data)

		return quote_data

	@staticmethod
	def map_quotation_item(in_item, idx, invoice_ninja_company=None):
		"""Map Invoice Ninja quote item to ERPNext quotation item"""
		try:
			# Get default UOM for this company
			default_uom = FieldMapper.get_default_product_uom(invoice_ninja_company)

			item_code = FieldMapper.get_or_create_item(in_item)

			item_data = {
				"doctype": "Quotation Item",
				"idx": idx,
				"item_code": item_code,
				"item_name": in_item.get("notes") or in_item.get("product_key") or "Service Item",
				"description": in_item.get("notes") or "",
				"qty": flt(in_item.get("quantity")) or 1.0,
				"rate": flt(in_item.get("cost")) or 0.0,
				"amount": flt(in_item.get("quantity", 1)) * flt(in_item.get("cost", 0)),
				"uom": default_uom,
			}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping quotation item: {e!s}", "Quote Item Mapping Error")
			return None

	@staticmethod
	def map_product_from_invoice_ninja(in_product, invoice_ninja_company=None):
		"""Map Invoice Ninja product to ERPNext item"""
		try:
			# Get default UOM for this company
			default_uom = FieldMapper.get_default_product_uom(invoice_ninja_company)

			item_data = {
				"doctype": "Item",
				"item_code": in_product.get("product_key") or f"IN-PROD-{in_product.get('id')}",
				"item_name": in_product.get("notes") or in_product.get("product_key") or "Unknown Item",
				"item_group": "Products",
				"stock_uom": default_uom,
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 0,
				"include_item_in_manufacturing": 0,
				"description": in_product.get("notes") or "",
				"invoice_ninja_id": str(in_product.get("id")),
				"invoice_ninja_company": invoice_ninja_company,
				"sync_status": "Synced",
			}

			return item_data

		except Exception as e:
			frappe.log_error(f"Error mapping product {in_product.get('id')}: {e!s}", "Product Mapping Error")
			return None

	@staticmethod
	def get_default_product_uom(invoice_ninja_company):
		"""
		Get default product UOM from company settings with validation

		Args:
			invoice_ninja_company: Invoice Ninja Company doc name

		Returns:
			str: Default UOM (defaults to "Nos" if not set or invalid)
		"""
		if not invoice_ninja_company:
			return "Nos"

		try:
			company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)
			default_uom = company_doc.default_product_uom

			# Validate UOM exists in ERPNext
			if default_uom and frappe.db.exists("UOM", default_uom):
				return default_uom
			else:
				return "Nos"  # Fallback if UOM doesn't exist
		except Exception:
			return "Nos"  # Fallback on any error

	@staticmethod
	def get_or_create_item(in_item):
		"""Get existing item or create item code for line item"""

		# Debug logging to identify Invoice Ninja line item structure
		frappe.log_error(
			f"Line item structure: {json.dumps(in_item, indent=2)}",
			"Invoice Line Item Debug"
		)

		# Strategy 1: Look up by Invoice Ninja product ID
		# Invoice Ninja line items may have product references in various fields
		product_id = (
			in_item.get("product_cost")  # Common field name
			or in_item.get("product_id")  # Alternative field name
			or in_item.get("id")  # Some line items have their own ID
		)

		if product_id:
			existing_item = frappe.db.get_value(
				"Item",
				{"invoice_ninja_id": str(product_id)},
				"name"
			)
			if existing_item:
				return existing_item

		# Strategy 2: Try to find existing item by product_key (item_code)
		if in_item.get("product_key"):
			existing_item = frappe.db.get_value(
				"Item",
				{"item_code": in_item.get("product_key")},
				"name"
			)
			if existing_item:
				return existing_item

		# Strategy 3: Return a default service item for line items without product
		# This is common for custom/description-only line items in Invoice Ninja
		if not in_item.get("product_key"):
			# Check if a generic "Service" item exists
			service_item = frappe.db.get_value("Item", {"item_code": "SERVICE"}, "name")
			if service_item:
				return service_item

		# Strategy 4: Create new item code as last resort
		# This will be used if the product doesn't exist in ERPNext yet
		item_code = in_item.get("product_key") or f"IN-ITEM-{frappe.generate_hash(length=8)}"

		# Ensure item code is unique
		if frappe.db.exists("Item", item_code):
			item_code = f"{item_code}-{frappe.generate_hash(length=4)}"

		return item_code

	@staticmethod
	def get_customer_by_invoice_ninja_id(client_id):
		"""Get ERPNext customer name by Invoice Ninja client ID"""
		if not client_id:
			return None

		customer = frappe.db.get_value("Customer", {"invoice_ninja_id": str(client_id)}, "name")
		return customer

	@staticmethod
	def get_currency_code(currency_id):
		"""Map Invoice Ninja currency ID to currency code"""
		if not currency_id:
			return "USD"

		# Comprehensive currency mapping based on Invoice Ninja's currency IDs
		currency_map = {
		"1": "USD",  # US Dollar
		"2": "GBP",  # British Pound
		"3": "EUR",  # Euro
		"4": "CAD",  # Canadian Dollar
		"5": "AUD",  # Australian Dollar
		"6": "JPY",  # Japanese Yen
		"7": "CHF",  # Swiss Franc
		"8": "SEK",  # Swedish Krona
		"9": "NOK",  # Norwegian Krone
		"10": "DKK",  # Danish Krone
		"11": "PLN",  # Polish Zloty
		"12": "BRL",  # Brazilian Real
		"13": "INR",  # Indian Rupee
		"14": "AED",  # UAE Dirham
		"15": "CNY",  # Chinese Yuan
		"16": "ZAR",  # South African Rand
		"17": "BGN",  # Bulgarian Lev
		"18": "CZK",  # Czech Koruna
		"19": "EGP",  # Egyptian Pound
		"20": "HUF",  # Hungarian Forint
		"21": "ISK",  # Icelandic Krona
		"22": "RON",  # Romanian Leu
		"23": "ILS",  # Israeli Shekel
		"24": "MXN",  # Mexican Peso
		"25": "SGD",  # Singapore Dollar
		"26": "HKD",  # Hong Kong Dollar
		"27": "NZD",  # New Zealand Dollar
		"28": "KRW",  # South Korean Won
		"29": "MYR",  # Malaysian Ringgit
		"30": "THB",  # Thai Baht
		"31": "PHP",  # Philippine Peso
		"32": "IDR",  # Indonesian Rupiah
		"33": "TWD",  # Taiwan Dollar
		"34": "VND",  # Vietnamese Dong
		"35": "RUB",  # Russian Ruble
		"36": "TRY",  # Turkish Lira
		"37": "CLP",  # Chilean Peso
		"38": "COP",  # Colombian Peso
		"39": "PEN",  # Peruvian Sol
		"40": "ARS",  # Argentine Peso
		"41": "UYU",  # Uruguayan Peso
		"42": "PYG",  # Paraguayan Guarani
		"43": "BOB",  # Bolivian Boliviano
		"44": "VEF",  # Venezuelan Bolívar
		"45": "GYD",  # Guyanese Dollar
		"46": "SRD",  # Surinamese Dollar
		"47": "FKP",  # Falkland Islands Pound
		"48": "CRC",  # Costa Rican Colón
		"49": "GTQ",  # Guatemalan Quetzal
		"50": "HNL",  # Honduran Lempira
		"51": "NIO",  # Nicaraguan Córdoba
		"52": "PAB",  # Panamanian Balboa
		"53": "BZD",  # Belize Dollar
		"54": "JMD",  # Jamaican Dollar
		"55": "HTG",  # Haitian Gourde
		"56": "DOP",  # Dominican Peso
		"57": "CUP",  # Cuban Peso
		"58": "BBD",  # Barbadian Dollar
		"59": "TTD",  # Trinidad and Tobago Dollar
		"60": "XCD",  # East Caribbean Dollar
		"61": "AWG",  # Aruban Florin
		"62": "ANG",  # Netherlands Antillean Guilder
		"63": "SVC",  # Salvadoran Colón
		"64": "KYD",  # Cayman Islands Dollar
		"65": "BMD",  # Bermudian Dollar
		"66": "BSD",  # Bahamian Dollar
		"67": "USD",  # US Dollar (Puerto Rico)
		"68": "USD",  # US Dollar (US Virgin Islands)
		"69": "MAD",  # Moroccan Dirham
		"70": "TND",  # Tunisian Dinar
		"71": "DZD",  # Algerian Dinar
		"72": "LYD",  # Libyan Dinar
		"73": "SDG",  # Sudanese Pound
		"74": "ETB",  # Ethiopian Birr
		"75": "ERN",  # Eritrean Nakfa
		"76": "DJF",  # Djiboutian Franc
		"77": "SOS",  # Somali Shilling
		"78": "KES",  # Kenyan Shilling
		"79": "UGX",  # Ugandan Shilling
		"80": "TZS",  # Tanzanian Shilling
		"81": "RWF",  # Rwandan Franc
		"82": "BIF",  # Burundian Franc
		"83": "SCR",  # Seychellois Rupee
		"84": "MUR",  # Mauritian Rupee
		"85": "KMF",  # Comorian Franc
		"86": "MGA",  # Malagasy Ariary
		"87": "MWK",  # Malawian Kwacha
		"88": "ZMW",  # Zambian Kwacha
		"89": "ZWL",  # Zimbabwean Dollar
		"90": "BWP",  # Botswanan Pula
		"91": "NAD",  # Namibian Dollar
		"92": "LSL",  # Lesotho Loti
		"93": "SZL",  # Swazi Lilangeni
		"94": "CVE",  # Cape Verdean Escudo
		"95": "GMD",  # Gambian Dalasi
		"96": "GNF",  # Guinean Franc
		"97": "SLL",  # Sierra Leonean Leone
		"98": "LRD",  # Liberian Dollar
		"99": "GHS",  # Ghanaian Cedi
			"100": "NGN",  # Nigerian Naira
		}

		# Convert to string and lookup
		currency_id_str = str(currency_id)
		return currency_map.get(currency_id_str, "USD")

	@staticmethod
	def get_country_name(country_id):
		"""Map Invoice Ninja country ID to country name"""
		if not country_id:
			return "United States"  # Default

		# Comprehensive country mapping based on ISO 3166-1 numeric codes used by Invoice Ninja
		country_map = {
		# Major countries
		"004": "Afghanistan",
		"008": "Albania",
		"012": "Algeria",
		"016": "American Samoa",
		"020": "Andorra",
		"024": "Angola",
		"028": "Antigua and Barbuda",
		"032": "Argentina",
		"036": "Australia",
		"040": "Austria",
		"044": "Bahamas",
		"048": "Bahrain",
		"050": "Bangladesh",
		"052": "Barbados",
		"056": "Belgium",
		"060": "Bermuda",
		"064": "Bhutan",
		"068": "Bolivia",
		"070": "Bosnia and Herzegovina",
		"072": "Botswana",
		"076": "Brazil",
		"084": "Belize",
		"092": "British Virgin Islands",
		"096": "Brunei",
		"100": "Bulgaria",
		"108": "Burundi",
		"116": "Cambodia",
		"120": "Cameroon",
		"124": "Canada",
		"132": "Cape Verde",
		"136": "Cayman Islands",
		"140": "Central African Republic",
		"144": "Sri Lanka",
		"148": "Chad",
		"152": "Chile",
		"156": "China",
		"170": "Colombia",
		"174": "Comoros",
		"178": "Congo",
		"180": "Congo, Democratic Republic",
		"188": "Costa Rica",
		"191": "Croatia",
		"192": "Cuba",
		"196": "Cyprus",
		"203": "Czech Republic",
		"208": "Denmark",
		"214": "Dominican Republic",
		"218": "Ecuador",
		"222": "El Salvador",
		"226": "Equatorial Guinea",
		"231": "Ethiopia",
		"232": "Eritrea",
		"233": "Estonia",
		"234": "Faroe Islands",
		"238": "Falkland Islands",
		"242": "Fiji",
		"246": "Finland",
		"250": "France",
		"254": "French Guiana",
		"258": "French Polynesia",
		"262": "Djibouti",
		"266": "Gabon",
		"268": "Georgia",
		"270": "Gambia",
		"276": "Germany",
		"288": "Ghana",
		"292": "Gibraltar",
		"296": "Kiribati",
		"300": "Greece",
		"304": "Greenland",
		"308": "Grenada",
		"312": "Guadeloupe",
		"316": "Guam",
		"320": "Guatemala",
		"324": "Guinea",
		"328": "Guyana",
		"332": "Haiti",
		"336": "Vatican City",
		"340": "Honduras",
		"344": "Hong Kong",
		"348": "Hungary",
		"352": "Iceland",
		"356": "India",
		"360": "Indonesia",
		"364": "Iran",
		"368": "Iraq",
		"372": "Ireland",
		"376": "Israel",
		"380": "Italy",
		"384": "Ivory Coast",
		"388": "Jamaica",
		"392": "Japan",
		"398": "Kazakhstan",
		"400": "Jordan",
		"404": "Kenya",
		"408": "North Korea",
		"410": "South Korea",
		"414": "Kuwait",
		"417": "Kyrgyzstan",
		"418": "Laos",
		"422": "Lebanon",
		"426": "Lesotho",
		"428": "Latvia",
		"430": "Liberia",
		"434": "Libya",
		"438": "Liechtenstein",
		"440": "Lithuania",
		"442": "Luxembourg",
		"446": "Macau",
		"450": "Madagascar",
		"454": "Malawi",
		"458": "Malaysia",
		"462": "Maldives",
		"466": "Mali",
		"470": "Malta",
		"474": "Martinique",
		"478": "Mauritania",
		"480": "Mauritius",
		"484": "Mexico",
		"492": "Monaco",
		"496": "Mongolia",
		"498": "Moldova",
		"499": "Montenegro",
		"500": "Montserrat",
		"504": "Morocco",
		"508": "Mozambique",
		"512": "Oman",
		"516": "Namibia",
		"520": "Nauru",
		"524": "Nepal",
		"528": "Netherlands",
		"530": "Netherlands Antilles",
		"533": "Aruba",
		"540": "New Caledonia",
		"548": "Vanuatu",
		"554": "New Zealand",
		"558": "Nicaragua",
		"562": "Niger",
		"566": "Nigeria",
		"570": "Niue",
		"574": "Norfolk Island",
		"578": "Norway",
		"580": "Northern Mariana Islands",
		"581": "United States Minor Outlying Islands",
		"583": "Micronesia",
		"584": "Marshall Islands",
		"585": "Palau",
		"586": "Pakistan",
		"591": "Panama",
		"598": "Papua New Guinea",
		"600": "Paraguay",
		"604": "Peru",
		"608": "Philippines",
		"612": "Pitcairn Islands",
		"616": "Poland",
		"620": "Portugal",
		"624": "Guinea-Bissau",
		"626": "East Timor",
		"630": "Puerto Rico",
		"634": "Qatar",
		"638": "Reunion",
		"642": "Romania",
		"643": "Russia",
		"646": "Rwanda",
		"654": "Saint Helena",
		"659": "Saint Kitts and Nevis",
		"660": "Anguilla",
		"662": "Saint Lucia",
		"666": "Saint Pierre and Miquelon",
		"670": "Saint Vincent and the Grenadines",
		"674": "San Marino",
		"678": "Sao Tome and Principe",
		"682": "Saudi Arabia",
		"686": "Senegal",
		"688": "Serbia",
		"690": "Seychelles",
		"694": "Sierra Leone",
		"702": "Singapore",
		"703": "Slovakia",
		"704": "Vietnam",
		"705": "Slovenia",
		"706": "Somalia",
		"710": "South Africa",
		"716": "Zimbabwe",
		"724": "Spain",
		"732": "Western Sahara",
		"736": "Sudan",
		"740": "Suriname",
		"744": "Svalbard and Jan Mayen",
		"748": "Swaziland",
		"752": "Sweden",
		"756": "Switzerland",
		"760": "Syria",
		"762": "Tajikistan",
		"764": "Thailand",
		"768": "Togo",
		"772": "Tokelau",
		"776": "Tonga",
		"780": "Trinidad and Tobago",
		"784": "United Arab Emirates",
		"788": "Tunisia",
		"792": "Turkey",
		"795": "Turkmenistan",
		"796": "Turks and Caicos Islands",
		"798": "Tuvalu",
		"800": "Uganda",
		"804": "Ukraine",
		"807": "Macedonia",
		"818": "Egypt",
		"826": "United Kingdom",
		"834": "Tanzania",
		"840": "United States",
		"850": "United States Virgin Islands",
		"854": "Burkina Faso",
		"858": "Uruguay",
		"860": "Uzbekistan",
		"862": "Venezuela",
		"876": "Wallis and Futuna",
		"882": "Samoa",
		"887": "Yemen",
			"894": "Zambia",
		}

		# Convert to string and lookup
		country_id_str = str(country_id)
		return country_map.get(country_id_str, "United States")

	@staticmethod
	def map_invoice_status(status_id):
		"""Map Invoice Ninja invoice status to ERPNext status"""
		status_map = {"1": "Draft", "2": "Submitted", "3": "Paid", "4": "Cancelled", "5": "Overdue"}
		return status_map.get(str(status_id), "Draft")

	@staticmethod
	def map_quote_status(status_id):
		"""Map Invoice Ninja quote status to ERPNext status"""
		status_map = {"1": "Draft", "2": "Open", "3": "Ordered", "4": "Expired", "5": "Cancelled"}
		return status_map.get(str(status_id), "Draft")

	@staticmethod
	def parse_date(date_string):
		"""Parse date string to ERPNext format"""
		if not date_string:
			return None
		try:
			if isinstance(date_string, str):
				# Handle various date formats
				date_string = date_string.split(" ")[0]  # Remove time part
				return get_datetime(date_string).date()
			return date_string
		except Exception:
			return None

	@staticmethod
	def parse_time(date_string):
		"""Parse time string to ERPNext format"""
		if not date_string:
			return None
		try:
			if isinstance(date_string, str):
				return get_datetime(date_string).time()
			return date_string
		except Exception:
			return None

	@staticmethod
	def map_invoice_taxes(in_invoice, invoice_ninja_company=None):
		"""Map Invoice Ninja taxes to ERPNext taxes"""
		taxes = []
		settings = frappe.get_single("Invoice Ninja Settings")

		# Invoice Ninja can have multiple tax fields: tax_name1, tax_rate1, tax_name2, tax_rate2, etc.
		for i in range(1, 4):  # Support up to 3 taxes
			tax_name_field = f"tax_name{i}"
			tax_rate_field = f"tax_rate{i}"
			tax_amount_field = f"tax_amount{i}" if i > 1 else "tax_amount"

			tax_name = in_invoice.get(tax_name_field)
			tax_rate = flt(in_invoice.get(tax_rate_field, 0))
			tax_amount = flt(in_invoice.get(tax_amount_field, 0))

			if not tax_amount and not tax_rate:
				continue

			# Try to find mapping
			tax_template = None

			# Look up by tax name/ID if available
			if tax_name:
				# Try to find Invoice Ninja Tax Rate by name
				tax_rate_doc = frappe.db.get_value(
					"Invoice Ninja Tax Rate",
					{"tax_name": tax_name},
					["name", "tax_rate_id"],
					as_dict=True
				)

				if tax_rate_doc:
					tax_mapping = FieldMapper.get_tax_template_mapping(
						invoice_ninja_company=invoice_ninja_company,  # Pass company context
						invoice_ninja_tax_rate_id=tax_rate_doc.tax_rate_id
					)
					if tax_mapping:
						tax_template = tax_mapping.tax_template

			# If no mapping found, use default
			if not tax_template and settings.default_tax_template:
				tax_template = settings.default_tax_template

			# Get the first tax account from the template
			account_head = "VAT - Company"  # Fallback
			if tax_template:
				template_doc = frappe.get_doc("Sales Taxes and Charges Template", tax_template)
				if template_doc.taxes and len(template_doc.taxes) > 0:
					account_head = template_doc.taxes[0].account_head

			tax_data = {
				"doctype": "Sales Taxes and Charges",
				"charge_type": "Actual",
				"account_head": account_head,
				"rate": tax_rate,
				"tax_amount": tax_amount,
				"description": tax_name or f"Tax from Invoice Ninja ({tax_rate}%)",
			}
			taxes.append(tax_data)

		return taxes

	@staticmethod
	def map_customer_to_invoice_ninja(customer_doc):
		"""Map ERPNext customer to Invoice Ninja format"""
		# Validate and get company mapping
		company_mapping = FieldMapper.validate_company_mapping(customer_doc)

		customer_data = {
			"name": customer_doc.customer_name,
			"display_name": customer_doc.customer_name,
			"email": customer_doc.email_id or "",
			"phone": customer_doc.mobile_no or "",
			"website": customer_doc.website or "",
			"vat_number": customer_doc.tax_id or "",
			"public_notes": customer_doc.customer_details or "",
			"is_company": 1 if customer_doc.customer_type == "Company" else 0,
			"company_id": company_mapping.invoice_ninja_company_id,  # Add company mapping
		}

		# Add customer group mapping if available
		customer_group_mapping = FieldMapper.get_customer_group_mapping(
			erpnext_customer_group=customer_doc.customer_group
		)
		if customer_group_mapping and customer_group_mapping.invoice_ninja_customer_group:
			# Get the group_id from the linked Invoice Ninja Customer Group document
			group_id = frappe.db.get_value(
				"Invoice Ninja Customer Group",
				customer_group_mapping.invoice_ninja_customer_group,
				"group_id",
			)
			if group_id:
				customer_data["group_settings_id"] = group_id

		# Add address information
		address = frappe.db.get_value(
			"Address",
			{"link_doctype": "Customer", "link_name": customer_doc.name, "is_primary_address": 1},
			["address_line1", "address_line2", "city", "state", "pincode", "country"],
			as_dict=True,
		)

		if address:
			customer_data.update(
				{
					"address1": address.address_line1 or "",
					"address2": address.address_line2 or "",
					"city": address.city or "",
					"state": address.state or "",
					"postal_code": address.pincode or "",
					"country_id": FieldMapper.get_country_id(address.country),
				}
			)

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
			"client_id": client_id,
			"company_id": company_mapping.invoice_ninja_company_id,  # Add company mapping
			"date": str(invoice_doc.posting_date),
			"due_date": str(invoice_doc.due_date) if invoice_doc.due_date else None,
			"number": invoice_doc.name,
			"public_notes": invoice_doc.remarks or "",
			"terms": invoice_doc.terms or "",
			"currency_id": FieldMapper.get_currency_id(invoice_doc.currency),
			"exchange_rate": invoice_doc.conversion_rate or 1.0,
			"line_items": [],
		}

		# Add line items
		for item in invoice_doc.items:
			line_item = {
				"product_key": item.item_code,
				"notes": item.description or item.item_name,
				"qty": item.qty,
				"cost": item.rate,
				"discount": item.discount_percentage or 0,
			}
			invoice_data["line_items"].append(line_item)

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
			"client_id": client_id,
			"company_id": company_mapping.invoice_ninja_company_id,  # Add company mapping
			"date": str(quotation_doc.transaction_date),
			"valid_until": str(quotation_doc.valid_till) if quotation_doc.valid_till else None,
			"number": quotation_doc.name,
			"public_notes": quotation_doc.terms or "",
			"currency_id": FieldMapper.get_currency_id(quotation_doc.currency),
			"exchange_rate": quotation_doc.conversion_rate or 1.0,
			"line_items": [],
		}

		# Add line items
		for item in quotation_doc.items:
			line_item = {
				"product_key": item.item_code,
				"notes": item.description or item.item_name,
				"qty": item.qty,
				"cost": item.rate,
				"discount": item.discount_percentage or 0,
			}
			quote_data["line_items"].append(line_item)

		return quote_data

	@staticmethod
	def map_item_to_invoice_ninja(item_doc):
		"""Map ERPNext item to Invoice Ninja product format"""
		product_data = {
			"product_key": item_doc.item_code,
			"notes": item_doc.description or item_doc.item_name,
			"cost": item_doc.standard_rate or 0,
			"price": item_doc.standard_rate or 0,
			"tax_name": "",  # Map tax template if needed
			"tax_rate": 0,  # Map tax rate if needed
		}

		return product_data

	@staticmethod
	def map_item_from_invoice_ninja(in_product, invoice_ninja_company=None):
		"""
		Map Invoice Ninja product to ERPNext item with tax rate

		Args:
			in_product: Invoice Ninja product data
			invoice_ninja_company: Invoice Ninja Company doc name for linking
		"""
		# Get default UOM for this company
		default_uom = FieldMapper.get_default_product_uom(invoice_ninja_company)

		# Get item group mapping based on Invoice Ninja tax category
		# Use default item group for all items
		default_item_group = "Products"

		# Add tax rate application
		tax_template = None
		if in_product.get("tax_rate1") or in_product.get("tax_id"):
			tax_rate_id = in_product.get("tax_rate1") or in_product.get("tax_id")

			# Find matching tax rate
			tax_rate_doc = frappe.db.get_value(
				"Invoice Ninja Tax Rate",
				{"tax_rate_id": str(tax_rate_id)},
				["name", "rate", "account_head", "tax_name"],
				as_dict=True
			)

			if tax_rate_doc and tax_rate_doc.account_head:
				# Get ERPNext company from mapping
				company_mapping = FieldMapper.get_company_mapping_by_invoice_ninja_company_doc(
					invoice_ninja_company
				)
				company = company_mapping.company if company_mapping else None

				if company:
					# Create or get tax template for this rate
					tax_template = FieldMapper.get_or_create_tax_template_for_rate(
						tax_rate_doc,
						company
					)

		item_data = {
			"doctype": "Item",
			"item_code": in_product.get("product_key") or f"IN-{in_product.get('id')}",
			"item_name": in_product.get("notes") or in_product.get("product_key"),
			"description": in_product.get("notes") or in_product.get("product_key"),
			"item_group": default_item_group,  # Use mapped group
			"stock_uom": default_uom,
			"is_stock_item": 0,
			"is_sales_item": 1,
			"standard_rate": flt(in_product.get("price", 0)),
			"invoice_ninja_id": str(in_product.get("id")),
			"invoice_ninja_company": invoice_ninja_company,
			"invoice_ninja_sync_status": "Synced",
		}

		# Add tax template if found
		if tax_template:
			item_data["taxes"] = [{
				"item_tax_template": tax_template
			}]

		return item_data

	@staticmethod
	def map_payment_from_invoice_ninja(in_payment, invoice_ninja_company=None):
		"""
		Map Invoice Ninja payment to ERPNext payment entry

		Args:
			in_payment: Invoice Ninja payment data
			invoice_ninja_company: Invoice Ninja Company doc name for linking
		"""
		# Get related invoice
		invoice_id = in_payment.get("invoice_id")
		if not invoice_id:
			return None

		invoice_name = frappe.db.get_value("Sales Invoice", {"invoice_ninja_id": str(invoice_id)}, "name")
		if not invoice_name:
			frappe.log_error(
				f"Invoice not found for Invoice Ninja payment: {in_payment.get('id')}",
				"Payment Mapping Error",
			)
			return None

		invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)

		payment_data = {
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": invoice_doc.customer,
			"posting_date": FieldMapper.parse_date(in_payment.get("date")) or nowdate(),
			"paid_amount": flt(in_payment.get("amount", 0)),
			"received_amount": flt(in_payment.get("amount", 0)),
			"source_exchange_rate": 1.0,
			"target_exchange_rate": 1.0,
			"reference_no": in_payment.get("transaction_reference") or "",
			"reference_date": FieldMapper.parse_date(in_payment.get("date")),
			"invoice_ninja_id": str(in_payment.get("id")),
			"invoice_ninja_company": invoice_ninja_company,
			"sync_status": "Synced",
			"references": [
				{
					"doctype": "Payment Entry Reference",
					"reference_doctype": "Sales Invoice",
					"reference_name": invoice_name,
					"allocated_amount": flt(in_payment.get("amount", 0)),
				}
			],
		}

		# Set default accounts (adjust based on your setup)
		payment_data["paid_from"] = frappe.db.get_value(
			"Account", {"account_type": "Receivable", "is_group": 0}, "name"
		)
		payment_data["paid_to"] = frappe.db.get_value(
			"Account", {"account_type": "Cash", "is_group": 0}, "name"
		)

		return payment_data

	@staticmethod
	def map_task_from_invoice_ninja(in_task, invoice_ninja_company=None):
		"""
		Map Invoice Ninja task to ERPNext Invoice Ninja Task

		Args:
			in_task: Invoice Ninja task data
			invoice_ninja_company: Invoice Ninja Company doc name for linking
		"""
		# Calculate duration in hours
		duration_seconds = int(in_task.get('duration', 0))
		duration_hours = duration_seconds / 3600.0 if duration_seconds > 0 else 0

		# Map client to customer
		customer = None
		if in_task.get('client_id'):
			customer = frappe.db.get_value(
				"Customer",
				{"invoice_ninja_id": str(in_task.get('client_id'))},
				"name"
			)

		# Map project if available
		project = None
		if in_task.get('project_id'):
			project = frappe.db.get_value(
				"Project",
				{"invoice_ninja_project_id": str(in_task.get('project_id'))},
				"name"
			)

		# Determine status
		status = "Logged"
		if in_task.get('invoice_id'):
			status = "Invoiced"
		elif in_task.get('is_running'):
			status = "Running"

		task_data = {
			"doctype": "Invoice Ninja Task",
			"task_id": str(in_task.get('id')),
			"task_number": in_task.get('number'),
			"description": in_task.get('description') or in_task.get('notes') or "Time Entry",
			"invoice_ninja_company": invoice_ninja_company,
			"client_id": str(in_task.get('client_id')) if in_task.get('client_id') else None,
			"customer": customer,
			"project_id": str(in_task.get('project_id')) if in_task.get('project_id') else None,
			"project": project,
			"duration": duration_seconds,
			"duration_hours": duration_hours,
			"start_time": in_task.get('start_time'),
			"end_time": in_task.get('end_time'),
			"is_running": int(in_task.get('is_running', 0)),
			"rate": flt(in_task.get('rate', 0)),
			"status": status,
			"is_invoiced": 1 if in_task.get('invoice_id') else 0,
			"invoice_id": str(in_task.get('invoice_id')) if in_task.get('invoice_id') else None,
			"sync_status": "Synced",
			"last_synced": now_datetime(),
		}

		return task_data

	@staticmethod
	def sync_task_inline(task_data, invoice_ninja_company):
		"""
		Create/update task record inline during invoice sync

		Args:
			task_data: Task data from Invoice Ninja (can be nested in invoice)
			invoice_ninja_company: Company reference for the task
		"""
		task_id = str(task_data.get('id'))

		# Check if task already exists
		existing = frappe.db.exists("Invoice Ninja Task", {"task_id": task_id})

		if not existing:
			# Create new task record
			task_doc_data = FieldMapper.map_task_from_invoice_ninja(task_data, invoice_ninja_company)
			if task_doc_data:
				doc = frappe.get_doc(task_doc_data)
				doc.insert(ignore_permissions=True)
				frappe.db.commit()

	@staticmethod
	def get_currency_id(currency_code):
		"""Get Invoice Ninja currency ID from code"""
		# This is a simplified mapping - you'd need the actual currency IDs from Invoice Ninja
		currency_map = {"USD": 1, "EUR": 3, "GBP": 2, "AUD": 12, "CAD": 4}
		return currency_map.get(currency_code, 1)  # Default to USD

	@staticmethod
	def get_country_id(country_name):
		"""Get Invoice Ninja country ID from name"""
		# This is a simplified mapping - you'd need the actual country IDs from Invoice Ninja
		if not country_name:
			return 840  # Default to US

		country_map = {
			"United States": 840,
			"United Kingdom": 826,
			"Canada": 124,
			"Australia": 36,
			"Germany": 276,
			"France": 250,
		}
		return country_map.get(country_name, 840)

	@staticmethod
	def get_item_code(product_key):
		"""Get ERPNext item code from Invoice Ninja product key"""
		if not product_key:
			return "Service"  # Default service item

		# Try to find existing item
		existing_item = frappe.db.get_value("Item", {"item_code": product_key}, "name")
		if existing_item:
			return existing_item

		# Return the product key as item code (will be created if needed)
		return product_key

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
			elif invoice_ninja_company_id and str(mapping.invoice_ninja_company_id) == str(
				invoice_ninja_company_id
			):
				return mapping

		# Return default mapping if no specific match found
		for mapping in settings.company_mappings:
			if mapping.enabled and mapping.is_default:
				return mapping

		return None

	@staticmethod
	def get_company_mapping_by_invoice_ninja_company_doc(invoice_ninja_company_doc_name):
		"""
		Get company mapping using Invoice Ninja Company doc name

		Args:
			invoice_ninja_company_doc_name: Name of Invoice Ninja Company doc (e.g., "IN-COM-001")

		Returns:
			Company mapping object with erpnext_company, invoice_ninja_company_id, etc.
		"""
		if not invoice_ninja_company_doc_name:
			return None

		# Get the Invoice Ninja Company doc
		in_company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company_doc_name)

		# Find the mapping for this company
		settings = frappe.get_single("Invoice Ninja Settings")
		if not settings.company_mappings:
			return None

		for mapping in settings.company_mappings:
			if not mapping.enabled:
				continue

			# Match by company_id or company name
			if (mapping.invoice_ninja_company_id == in_company_doc.company_id or
				mapping.invoice_ninja_company_id == invoice_ninja_company_doc_name):
				return mapping

		return None

	@staticmethod
	def get_customer_group_mapping(invoice_ninja_company=None, erpnext_customer_group=None, invoice_ninja_customer_group_id=None):
		"""Get customer group mapping for a specific Invoice Ninja Company"""

		if not invoice_ninja_company:
			# Fallback to global settings (deprecated)
			settings = frappe.get_single("Invoice Ninja Settings")
			mappings = settings.customer_group_mappings
		else:
			# Get mappings from the specific company
			company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)
			mappings = company_doc.customer_group_mappings

		if not mappings:
			return None

		for mapping in mappings:
			if erpnext_customer_group and mapping.customer_group == erpnext_customer_group:
				return mapping
			elif invoice_ninja_customer_group_id and mapping.invoice_ninja_customer_group:
				# Fetch the actual group_id from the linked DocType (filtered by company)
				group_id = frappe.db.get_value(
					"Invoice Ninja Customer Group",
					{
						"name": mapping.invoice_ninja_customer_group,
						"invoice_ninja_company": invoice_ninja_company
					},
					"group_id"
				)
				if group_id and str(group_id) == str(invoice_ninja_customer_group_id):
					return mapping

		return None

	@staticmethod
	def get_tax_template_mapping(invoice_ninja_company=None, erpnext_tax_template=None, invoice_ninja_tax_rate_id=None):
		"""Get tax template mapping for a specific Invoice Ninja Company"""

		if not invoice_ninja_company:
			# Fallback to global settings (deprecated)
			settings = frappe.get_single("Invoice Ninja Settings")
			mappings = settings.tax_template_mappings
		else:
			# Get mappings from the specific company
			company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)
			mappings = company_doc.tax_template_mappings

		if not mappings:
			return None

		for mapping in mappings:
			if erpnext_tax_template and mapping.tax_template == erpnext_tax_template:
				return mapping
			elif invoice_ninja_tax_rate_id and mapping.invoice_ninja_tax_rate:
				# Fetch tax_rate_id filtered by company
				tax_rate_id = frappe.db.get_value(
					"Invoice Ninja Tax Rate",
					{
						"name": mapping.invoice_ninja_tax_rate,
						"invoice_ninja_company": invoice_ninja_company
					},
					"tax_rate_id"
				)
				if tax_rate_id and str(tax_rate_id) == str(invoice_ninja_tax_rate_id):
					return mapping

		return None

	@staticmethod
	def get_or_create_tax_template_for_rate(tax_rate_doc, company):
		"""Get or create Sales Taxes and Charges Template for a tax rate"""

		template_name = f"IN-{tax_rate_doc.tax_name}-{company}"

		# Check if template exists
		if frappe.db.exists("Sales Taxes and Charges Template", template_name):
			return template_name

		# Create new template
		template = frappe.get_doc({
			"doctype": "Sales Taxes and Charges Template",
			"title": template_name,
			"company": company,
			"taxes": [{
				"charge_type": "On Net Total",
				"account_head": tax_rate_doc.account_head,
				"rate": tax_rate_doc.rate,
				"description": tax_rate_doc.tax_name
			}]
		})
		template.insert(ignore_permissions=True)

		return template.name

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
		if hasattr(doc, "company"):
			company = doc.company
		elif hasattr(doc, "customer") and doc.customer:
			# Get company from customer's default company
			customer_doc = frappe.get_doc("Customer", doc.customer)
			if hasattr(customer_doc, "default_company"):
				company = customer_doc.default_company

		if not company:
			# Use default company
			company = frappe.db.get_single_value("Global Defaults", "default_company")

		if not company:
			frappe.throw(
				"Cannot determine company for document. Please ensure company mappings are configured."
			)

		# Check if company mapping exists
		mapping = FieldMapper.get_company_mapping(erpnext_company=company)
		if not mapping:
			frappe.throw(
				f"No company mapping found for ERPNext company '{company}'. Please configure company mappings in Invoice Ninja Settings."
			)

		return mapping

	@staticmethod
	def map_product_to_invoice_ninja(item_doc):
		"""Map ERPNext item to Invoice Ninja product format (alias for map_item_to_invoice_ninja)"""
		return FieldMapper.map_item_to_invoice_ninja(item_doc)

	@staticmethod
	def get_receivable_account_for_currency(invoice_ninja_company, currency, erpnext_company):
		"""
		Get the appropriate receivable account for a given currency

		Args:
			invoice_ninja_company: Invoice Ninja Company doc name
			currency: Currency code (e.g., 'USD', 'EUR')
			erpnext_company: ERPNext company name

		Returns:
			Account name or None
		"""
		if not invoice_ninja_company or not currency:
			return None

		# Get the Invoice Ninja Company document
		company_doc = frappe.get_doc("Invoice Ninja Company", invoice_ninja_company)

		# Look for currency mapping
		if company_doc.currency_account_mappings:
			for mapping in company_doc.currency_account_mappings:
				if mapping.currency == currency:
					# Validate that the account belongs to the correct company
					account_company = frappe.db.get_value(
						"Account",
						mapping.receivable_account,
						"company"
					)
					if account_company == erpnext_company:
						return mapping.receivable_account

		# If no specific mapping found, check for default mapping
		if company_doc.currency_account_mappings:
			for mapping in company_doc.currency_account_mappings:
				if mapping.is_default:
					return mapping.receivable_account

		# Final fallback: return None and let ERPNext use customer default
		return None

	@staticmethod
	def validate_currency_mapping_exists(invoice_ninja_company, currency, erpnext_company):
		"""
		Check if currency mapping exists for the given currency

		Returns:
			tuple: (exists: bool, account: str or None, message: str)
		"""
		if not invoice_ninja_company or not currency:
			return False, None, "Missing company or currency information"

		account = FieldMapper.get_receivable_account_for_currency(
			invoice_ninja_company,
			currency,
			erpnext_company
		)

		if account:
			return True, account, ""
		else:
			return False, None, f"No receivable account mapping found for currency {currency}"

	@staticmethod
	def map_quote_to_invoice_ninja(quotation_doc):
		"""Map ERPNext quotation to Invoice Ninja quote format (alias for map_quotation_to_invoice_ninja)"""
		return FieldMapper.map_quotation_to_invoice_ninja(quotation_doc)

	@staticmethod
	def map_payment_to_invoice_ninja(payment_doc):
		"""Map ERPNext payment entry to Invoice Ninja payment format"""
		try:
			# Get related invoice(s)
			invoice_refs = payment_doc.references or []
			if not invoice_refs:
				frappe.log_error(
					f"Payment {payment_doc.name} has no invoice references", "Payment Mapping Error"
				)
				return None

			# Get first invoice reference (Invoice Ninja payments are typically for single invoices)
			main_ref = invoice_refs[0]
			if main_ref.reference_doctype != "Sales Invoice":
				return None

			# Get Invoice Ninja invoice ID
			invoice_doc = frappe.get_doc("Sales Invoice", main_ref.reference_name)
			invoice_ninja_id = getattr(invoice_doc, "invoice_ninja_id", None)
			if not invoice_ninja_id:
				frappe.log_error(
					f"Invoice {invoice_doc.name} not synced to Invoice Ninja", "Payment Mapping Error"
				)
				return None

			payment_data = {
				"invoice_id": invoice_ninja_id,
				"amount": float(payment_doc.paid_amount),
				"payment_date": str(payment_doc.posting_date),
				"payment_type_id": 1,  # Default payment type
				"transaction_reference": payment_doc.reference_no or "",
				"private_notes": payment_doc.remarks or "",
			}

			return payment_data

		except Exception as e:
			frappe.log_error(f"Error mapping payment {payment_doc.name}: {e!s}", "Payment Mapping Error")
			return None
