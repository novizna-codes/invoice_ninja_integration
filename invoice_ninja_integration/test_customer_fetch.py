#!/usr/bin/env python3
"""
Test script for customer fetch API endpoints
Run from bench: bench --site [site-name] execute invoice_ninja_integration.test_customer_fetch.test_fetch_customers
"""

import frappe
import json


def test_fetch_customers_all_companies():
	"""Test fetching customers from all mapped companies using centralized SyncManager"""
	print("\n" + "="*80)
	print("TEST: Fetching Customers from All Mapped Companies (via SyncManager)")
	print("="*80)

	try:
		# Test using API endpoint (which now uses SyncManager internally)
		result = frappe.call(
			"invoice_ninja_integration.api.get_customers_for_mapped_companies",
			page=1,
			per_page=10  # Limit to 10 for testing
		)

		print(f"\nSuccess: {result.get('success')}")
		print(f"Total Customers: {result.get('total_customers', 0)}")
		print(f"Number of Companies: {len(result.get('companies', []))}")

		if result.get("success"):
			print("\n" + "-"*80)
			for company_data in result["companies"]:
				print(f"\nERPNext Company: {company_data['erpnext_company']}")
				print(f"Invoice Ninja Company: {company_data['invoice_ninja_company_name']}")
				print(f"Company ID: {company_data['invoice_ninja_company_id']}")
				print(f"Is Default: {company_data['is_default']}")
				print(f"Customer Count: {company_data['customer_count']}")

				if company_data['customers']:
					print("\nFirst 3 Customers:")
					for i, customer in enumerate(company_data['customers'][:3], 1):
						print(f"  {i}. {customer.get('name', 'N/A')} (ID: {customer.get('id')})")

						# Display contacts if available
						contacts = customer.get('contacts', [])
						if contacts:
							primary_contact = next((c for c in contacts if c.get('is_primary')), contacts[0] if contacts else None)
							if primary_contact:
								email = primary_contact.get('email', 'N/A')
								phone = primary_contact.get('phone', 'N/A')
								print(f"     Email: {email}, Phone: {phone}")
				else:
					print("\n  No customers found for this company")
		else:
			print(f"\nError: {result.get('message')}")

	except Exception as e:
		print(f"\nException occurred: {str(e)}")
		import traceback
		traceback.print_exc()


def test_fetch_customers_single_company(company_name=None):
	"""Test fetching customers from a single company using centralized SyncManager"""
	print("\n" + "="*80)
	print("TEST: Fetching Customers from Single Company (via SyncManager)")
	print("="*80)

	# Get first mapped company if no company name provided
	if not company_name:
		try:
			settings = frappe.get_single("Invoice Ninja Settings")
			if settings.company_mappings:
				company_name = settings.company_mappings[0].erpnext_company
				print(f"\nUsing first mapped company: {company_name}")
			else:
				print("\nNo company mappings found. Skipping test.")
				return
		except Exception as e:
			print(f"\nError getting company mappings: {str(e)}")
			return

	try:
		result = frappe.call(
			"invoice_ninja_integration.api.get_customers_for_company",
			erpnext_company=company_name,
			page=1,
			per_page=10  # Limit to 10 for testing
		)

		print(f"\nSuccess: {result.get('success')}")

		if result.get("success"):
			print(f"ERPNext Company: {result.get('erpnext_company')}")
			print(f"Invoice Ninja Company: {result.get('invoice_ninja_company_name')}")
			print(f"Company ID: {result.get('invoice_ninja_company_id')}")
			print(f"Customer Count: {result.get('customer_count')}")

			customers = result.get('customers', [])
			if customers:
				print("\nFirst 5 Customers:")
				for i, customer in enumerate(customers[:5], 1):
					print(f"\n  {i}. {customer.get('name', 'N/A')}")
					print(f"     ID: {customer.get('id')}")
					print(f"     Balance: ${customer.get('balance', 0)}")
					print(f"     Paid to Date: ${customer.get('paid_to_date', 0)}")

					# Display contacts
					contacts = customer.get('contacts', [])
					if contacts:
						print(f"     Contacts:")
						for contact in contacts[:2]:  # Show first 2 contacts
							name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
							email = contact.get('email', 'N/A')
							phone = contact.get('phone', 'N/A')
							is_primary = " (Primary)" if contact.get('is_primary') else ""
							print(f"       - {name}{is_primary}")
							print(f"         Email: {email}, Phone: {phone}")
			else:
				print("\n  No customers found for this company")
		else:
			print(f"\nError: {result.get('message')}")

	except Exception as e:
		print(f"\nException occurred: {str(e)}")
		import traceback
		traceback.print_exc()


