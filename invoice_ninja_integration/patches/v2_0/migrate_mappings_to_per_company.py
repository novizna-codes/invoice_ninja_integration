import frappe

def execute():
	"""Migrate global mappings to per-company mappings"""

	# Reload DocTypes to ensure new fields are available
	frappe.reload_doctype("Invoice Ninja Company")
	frappe.reload_doctype("Invoice Ninja Settings")
	frappe.reload_doctype("Invoice Ninja Customer Group Mapping")
	frappe.reload_doctype("Invoice Ninja Item Group Mapping")
	frappe.reload_doctype("Invoice Ninja Tax Template Mapping")

	# Check if the database table has the new child table columns
	table_name = "tabInvoice Ninja Company"
	if not frappe.db.table_exists(table_name):
		print(f"Table {table_name} does not exist. Skipping migration.")
		return

	# Verify the parent DocType has been synced with new fields
	meta = frappe.get_meta("Invoice Ninja Company")
	has_mappings = any(
		field.fieldname in ['customer_group_mappings', 'tax_template_mappings']
		for field in meta.fields
	)

	if not has_mappings:
		print("Invoice Ninja Company DocType not yet synced with new mapping fields. Will retry on next migrate.")
		return

	settings = frappe.get_single("Invoice Ninja Settings")
	companies = frappe.get_all("Invoice Ninja Company", filters={"enabled": 1}, fields=["name"])

	if not companies:
		print("No enabled Invoice Ninja companies found. Skipping migration.")
		return

	migrated_count = 0
	for company in companies:
		try:
			company_doc = frappe.get_doc("Invoice Ninja Company", company.name)

			# Copy customer group mappings
			if settings.customer_group_mappings and not company_doc.customer_group_mappings:
				for mapping in settings.customer_group_mappings:
					company_doc.append("customer_group_mappings", {
						"customer_group": mapping.customer_group,
						"invoice_ninja_customer_group": mapping.invoice_ninja_customer_group
					})

			# Copy tax template mappings
			if settings.tax_template_mappings and not company_doc.tax_template_mappings:
				for mapping in settings.tax_template_mappings:
					company_doc.append("tax_template_mappings", {
						"tax_template": mapping.tax_template,
						"invoice_ninja_tax_rate": mapping.invoice_ninja_tax_rate
					})

			# Copy default tax template
			if settings.default_tax_template and not company_doc.default_tax_template:
				company_doc.default_tax_template = settings.default_tax_template

			company_doc.save(ignore_permissions=True)
			migrated_count += 1

		except Exception as e:
			print(f"Error migrating company {company.name}: {str(e)}")
			frappe.log_error(f"Migration error for {company.name}: {str(e)}", "Mapping Migration Error")

	frappe.db.commit()
	print(f"Successfully migrated mappings to {migrated_count} out of {len(companies)} Invoice Ninja companies")

