import frappe
import os
import json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_migrate():
	"""Install customizations after migration"""
	install_customizations()


def install_customizations():
	"""Install custom fields and property setters from custom folder"""
	customizations_path = frappe.get_app_path("invoice_ninja_integration", "invoice_ninja_integration", "custom")

	if not os.path.exists(customizations_path):
		return

	# Get list of customization files
	customization_files = [f for f in os.listdir(customizations_path) if f.endswith('.json')]

	for filename in customization_files:
		file_path = os.path.join(customizations_path, filename)

		try:
			with open(file_path, 'r') as f:
				customization_data = json.load(f)

			install_customization(customization_data)
			frappe.db.commit()

		except Exception as e:
			frappe.log_error(f"Error installing customization from {filename}: {str(e)}", "Customization Install Error")


def install_customization(customization_data):
	"""Install a single customization"""
	doctype = customization_data.get('doctype')

	if not doctype:
		return

	# Install custom fields
	custom_fields = customization_data.get('custom_fields', [])
	if custom_fields:
		# Convert to the format expected by create_custom_fields
		custom_fields_dict = {doctype: []}

		for field in custom_fields:
			custom_fields_dict[doctype].append({
				'fieldname': field.get('fieldname'),
				'label': field.get('label'),
				'fieldtype': field.get('fieldtype'),
				'options': field.get('options'),
				'insert_after': field.get('insert_after'),
				'description': field.get('description'),
				'read_only': field.get('read_only', 0),
				'hidden': field.get('hidden', 0),
				'print_hide': field.get('print_hide', 0),
				'no_copy': field.get('no_copy', 0),
				'unique': field.get('unique', 0),
				'reqd': field.get('reqd', 0),
				'in_list_view': field.get('in_list_view', 0),
				'in_standard_filter': field.get('in_standard_filter', 0),
				'search_index': field.get('search_index', 0),
				'permlevel': field.get('permlevel', 0)
			})

		create_custom_fields(custom_fields_dict, ignore_validate=True)

	# Install property setters
	property_setters = customization_data.get('property_setters', [])
	for prop in property_setters:
		make_property_setter(
			doctype=prop.get('doc_type'),
			fieldname=prop.get('field_name'),
			property=prop.get('property'),
			value=prop.get('value'),
			property_type=prop.get('property_type')
		)

	print(f"Installed customization for {doctype}")


def uninstall_customizations():
	"""Remove all Invoice Ninja custom fields"""
	custom_fields_to_remove = [
		# Customer fields
		"Customer-invoice_ninja_id",
		"Customer-invoice_ninja_sync_status",
		"Customer-invoice_ninja_last_sync",

		# Sales Invoice fields
		"Sales Invoice-invoice_ninja_id",
		"Sales Invoice-invoice_ninja_sync_status",
		"Sales Invoice-invoice_ninja_last_sync",
		"Sales Invoice-invoice_ninja_number",

		# Quotation fields
		"Quotation-invoice_ninja_id",
		"Quotation-invoice_ninja_sync_status",
		"Quotation-invoice_ninja_last_sync",
		"Quotation-invoice_ninja_number",

		# Item fields
		"Item-invoice_ninja_id",
		"Item-invoice_ninja_sync_status",
		"Item-invoice_ninja_last_sync",

		# Payment Entry fields
		"Payment Entry-invoice_ninja_id",
		"Payment Entry-invoice_ninja_sync_status",
		"Payment Entry-invoice_ninja_last_sync",

		# File fields
		"File-invoice_ninja_id",
		"File-invoice_ninja_sync_status",
		"File-invoice_ninja_last_sync"
	]

	for field_name in custom_fields_to_remove:
		try:
			if frappe.db.exists("Custom Field", field_name):
				frappe.delete_doc("Custom Field", field_name)
				print(f"Removed custom field: {field_name}")
		except Exception as e:
			frappe.log_error(f"Error removing custom field {field_name}: {str(e)}", "Customization Removal Error")

	frappe.db.commit()
	print("Invoice Ninja customizations removed successfully")
