// Copyright (c) 2025, Novizna and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Ninja Company Mapping', {
	erpnext_company: function(frm, cdt, cdn) {
		// Auto-populate company name when ERPNext company is selected
		var row = locals[cdt][cdn];
		if (row.erpnext_company && !row.invoice_ninja_company_name) {
			row.invoice_ninja_company_name = row.erpnext_company;
			refresh_field("invoice_ninja_company_name", cdn, "company_mappings");
		}
	},

	is_default: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.is_default) {
			// Uncheck other default mappings
			frm.doc.company_mappings.forEach(function(mapping) {
				if (mapping.name !== row.name) {
					mapping.is_default = 0;
				}
			});
			refresh_field("company_mappings");
		}
	},

	invoice_ninja_company_id: function(frm, cdt, cdn) {
		// Auto-populate company name when company ID is selected
		let row = locals[cdt][cdn];
		if (row.invoice_ninja_company_id && frm._ninja_companies) {
			// Find the selected company from fetched data
			let company_id = row.invoice_ninja_company_id.split(':')[0]; // Get ID part
			let selected_company = frm._ninja_companies.find(c => c.id == company_id);
			if (selected_company) {
				row.invoice_ninja_company_name = selected_company.name;
				refresh_field("invoice_ninja_company_name", cdn, "company_mappings");
			}
		}
	}
});
