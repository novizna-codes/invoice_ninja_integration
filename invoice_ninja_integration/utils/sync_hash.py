# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib
import json
import frappe


class SyncHashManager:
	"""Manages hashing and comparison for incremental sync"""

	# Define which fields to track for each entity type
	TRACKED_FIELDS = {
		"Customer": [
			"customer_name", "customer_type", "customer_group",
			"territory", "email_id", "mobile_no", "phone_no",
			"website", "tax_id", "is_frozen"
		],
		"Sales Invoice": [
			"customer", "posting_date", "due_date", "currency",
			"conversion_rate", "total", "grand_total", "outstanding_amount",
			"status", "items"  # Will hash line items separately
		],
		"Quotation": [
			"party_name", "quotation_to", "transaction_date",
			"valid_till", "currency", "grand_total", "status", "items"
		],
		"Item": [
			"item_code", "item_name", "item_group", "stock_uom",
			"description", "standard_rate", "is_stock_item"
		],
		"Payment Entry": [
			"party_type", "party", "payment_type", "posting_date",
			"paid_amount", "received_amount", "references"
		],
		"Invoice Ninja Task": [
			"task_id", "description", "duration", "rate",
			"is_invoiced", "status"
		]
	}

	@staticmethod
	def calculate_hash(data, entity_type):
		"""
		Calculate hash for an entity based on tracked fields

		Args:
			data: Dictionary of entity data
			entity_type: Type of entity (Customer, Sales Invoice, etc.)

		Returns:
			str: MD5 hash of tracked fields
		"""
		tracked_fields = SyncHashManager.TRACKED_FIELDS.get(entity_type, [])

		# Extract only tracked fields
		tracked_data = {}
		for field in tracked_fields:
			if field in data:
				value = data[field]
				# Handle special cases
				if field == "items" and isinstance(value, list):
					# Hash line items
					tracked_data[field] = SyncHashManager._hash_line_items(value)
				elif field == "references" and isinstance(value, list):
					# Hash payment references
					tracked_data[field] = SyncHashManager._hash_references(value)
				else:
					tracked_data[field] = value

		# Convert to JSON string and hash
		json_str = json.dumps(tracked_data, sort_keys=True, default=str)
		return hashlib.md5(json_str.encode()).hexdigest()

	@staticmethod
	def _hash_line_items(items):
		"""Hash line items for invoices/quotations"""
		item_hashes = []
		for item in items:
			item_data = {
				"item_code": item.get("item_code"),
				"qty": item.get("qty"),
				"rate": item.get("rate"),
				"amount": item.get("amount")
			}
			item_hashes.append(json.dumps(item_data, sort_keys=True))
		return hashlib.md5("|".join(item_hashes).encode()).hexdigest()

	@staticmethod
	def _hash_references(references):
		"""Hash payment references"""
		ref_hashes = []
		for ref in references:
			ref_data = {
				"reference_doctype": ref.get("reference_doctype"),
				"reference_name": ref.get("reference_name"),
				"allocated_amount": ref.get("allocated_amount")
			}
			ref_hashes.append(json.dumps(ref_data, sort_keys=True))
		return hashlib.md5("|".join(ref_hashes).encode()).hexdigest()

	@staticmethod
	def get_existing_hash(doctype, invoice_ninja_id):
		"""Get stored hash for existing ERPNext record"""
		# Query the custom hash field
		hash_value = frappe.db.get_value(
			doctype,
			{"invoice_ninja_id": invoice_ninja_id},
			"invoice_ninja_sync_hash"
		)
		return hash_value

	@staticmethod
	def store_hash(doc, hash_value):
		"""Store hash in ERPNext record"""
		doc.db_set("invoice_ninja_sync_hash", hash_value, update_modified=False)

