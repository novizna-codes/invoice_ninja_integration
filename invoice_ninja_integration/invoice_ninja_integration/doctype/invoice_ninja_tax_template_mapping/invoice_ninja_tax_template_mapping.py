# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InvoiceNinjaTaxTemplateMapping(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		invoice_ninja_tax_name: DF.Data | None
		invoice_ninja_tax_rate: DF.Link | None
		invoice_ninja_tax_rate_percent: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		tax_template: DF.Link
		tax_template_title: DF.Data | None
	# end: auto-generated types

	pass

