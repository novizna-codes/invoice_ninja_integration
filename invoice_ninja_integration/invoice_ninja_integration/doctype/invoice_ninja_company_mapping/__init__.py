# Copyright (c) 2025, Novizna and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InvoiceNinjaCompanyMapping(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		enabled: DF.Check
		erpnext_company: DF.Link
		invoice_ninja_company_id: DF.Data
		invoice_ninja_company_name: DF.Data
		is_default: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
