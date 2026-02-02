// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Ninja Task', {
	refresh: function(frm) {
		if (!frm.doc.__islocal && frm.doc.status !== 'Invoiced') {
			frm.add_custom_button(__('Convert to Timesheet'), function() {
				frappe.call({
					method: 'convert_to_timesheet',
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							frappe.msgprint(__('Timesheet {0} created', [r.message]));
							frappe.set_route('Form', 'Timesheet', r.message);
						}
					}
				});
			});
		}
	}
});

