"""
Entity Mapper for Invoice Ninja Integration

Centralized mapping configuration between ERPNext doctypes,
Invoice Ninja API entities, and user interface labels.
"""

import frappe


class EntityMapper:
	"""
	Centralized entity mapping between ERPNext doctypes and Invoice Ninja API entities

	This class serves as the single source of truth for all entity type mappings
	used throughout the Invoice Ninja integration.
	"""

	# Master configuration - single source of truth
	ENTITY_MAPPING = {
		"Customer": {
			"erpnext_doctype": "Customer",
			"invoice_ninja_endpoint": "clients",
			"invoice_ninja_method": "get_customers",
			"invoice_ninja_entity": "client",
			"include_params": "contacts,group_settings",
			"description": "Customer records and contacts"
		},
		"Sales Invoice": {
			"erpnext_doctype": "Sales Invoice",
			"invoice_ninja_endpoint": "invoices",
			"invoice_ninja_method": "get_invoices",
			"invoice_ninja_entity": "invoice",
			"include_params": "client.group_settings,project",
			"description": "Sales invoices and billing documents"
		},
		"Quotation": {
			"erpnext_doctype": "Quotation",
			"invoice_ninja_endpoint": "quotes",
			"invoice_ninja_method": "get_quotes",
			"invoice_ninja_entity": "quote",
			"include_params": "client,line_items",
			"description": "Quotations and estimates"
		},
		"Item": {
			"erpnext_doctype": "Item",
			"invoice_ninja_endpoint": "products",
			"invoice_ninja_method": "get_products",
			"invoice_ninja_entity": "product",
			"include_params": None,
			"description": "Products and service items"
		},
		"Payment Entry": {
			"erpnext_doctype": "Payment Entry",
			"invoice_ninja_endpoint": "payments",
			"invoice_ninja_method": "get_payments",
			"invoice_ninja_entity": "payment",
			"include_params": "invoices,client",
			"description": "Payment entries and transactions"
		},
		"Invoice Ninja Task": {
			"erpnext_doctype": "Invoice Ninja Task",
			"invoice_ninja_endpoint": "tasks",
			"invoice_ninja_method": "get_tasks",
			"invoice_ninja_entity": "task",
			"include_params": "client,project",
			"description": "Tasks and time entries"
		}
	}

	@staticmethod
	def get_all_erpnext_doctypes():
		"""Get all supported ERPNext doctype names"""
		return list(EntityMapper.ENTITY_MAPPING.keys())

	@staticmethod
	def get_entity_config(erpnext_doctype):
		"""Get complete entity configuration for ERPNext doctype"""
		return EntityMapper.ENTITY_MAPPING.get(erpnext_doctype)

	@staticmethod
	def get_invoice_ninja_endpoint(erpnext_doctype):
		"""Get Invoice Ninja API endpoint for ERPNext doctype"""
		config = EntityMapper.get_entity_config(erpnext_doctype)
		return config.get("invoice_ninja_endpoint") if config else None

	@staticmethod
	def get_invoice_ninja_entity(erpnext_doctype):
		"""Get Invoice Ninja entity name for ERPNext doctype"""
		config = EntityMapper.get_entity_config(erpnext_doctype)
		return config.get("invoice_ninja_entity") if config else None

	@staticmethod
	def get_invoice_ninja_method(erpnext_doctype):
		"""Get Invoice Ninja client method name for ERPNext doctype"""
		config = EntityMapper.get_entity_config(erpnext_doctype)
		return config.get("invoice_ninja_method") if config else None

	@staticmethod
	def get_include_params(erpnext_doctype):
		"""Get Invoice Ninja API include parameters for ERPNext doctype"""
		config = EntityMapper.get_entity_config(erpnext_doctype)
		return config.get("include_params") if config else None

	@staticmethod
	def is_valid_erpnext_doctype(erpnext_doctype):
		"""Check if ERPNext doctype is supported"""
		return erpnext_doctype in EntityMapper.ENTITY_MAPPING

	@staticmethod
	def validate_entity_type(entity_type):
		"""
		Validate entity type and return standardized ERPNext doctype

		Args:
			entity_type: Entity type to validate

		Returns:
			tuple: (is_valid, standardized_doctype_or_error_message)
		"""
		if EntityMapper.is_valid_erpnext_doctype(entity_type):
			return True, entity_type

		valid_types = EntityMapper.get_all_erpnext_doctypes()
		error_msg = f'Record Type cannot be "{entity_type}". It should be one of {", ".join([f'"{t}"' for t in valid_types])}'
		return False, error_msg

	@staticmethod
	def get_legacy_entity_config():
		"""
		Get entity config in the format expected by SyncManager.ENTITY_CONFIG

		This provides backward compatibility for existing code that expects
		the old ENTITY_CONFIG structure.
		"""
		legacy_config = {}
		for doctype, mapping in EntityMapper.ENTITY_MAPPING.items():
			legacy_config[doctype] = {
				"invoice_ninja_endpoint": mapping["invoice_ninja_endpoint"],
				"invoice_ninja_method": mapping["invoice_ninja_method"],
				"erpnext_doctype": mapping["erpnext_doctype"],
				"include_params": mapping["include_params"]
			}
		return legacy_config
