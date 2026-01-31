// Copyright (c) 2026, Novizna and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Ninja Company', {
	refresh: function(frm) {
		// Show warning if no token
		if (!frm.doc.api_token && !frm.is_new()) {
			frm.dashboard.add_comment(
				__('API Token Required: This company cannot sync until you set an API token.'),
				'red',
				true
			);
		}

		// Add test connection button only if token exists
		if (!frm.is_new() && frm.doc.api_token) {
			frm.add_custom_button(__('Test Connection'), function() {
				test_connection(frm);
			});
		}

		// Show connection status with color
		if (frm.doc.connection_status) {
			set_connection_status_indicator(frm);
		}

		// Add sync actions dropdown if company is enabled
		if (!frm.is_new() && frm.doc.enabled && frm.doc.api_token) {
			frm.add_custom_button(__('Sync Customers'), function() {
				sync_entity(frm, 'Customer');
			}, __('Sync Actions'));

			frm.add_custom_button(__('Sync Invoices'), function() {
				sync_entity(frm, 'Sales Invoice');
			}, __('Sync Actions'));

			frm.add_custom_button(__('Sync Quotations'), function() {
				sync_entity(frm, 'Quotation');
			}, __('Sync Actions'));

			frm.add_custom_button(__('Sync Items'), function() {
				sync_entity(frm, 'Item');
			}, __('Sync Actions'));

			frm.add_custom_button(__('Sync Payments'), function() {
				sync_entity(frm, 'Payment Entry');
			}, __('Sync Actions'));

			frm.add_custom_button(__('Sync All'), function() {
				sync_all_entities(frm);
			}, __('Sync Actions'));
		}

		// Add button to view sync logs
		if (!frm.is_new()) {
			frm.add_custom_button(__('View Sync Logs'), function() {
				view_sync_logs(frm);
			});
		}

		// Show sync statistics dashboard
		if (!frm.is_new() && frm.doc.enabled) {
			show_sync_statistics_dashboard(frm);
		}
	},

	invoice_ninja_url: function(frm) {
		// Validate URL format
		if (frm.doc.invoice_ninja_url) {
			const url = frm.doc.invoice_ninja_url.trim();
			if (!url.startsWith('http://') && !url.startsWith('https://')) {
				frappe.msgprint({
					title: __('Invalid URL'),
					indicator: 'red',
					message: __('Invoice Ninja URL must start with http:// or https://')
				});
			}
		}
	},

	api_token: function(frm) {
		// Clear connection status when token changes
		if (frm.doc.connection_status !== 'Not Tested') {
			frm.set_value('connection_status', 'Not Tested');
		}

		// Enable company when token is set
		if (frm.doc.api_token && !frm.doc.enabled) {
			frm.set_value('enabled', 1);
		}
	}
});

