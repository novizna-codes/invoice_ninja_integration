# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def setup_custom_fields():
	"""
	Custom fields are now managed via JSON files in:
	- invoice_ninja_integration/custom/sales_invoice.json
	- invoice_ninja_integration/custom/sales_invoice_item.json

	This function is kept for backward compatibility but does nothing.
	Fields are automatically synced from JSON files during migration.
	"""
	pass


def setup_property_setters():
	"""Create property setters to increase item_name field length to 1000 characters"""

	property_setters = [
		{
			"doctype": "Sales Invoice Item",
			"fieldname": "item_name",
			"property": "length",
			"value": "1000",
			"property_type": "Int"
		},
		{
			"doctype": "Quotation Item",
			"fieldname": "item_name",
			"property": "length",
			"value": "1000",
			"property_type": "Int"
		},
		{
			"doctype": "Item",
			"fieldname": "item_name",
			"property": "length",
			"value": "1000",
			"property_type": "Int"
		}
	]

	for prop in property_setters:
		try:
			make_property_setter(
				doctype=prop["doctype"],
				fieldname=prop["fieldname"],
				property=prop["property"],
				value=prop["value"],
				property_type=prop["property_type"],
				validate_fields_for_doctype=False
			)
			print(f"Set {prop['property']} = {prop['value']} for {prop['doctype']}.{prop['fieldname']}")
		except Exception as e:
			frappe.log_error(
				f"Error creating property setter for {prop['doctype']}.{prop['fieldname']}: {str(e)}",
				"Property Setter Error"
			)

	frappe.db.commit()


def remove_custom_fields():
	"""Remove custom fields (for uninstall)"""

	custom_fields_to_remove = [
		("Sales Invoice Item", "invoice_ninja_task_id"),
		("Sales Invoice Item", "custom_is_task_based"),
		("Sales Invoice", "invoice_ninja_tasks")
	]

	for dt, fieldname in custom_fields_to_remove:
		frappe.delete_doc_if_exists("Custom Field", f"{dt}-{fieldname}")

	frappe.db.commit()

