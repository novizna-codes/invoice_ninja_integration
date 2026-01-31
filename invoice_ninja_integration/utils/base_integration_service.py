"""
Base Integration Service for Frappe Apps

This module provides a base class for creating third-party integration services
in Frappe apps. It establishes standard patterns for fetch and sync operations
with multi-company support that can be reused across different integration apps.

Example usage in other apps:
    from invoice_ninja_integration.utils.base_integration_service import BaseIntegrationService

    class ShopifyIntegrationService(BaseIntegrationService):
        SETTINGS_DOCTYPE = "Shopify Settings"
        ENTITY_CONFIG = {
            "Customer": {"shopify_endpoint": "customers", ...},
            "Sales Order": {"shopify_endpoint": "orders", ...},
        }
"""

import frappe
from abc import ABC, abstractmethod


class BaseIntegrationService(ABC):
	"""
	Base class for third-party integration services in Frappe apps

	Provides standard patterns for:
	- Multi-company mapping and context
	- Generic entity fetching operations
	- Bidirectional sync operations
	- Error handling and logging

	Subclasses must override:
	- SETTINGS_DOCTYPE: Name of the settings DocType
	- ENTITY_CONFIG: Dictionary mapping entity types to API configuration
	- _init_components(): Initialize service-specific components
	"""

	# Must be overridden by subclass
	SETTINGS_DOCTYPE = None
	ENTITY_CONFIG = {}

	def __init__(self):
		"""Initialize the integration service"""
		if not self.SETTINGS_DOCTYPE:
			raise NotImplementedError(
				"SETTINGS_DOCTYPE must be defined in subclass. "
				"Example: SETTINGS_DOCTYPE = 'Invoice Ninja Settings'"
			)

		if not self.ENTITY_CONFIG:
			frappe.log_error(
				"ENTITY_CONFIG is empty. Define entity mappings in subclass.",
				"Integration Service Warning"
			)

		# Load settings
		self.settings = frappe.get_single(self.SETTINGS_DOCTYPE)

		# Initialize service-specific components
		self._init_components()

	@abstractmethod
	def _init_components(self):
		"""
		Initialize required components for the integration service

		This method should initialize:
		- API client
		- Field mapper
		- Company mapper
		- Any other service-specific components

		Example:
			def _init_components(self):
				self.client = ShopifyClient()
				self.mapper = ShopifyFieldMapper()
				self.company_mapper = CompanyMapper()
		"""
		raise NotImplementedError("_init_components() must be implemented in subclass")

	def validate_entity_type(self, entity_type):
		"""
		Validate if entity type is supported

		Args:
			entity_type: Type of entity to validate

		Returns:
			tuple: (is_valid, error_message)
		"""
		if entity_type not in self.ENTITY_CONFIG:
			valid_types = list(self.ENTITY_CONFIG.keys())
			return False, f"Invalid entity type: {entity_type}. Valid types: {valid_types}"
		return True, None

	def is_integration_enabled(self):
		"""
		Check if integration is enabled in settings

		Returns:
			bool: True if enabled, False otherwise
		"""
		return getattr(self.settings, 'enabled', False)

	@abstractmethod
	def fetch_entities_for_mapped_companies(self, entity_type, page=1, per_page=100, filters=None):
		"""
		Generic method to fetch entities from third-party service for all mapped companies

		Args:
			entity_type: Type of entity (e.g., Customer, Sales Invoice)
			page: Page number for pagination
			per_page: Number of records per page
			filters: Optional filters to apply

		Returns:
			dict: {
				"success": bool,
				"companies": [
					{
						"erpnext_company": str,
						"third_party_company_id": str,
						"third_party_company_name": str,
						"entities": [...],
						"entity_count": int
					}
				],
				"total_entities": int,
				"entity_type": str,
				"message": str
			}
		"""
		raise NotImplementedError("fetch_entities_for_mapped_companies() must be implemented in subclass")

	@abstractmethod
	def fetch_entities_for_company(self, entity_type, erpnext_company=None,
									third_party_company_id=None, page=1, per_page=100, filters=None):
		"""
		Generic method to fetch entities from third-party service for a specific company

		Args:
			entity_type: Type of entity
			erpnext_company: ERPNext company name (optional)
			third_party_company_id: Third-party service company ID (optional)
			page: Page number for pagination
			per_page: Number of records per page
			filters: Optional filters to apply

		Returns:
			dict: {
				"success": bool,
				"erpnext_company": str,
				"third_party_company_id": str,
				"third_party_company_name": str,
				"entities": [...],
				"entity_count": int,
				"entity_type": str,
				"message": str
			}
		"""
		raise NotImplementedError("fetch_entities_for_company() must be implemented in subclass")

	@abstractmethod
	def fetch_entity_by_id(self, entity_type, entity_id, erpnext_company=None,
							third_party_company_id=None):
		"""
		Fetch a single entity by ID from third-party service

		Args:
			entity_type: Type of entity
			entity_id: Third-party service entity ID
			erpnext_company: ERPNext company name (optional)
			third_party_company_id: Third-party service company ID (optional)

		Returns:
			dict: {
				"success": bool,
				"entity": {...},
				"entity_type": str,
				"message": str
			}
		"""
		raise NotImplementedError("fetch_entity_by_id() must be implemented in subclass")

	def log_sync_success(self, doc, sync_direction, message):
		"""
		Log successful sync operation

		Args:
			doc: ERPNext document that was synced
			sync_direction: Direction of sync (e.g., "ERPNext to Third Party")
			message: Success message
		"""
		try:
			# Subclasses can override this to use custom logging DocType
			frappe.logger().info(f"Sync Success: {doc.doctype} {doc.name} - {message}")
		except Exception as e:
			frappe.log_error(f"Failed to log sync success: {str(e)}")

	def log_sync_error(self, doc, sync_direction, error_message, third_party_data=None):
		"""
		Log sync error

		Args:
			doc: ERPNext document (if available)
			sync_direction: Direction of sync
			error_message: Error message
			third_party_data: Third-party service data (optional)
		"""
		try:
			entity_name = doc.name if doc else third_party_data.get("id", "Unknown")
			entity_type = doc.doctype if doc else "Unknown"

			frappe.log_error(
				f"Sync Error: {entity_type} {entity_name}\n"
				f"Direction: {sync_direction}\n"
				f"Error: {error_message}",
				f"{self.SETTINGS_DOCTYPE} Sync Error"
			)
		except Exception as e:
			frappe.log_error(f"Failed to log sync error: {str(e)}")

	def get_entity_config(self, entity_type):
		"""
		Get configuration for a specific entity type

		Args:
			entity_type: Type of entity

		Returns:
			dict: Entity configuration or None if not found
		"""
		return self.ENTITY_CONFIG.get(entity_type)

	def get_supported_entity_types(self):
		"""
		Get list of supported entity types

		Returns:
			list: List of supported entity type names
		"""
		return list(self.ENTITY_CONFIG.keys())

	def validate_integration_setup(self):
		"""
		Validate that integration is properly set up

		Returns:
			tuple: (is_valid, error_message)
		"""
		if not self.is_integration_enabled():
			return False, f"{self.SETTINGS_DOCTYPE} is not enabled"

		# Subclasses can add additional validation
		return True, None

	def __repr__(self):
		"""String representation of the service"""
		return f"<{self.__class__.__name__} for {self.SETTINGS_DOCTYPE}>"