function test_connection(frm) {
	if (!frm.doc.invoice_ninja_url || !frm.doc.api_token) {
		frappe.msgprint({
			title: __('Missing Credentials'),
			indicator: 'red',
			message: __('Please enter Invoice Ninja URL and API Token before testing connection.')
		});
		return;
	}

	frappe.call({
		method: 'invoice_ninja_integration.api.test_invoice_ninja_company_connection',
		args: {
			invoice_ninja_company: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Testing connection...'),
		callback: function(r) {
			if (r.message && r.message.success) {
				frm.set_value('connection_status', 'Connected');
				frappe.show_alert({
					message: __('Connection successful!'),
					indicator: 'green'
				});
			} else {
				frm.set_value('connection_status', 'Failed');
				frappe.show_alert({
					message: __('Connection failed: ') + (r.message.message || 'Unknown error'),
					indicator: 'red'
				});
			}
			frm.save();
		},
		error: function(r) {
			frm.set_value('connection_status', 'Failed');
			frappe.show_alert({
				message: __('Connection test failed. Please check your settings.'),
				indicator: 'red'
			});
			frm.save();
		}
	});
}

function set_connection_status_indicator(frm) {
	const status = frm.doc.connection_status;
	const field = frm.fields_dict.connection_status;

	if (field && field.$wrapper) {
		field.$wrapper.find('.like-disabled-input').removeClass('green orange red');

		if (status === 'Connected') {
			field.$wrapper.find('.like-disabled-input').addClass('green');
		} else if (status === 'Not Tested') {
			field.$wrapper.find('.like-disabled-input').addClass('orange');
		} else if (status === 'Failed') {
			field.$wrapper.find('.like-disabled-input').addClass('red');
		}
	}
}

function sync_entity(frm, entity_type) {
	frappe.confirm(
		__('Sync {0} from Invoice Ninja for company {1}?', [entity_type, frm.doc.company_name]),
		function() {
			frappe.call({
				method: 'invoice_ninja_integration.api.sync_company_entities',
				args: {
					invoice_ninja_company: frm.doc.name,
					entity_type: entity_type,
					limit: 100
				},
				freeze: true,
				freeze_message: __('Syncing {0}...', [entity_type]),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('Synced {0} {1} records',
								[r.message.synced_count || r.message.total_fetched || 0, entity_type]),
							indicator: 'green'
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('Sync Failed'),
							indicator: 'red',
							message: r.message.message || __('Unknown error')
						});
					}
				}
			});
		}
	);
}

function sync_all_entities(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Sync All Entities'),
		fields: [
			{
				label: __('Select Entities to Sync'),
				fieldname: 'entities',
				fieldtype: 'MultiCheck',
				options: [
					{label: __('Customers'), value: 'Customer', checked: 1},
					{label: __('Invoices'), value: 'Sales Invoice', checked: 1},
					{label: __('Quotations'), value: 'Quotation', checked: 1},
					{label: __('Items'), value: 'Item', checked: 1},
					{label: __('Payments'), value: 'Payment Entry', checked: 1}
				]
			},
			{
				label: __('Records per Entity'),
				fieldname: 'limit',
				fieldtype: 'Int',
				default: 100
			}
		],
		primary_action_label: __('Start Sync'),
		primary_action: function(values) {
			d.hide();
			frappe.call({
				method: 'invoice_ninja_integration.api.sync_company_all_entities',
				args: {
					invoice_ninja_company: frm.doc.name,
					entity_types: values.entities,
					limit: values.limit
				},
				freeze: true,
				freeze_message: __('Syncing all entities...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __('Sync Complete'),
							indicator: 'green',
							message: __('Synced {0} total records', [r.message.total_synced])
						});
						frm.reload_doc();
					}
				}
			});
		}
	});
	d.show();
}

function view_sync_logs(frm) {
	frappe.set_route('List', 'Invoice Ninja Sync Logs', {
		'invoice_ninja_company': frm.doc.name
	});
}

function show_sync_statistics_dashboard(frm) {
	frappe.call({
		method: 'invoice_ninja_integration.api.get_company_sync_statistics',
		args: {
			invoice_ninja_company: frm.doc.name,
			days: 7
		},
		callback: function(r) {
			if (r.message) {
				render_sync_statistics(frm, r.message);
			}
		}
	});
}

function render_sync_statistics(frm, stats) {
	let html = `
		<div class="row">
			<div class="col-md-3">
				<div class="card">
					<div class="card-body text-center">
						<h3 class="text-success">${stats.successful_syncs || 0}</h3>
						<p class="text-muted">Successful Syncs (7d)</p>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card">
					<div class="card-body text-center">
						<h3 class="text-danger">${stats.failed_syncs || 0}</h3>
						<p class="text-muted">Failed Syncs (7d)</p>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card">
					<div class="card-body text-center">
						<h3 class="text-info">${stats.total_records || 0}</h3>
						<p class="text-muted">Total Records Synced</p>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card">
					<div class="card-body text-center">
						<h3>${stats.avg_duration || 0}s</h3>
						<p class="text-muted">Avg Sync Duration</p>
					</div>
				</div>
			</div>
		</div>
	`;

	frm.dashboard.add_section(html, __('Sync Statistics'));
}
