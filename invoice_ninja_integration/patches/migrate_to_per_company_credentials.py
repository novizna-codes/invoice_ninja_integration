import frappe
from frappe import _


def execute():
	"""
	Migrate from global Invoice Ninja credentials to per-company credentials

	This migration:
	1. Gets global credentials from Settings (if they exist)
	2. For each Company Mapping, updates the linked Invoice Ninja Company with those credentials
	3. Updates all synced entities to set invoice_ninja_company field
	4. KEEPS global credentials in Settings (they become master credentials for discovery)
	"""

	frappe.log_error("Starting migration to per-company credentials", "Invoice Ninja Migration")

	try:
		# Get settings
		settings = frappe.get_single("Invoice Ninja Settings")

		# Check if global credentials exist
		global_url = getattr(settings, 'invoice_ninja_url', None)
		global_token = None

		if global_url:
			try:
				global_token = settings.get_password("api_token")
			except Exception:
				pass

		if not global_url or not global_token:
			frappe.log_error(
				"No global credentials found. Skipping credential migration.",
				"Invoice Ninja Migration"
			)
			# Still need to migrate entity references if they exist
			global_url = None
			global_token = None

		# Get all company mappings
		if not hasattr(settings, 'company_mappings') or not settings.company_mappings:
			frappe.log_error(
				"No company mappings found. Nothing to migrate.",
				"Invoice Ninja Migration"
			)
			return

		migrated_companies = []

		# For each mapping, update the Invoice Ninja Company doc
		for mapping in settings.company_mappings:
			try:
				# Get the Invoice Ninja Company doc
				in_company_doc_name = frappe.get_value(
					"Invoice Ninja Company",
					{"company_id": mapping.invoice_ninja_company_id},
					"name"
				)

				if not in_company_doc_name:
					frappe.log_error(
						f"Invoice Ninja Company not found for company_id {mapping.invoice_ninja_company_id}",
						"Invoice Ninja Migration"
					)
					continue

				# Update the doc with credentials
				in_company_doc = frappe.get_doc("Invoice Ninja Company", in_company_doc_name)

				# Only set credentials if they don't already exist
				if not in_company_doc.get("invoice_ninja_url") and global_url:
					in_company_doc.invoice_ninja_url = global_url
					in_company_doc.set_value("api_token", global_token)
					in_company_doc.enabled = 1
					in_company_doc.connection_status = "Not Tested"
					in_company_doc.save(ignore_permissions=True)

					migrated_companies.append({
						"company_doc": in_company_doc_name,
						"erpnext_company": mapping.erpnext_company,
						"invoice_ninja_company_id": mapping.invoice_ninja_company_id
					})

					frappe.log_error(
						f"Migrated credentials to {in_company_doc_name} for {mapping.erpnext_company}",
						"Invoice Ninja Migration Success"
					)

			except Exception as e:
				frappe.log_error(
					f"Error migrating company {mapping.invoice_ninja_company_id}: {str(e)}",
					"Invoice Ninja Migration Error"
				)
				continue

		# Update all synced entities with invoice_ninja_company reference
		update_synced_entities(migrated_companies)

		frappe.db.commit()

		# Note: We intentionally keep the global credentials in Settings
		# They are now used as "master credentials" for discovering companies
		frappe.log_error(
			f"Migration complete! Migrated {len(migrated_companies)} companies. "
			"Global credentials kept in Settings for company discovery.",
			"Invoice Ninja Migration Complete"
		)

	except Exception as e:
		frappe.log_error(
			f"Migration failed: {str(e)}",
			"Invoice Ninja Migration Error"
		)
		frappe.db.rollback()


def update_synced_entities(migrated_companies):
	"""
	Update all synced entities to set invoice_ninja_company field
	based on their ERPNext company
	"""
	entity_types = [
		"Customer",
		"Sales Invoice",
		"Quotation",
		"Item",
		"Payment Entry",
		"Contact"
	]

	for entity_type in entity_types:
		try:
			# Get all entities that have invoice_ninja_id but no invoice_ninja_company
			entities = frappe.get_all(
				entity_type,
				filters={
					"invoice_ninja_id": ["!=", ""],
					"invoice_ninja_company": ["is", "not set"]
				},
				fields=["name", "company"] if frappe.get_meta(entity_type).has_field("company") else ["name"]
			)

			updated_count = 0

			for entity in entities:
				try:
					# Find the appropriate Invoice Ninja Company based on ERPNext company
					if hasattr(entity, 'company') and entity.company:
						# Find matching migrated company
						matching = next(
							(mc for mc in migrated_companies if mc["erpnext_company"] == entity.company),
							None
						)

						if matching:
							frappe.db.set_value(
								entity_type,
								entity.name,
								"invoice_ninja_company",
								matching["company_doc"],
								update_modified=False
							)
							updated_count += 1
					else:
						# For entities without company field (like Contact),
						# try to use the first migrated company (default)
						if migrated_companies:
							frappe.db.set_value(
								entity_type,
								entity.name,
								"invoice_ninja_company",
								migrated_companies[0]["company_doc"],
								update_modified=False
							)
							updated_count += 1

				except Exception as e:
					frappe.log_error(
						f"Error updating {entity_type} {entity.name}: {str(e)}",
						"Invoice Ninja Entity Migration Error"
					)
					continue

			if updated_count > 0:
				frappe.log_error(
					f"Updated {updated_count} {entity_type} records with invoice_ninja_company",
					"Invoice Ninja Migration Success"
				)

		except Exception as e:
			frappe.log_error(
				f"Error processing {entity_type}: {str(e)}",
				"Invoice Ninja Entity Migration Error"
			)
			continue

