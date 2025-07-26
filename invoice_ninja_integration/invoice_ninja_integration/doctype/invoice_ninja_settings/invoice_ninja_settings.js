// Client-side JavaScript for Invoice Ninja Settings form
frappe.ui.form.on('Invoice Ninja Settings', {
    refresh: function(frm) {
        // Add sync status indicators
        add_sync_status_indicators(frm);
    },

    test_connection: function(frm) {
        // Handle test connection button click
        test_invoice_ninja_connection(frm);
    },

    enable_customer_sync: function(frm) {
        // Toggle customer sync direction field visibility
        frm.toggle_display('customer_sync_direction', frm.doc.enable_customer_sync);
    },

    enable_invoice_sync: function(frm) {
        // Toggle invoice sync direction field visibility
        frm.toggle_display('invoice_sync_direction', frm.doc.enable_invoice_sync);
    },

    enable_quote_sync: function(frm) {
        // Toggle quote sync direction field visibility
        frm.toggle_display('quote_sync_direction', frm.doc.enable_quote_sync);
    },

    enable_product_sync: function(frm) {
        // Toggle product sync direction field visibility
        frm.toggle_display('product_sync_direction', frm.doc.enable_product_sync);
    },

    enable_payment_sync: function(frm) {
        // Toggle payment sync direction field visibility
        frm.toggle_display('payment_sync_direction', frm.doc.enable_payment_sync);
    }
});

function add_sync_status_indicators(frm) {
    // Add visual indicators for sync directions
    if (frm.doc.enable_customer_sync) {
        let direction = frm.doc.customer_sync_direction || 'Invoice Ninja to ERPNext';
        let indicator = get_direction_indicator(direction);
        frm.set_df_property('customer_sync_direction', 'description', indicator);
    }

    if (frm.doc.enable_invoice_sync) {
        let direction = frm.doc.invoice_sync_direction || 'Invoice Ninja to ERPNext';
        let indicator = get_direction_indicator(direction);
        frm.set_df_property('invoice_sync_direction', 'description', indicator);
    }

    if (frm.doc.enable_quote_sync) {
        let direction = frm.doc.quote_sync_direction || 'Invoice Ninja to ERPNext';
        let indicator = get_direction_indicator(direction);
        frm.set_df_property('quote_sync_direction', 'description', indicator);
    }

    if (frm.doc.enable_product_sync) {
        let direction = frm.doc.product_sync_direction || 'Invoice Ninja to ERPNext';
        let indicator = get_direction_indicator(direction);
        frm.set_df_property('product_sync_direction', 'description', indicator);
    }

    if (frm.doc.enable_payment_sync) {
        let direction = frm.doc.payment_sync_direction || 'Invoice Ninja to ERPNext';
        let indicator = get_direction_indicator(direction);
        frm.set_df_property('payment_sync_direction', 'description', indicator);
    }
}

function get_direction_indicator(direction) {
    switch(direction) {
        case 'Invoice Ninja to ERPNext':
            return '<span style="color: #4CAF50;">← Data flows from Invoice Ninja to ERPNext</span>';
        case 'ERPNext to Invoice Ninja':
            return '<span style="color: #2196F3;">→ Data flows from ERPNext to Invoice Ninja</span>';
        case 'Bidirectional':
            return '<span style="color: #FF9800;">↔ Data syncs in both directions</span>';
        default:
            return '';
    }
}

function test_invoice_ninja_connection(frm) {
    if (!frm.doc.invoice_ninja_url || !frm.doc.api_token) {
        frappe.msgprint(__('Please enter Invoice Ninja URL and API Token before testing connection.'));
        return;
    }

    frappe.call({
        method: 'test_connection',
        doc: frm.doc,
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.msgprint(__('Connection successful!'), __('Success'));
                frm.refresh_field('connection_status');
            } else {
                frappe.msgprint(__('Connection failed. Please check your settings.'), __('Error'));
                frm.refresh_field('connection_status');
            }
        },
        error: function(r) {
            frappe.msgprint(__('Connection test failed. Please check your settings.'), __('Error'));
        }
    });
}

function show_manual_sync_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Manual Sync'),
        fields: [
            {
                label: __('Sync Type'),
                fieldname: 'sync_type',
                fieldtype: 'Select',
                options: 'Customer\nInvoice\nQuote\nProduct\nPayment',
                reqd: 1
            },
            {
                label: __('Sync Direction'),
                fieldname: 'sync_direction',
                fieldtype: 'Select',
                options: 'Invoice Ninja to ERPNext\nERPNext to Invoice Ninja',
                reqd: 1
            },
            {
                label: __('Record ID (optional)'),
                fieldname: 'record_id',
                fieldtype: 'Data',
                description: 'Leave empty to sync all records'
            }
        ],
        primary_action_label: __('Start Sync'),
        primary_action: function(values) {
            frappe.call({
                method: 'invoice_ninja_integration.tasks.manual_sync',
                args: values,
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint(__('Sync started successfully!'));
                    } else {
                        frappe.msgprint(__('Sync failed: ' + (r.message.error || 'Unknown error')));
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
}
