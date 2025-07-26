// Copyright (c) 2025, Novizna and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Ninja Sync Logs', {
	refresh: function(frm) {
		// Add custom buttons based on status
		if (frm.doc.status === 'Failed' && frm.doc.record_type && frm.doc.record_id) {
			frm.add_custom_button(__('Retry Sync'), function() {
				frappe.call({
					method: 'invoice_ninja_integration.page.invoice_ninja_sync_dashboard.invoice_ninja_sync_dashboard.manual_sync',
					args: {
						sync_type: frm.doc.record_type,
						sync_direction: frm.doc.sync_direction,
						record_id: frm.doc.record_id
					},
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.msgprint(__('Retry sync has been queued successfully'));
						} else {
							frappe.msgprint(__('Error: ') + (r.message.error || 'Unknown error'));
						}
					}
				});
			});
		}

		// Color coding based on status
		if (frm.doc.status === 'Success') {
			frm.dashboard.set_headline_alert(__('Sync completed successfully'), 'green');
		} else if (frm.doc.status === 'Failed') {
			frm.dashboard.set_headline_alert(__('Sync failed'), 'red');
		} else if (frm.doc.status === 'In Progress') {
			frm.dashboard.set_headline_alert(__('Sync in progress'), 'blue');
		}
	}
});
