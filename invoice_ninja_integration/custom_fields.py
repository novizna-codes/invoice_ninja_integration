# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_custom_fields():
	"""Create custom fields for task-based invoice line items"""

	custom_fields = {
		"Sales Invoice Item": [
			{
				"fieldname": "invoice_ninja_task_id",
				"fieldtype": "Data",
				"label": "Invoice Ninja Task ID",
				"insert_after": "item_code",
				"read_only": 1,
				"hidden": 1,
				"no_copy": 1
			},
			{
				"fieldname": "custom_is_task_based",
				"fieldtype": "Check",
				"label": "Is Task Based",
				"insert_after": "invoice_ninja_task_id",
				"read_only": 1,
				"default": "0",
				"no_copy": 1
			}
		],
		"Sales Invoice": [
			{
				"fieldname": "invoice_ninja_tasks",
				"fieldtype": "Small Text",
				"label": "Invoice Ninja Tasks",
				"insert_after": "customer",
				"read_only": 1,
				"description": "Task IDs from Invoice Ninja that are billed in this invoice",
				"no_copy": 1
			}
		]
	}

	create_custom_fields(custom_fields, update=True)
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

