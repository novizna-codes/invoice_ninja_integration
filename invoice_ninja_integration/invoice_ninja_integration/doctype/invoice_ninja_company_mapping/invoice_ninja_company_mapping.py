# Copyright (c) 2025, Novizna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InvoiceNinjaCompanyMapping(Document):
	def validate(self):
		"""Validate company mapping"""
		self.validate_unique_mapping()
		self.validate_default_mapping()
	
	def validate_unique_mapping(self):
		"""Ensure unique mapping between ERPNext and Invoice Ninja companies"""
		# Check if ERPNext company is already mapped
		existing_mapping = frappe.db.get_value(
			"Invoice Ninja Company Mapping",
			{
				"erpnext_company": self.erpnext_company,
				"name": ("!=", self.name)
			},
			"name"
		)
		
		if existing_mapping:
			frappe.throw(f"ERPNext Company '{self.erpnext_company}' is already mapped to another Invoice Ninja company")
		
		# Check if Invoice Ninja company is already mapped
		existing_in_mapping = frappe.db.get_value(
			"Invoice Ninja Company Mapping", 
			{
				"invoice_ninja_company_id": self.invoice_ninja_company_id,
				"name": ("!=", self.name)
			},
			"name"
		)
		
		if existing_in_mapping:
			frappe.throw(f"Invoice Ninja Company ID '{self.invoice_ninja_company_id}' is already mapped to another ERPNext company")
	
	def validate_default_mapping(self):
		"""Ensure only one default mapping exists"""
		if self.is_default:
			# Remove default flag from other mappings
			frappe.db.sql("""
				UPDATE `tabInvoice Ninja Company Mapping` 
				SET is_default = 0 
				WHERE name != %s AND parent = %s
			""", (self.name, self.parent))