def test_company_mappings():
	"""Test and display current company mappings"""
	print("\n" + "="*80)
	print("CURRENT COMPANY MAPPINGS")
	print("="*80)

	try:
		from invoice_ninja_integration.utils.company_mapper import CompanyMapper

		company_mapper = CompanyMapper()
		mappings = company_mapper.get_all_mappings()

		if mappings:
			print(f"\nFound {len(mappings)} company mapping(s):")
			print("-"*80)

			for i, mapping in enumerate(mappings, 1):
				print(f"\n{i}. ERPNext Company: {mapping['erpnext_company']}")
				print(f"   Invoice Ninja Company: {mapping['invoice_ninja_company_name']}")
				print(f"   Company ID: {mapping['invoice_ninja_company_id']}")
				print(f"   Is Default: {mapping.get('is_default', False)}")
		else:
			print("\nNo company mappings found!")
			print("Please configure company mappings in Invoice Ninja Settings.")

	except Exception as e:
		print(f"\nException occurred: {str(e)}")
		import traceback
		traceback.print_exc()


def test_generic_fetch_entities():
	"""Test the generic fetch_entities endpoint"""
	print("\n" + "="*80)
	print("TEST: Generic fetch_entities Endpoint")
	print("="*80)

	try:
		# Test 1: Fetch customers using generic endpoint
		print("\n--- Test 1: Fetch Customers (all companies) ---")
		result = frappe.call(
			"invoice_ninja_integration.api.fetch_entities",
			entity_type="Customer",
			scope="all_companies",
			per_page=5
		)

		if result.get("success"):
			print(f"Success! Total entities: {result.get('total_entities', 0)}")
			print(f"Companies: {len(result.get('companies', []))}")
		else:
			print(f"Error: {result.get('message')}")

		# Test 2: Fetch invoices for single company
		print("\n--- Test 2: Fetch Invoices (single company) ---")
		settings = frappe.get_single("Invoice Ninja Settings")
		if settings.company_mappings:
			company_name = settings.company_mappings[0].erpnext_company
			result = frappe.call(
				"invoice_ninja_integration.api.fetch_entities",
				entity_type="Sales Invoice",
				scope="single_company",
				company_identifier=company_name,
				per_page=5
			)

			if result.get("success"):
				print(f"Success! Entity count: {result.get('entity_count', 0)}")
				print(f"Company: {result.get('invoice_ninja_company_name')}")
			else:
				print(f"Error: {result.get('message')}")
		else:
			print("No company mappings found. Skipping test.")

	except Exception as e:
		print(f"\nException occurred: {str(e)}")
		import traceback
		traceback.print_exc()


def run_all_tests():
	"""Run all test functions"""
	print("\n" + "="*80)
	print("INVOICE NINJA CENTRALIZED SERVICE TESTS")
	print("="*80)

	# Test 1: Display company mappings
	test_company_mappings()

	# Test 2: Fetch customers from all companies
	test_fetch_customers_all_companies()

	# Test 3: Fetch customers from single company
	test_fetch_customers_single_company()

	# Test 4: Generic fetch entities endpoint
	test_generic_fetch_entities()

	print("\n" + "="*80)
	print("ALL TESTS COMPLETED")
	print("="*80 + "\n")


# Main execution
if __name__ == "__main__":
	run_all_tests()


# Frappe bench compatible function
def test_fetch_customers():
	"""
	Main test function that can be called from bench
	Usage: bench --site [site-name] execute invoice_ninja_integration.test_customer_fetch.test_fetch_customers
	"""
	run_all_tests()

