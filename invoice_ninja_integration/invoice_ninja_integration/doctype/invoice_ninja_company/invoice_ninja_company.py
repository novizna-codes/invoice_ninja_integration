# Copyright (c) 2025, Novizna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InvoiceNinjaCompany(Document):
	def validate(self):
		"""Validate currency account mappings"""
		self.validate_currency_account_mappings()

	def validate_currency_account_mappings(self):
		"""Validate that receivable accounts support their mapped currencies"""
		if not self.currency_account_mappings:
			return

		# Get the ERPNext company this Invoice Ninja Company is mapped to
		settings = frappe.get_single("Invoice Ninja Settings")
		erpnext_company = None

		if settings.company_mappings:
			for company_mapping in settings.company_mappings:
				if company_mapping.invoice_ninja_company_id == self.company_id:
					erpnext_company = company_mapping.erpnext_company
					break

		# If no mapping found, skip validation (user hasn't set up company mapping yet)
		if not erpnext_company:
			return

		seen_currencies = set()
		default_count = 0

		for mapping in self.currency_account_mappings:
			# Check for duplicate currencies
			if mapping.currency in seen_currencies:
				frappe.throw(f"Currency {mapping.currency} is mapped multiple times. Each currency should be mapped only once.")
			seen_currencies.add(mapping.currency)

			# Count defaults
			if mapping.is_default:
				default_count += 1

			# Validate account belongs to the mapped ERPNext company
			account_company = frappe.db.get_value(
				"Account",
				mapping.receivable_account,
				"company"
			)

			if account_company != erpnext_company:
				frappe.throw(
					f"Account {mapping.receivable_account} belongs to company {account_company}, "
					f"but this Invoice Ninja Company is mapped to {erpnext_company}"
				)

			# Validate account is a receivable account
			account_type = frappe.db.get_value(
				"Account",
				mapping.receivable_account,
				"account_type"
			)

			if account_type != "Receivable":
				frappe.throw(
					f"Account {mapping.receivable_account} is not a Receivable account. "
					f"Only Receivable accounts can be used for invoice debit_to field."
				)

			# Validate account currency matches mapping currency
			account_currency = frappe.db.get_value(
				"Account",
				mapping.receivable_account,
				"account_currency"
			)

			if account_currency and account_currency != mapping.currency:
				frappe.throw(
					f"Account {mapping.receivable_account} has currency {account_currency}, "
					f"but is mapped to {mapping.currency}. Account currency must match the mapping."
				)

		# Warn if more than one default
		if default_count > 1:
			frappe.msgprint(
				"Multiple default currency mappings found. Only one should be marked as default.",
				indicator="orange"
			)
