// Client-side JavaScript for Invoice Ninja Settings form
frappe.ui.form.on('Invoice Ninja Settings', {
    refresh: function(frm) {
        // Add sync status indicators
        add_sync_status_indicators(frm);

        // Add buttons to fetch data from Invoice Ninja - only show when properly configured
        if (frm.doc.invoice_ninja_url && frm.doc.api_token) {
            frm.add_custom_button(__('Fetch Companies'), function() {
                fetch_invoice_ninja_companies(frm);
            }, __('Invoice Ninja'));
            
            frm.add_custom_button(__('Sync Customer Groups'), function() {
                sync_invoice_ninja_customer_groups(frm);
            }, __('Invoice Ninja'));
        }
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

frappe.ui.form.on('Invoice Ninja Company Mapping', {
    // cdt is Child DocType name i.e Quotation Item
    // cdn is the row name for e.g bbfcb8da6a
    invoice_ninja_company_id_add(frm, cdt, cdn) {

        if (!frm._ninja_companies || frm._ninja_companies.length === 0) {
            frappe.msgprint({
                title: __('No Companies Found'),
                message: __('No companies were found in your Invoice Ninja account.'),
                indicator: 'yellow'
            });
            return;
        }


        apply_ninja_company_to_field(frm);
    }
})

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



function fetch_invoice_ninja_companies(frm) {
    // Show loading screen
    frappe.freeze(__('Fetching companies from Invoice Ninja...'));
    
    frappe.call({
        method: 'invoice_ninja_integration.api.get_invoice_ninja_companies',
        callback: function(r) {
            // Always unfreeze screen when response is received
            frappe.unfreeze();
            
            if (r.message && r.message.success) {
                let companies = r.message.companies || [];

                if (companies.length === 0) {
                    frappe.msgprint({
                        title: __('No Companies Found'),
                        message: __('No companies were found in your Invoice Ninja account.'),
                        indicator: 'yellow'
                    });
                    return;
                }

                // Store companies data in form for reference
                frm._ninja_companies = companies;

                // Refresh the child table
                frappe.msgprint({
                    title: __('Companies Fetched'),
                    message: __('Successfully fetched {0} companies from Invoice Ninja', [companies.length]),
                    indicator: 'green'
                });

            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to fetch companies: {0}', [r.message?.error || 'Unknown error']),
                    indicator: 'red'
                });
            }
        },
        error: function() {
            // Always unfreeze screen even on error
            frappe.unfreeze();
            frappe.msgprint({
                title: __('Error'),
                message: __('Network error occurred while fetching companies'),
                indicator: 'red'
            });
        }
    });
}

function sync_invoice_ninja_customer_groups(frm) {
    // Show loading screen
    frappe.freeze(__('Syncing customer groups from Invoice Ninja...'));
    
    frappe.call({
        method: 'invoice_ninja_integration.api.sync_customer_groups_to_doctype',
        callback: function(r) {
            // Always unfreeze screen when response is received
            frappe.unfreeze();
            
            if (r.message && r.message.success) {
                let synced_count = r.message.synced_count || 0;
                
                frappe.msgprint({
                    title: __('Customer Groups Synced'),
                    message: __('Successfully synced {0} customer groups from Invoice Ninja', [synced_count]),
                    indicator: 'green'
                });
                
                // Refresh the form to show any updated data
                frm.reload_doc();
                
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to sync customer groups: {0}', [r.message?.error || 'Unknown error']),
                    indicator: 'red'
                });
            }
        },
        error: function() {
            // Always unfreeze screen even on error
            frappe.unfreeze();
            frappe.msgprint({
                title: __('Error'),
                message: __('Network error occurred while syncing customer groups'),
                indicator: 'red'
            });
        }
    });
}

function apply_ninja_company_to_field(frm) {
    let company_options = frm._ninja_companies.map(company =>
        `${company.id}:${company.name}`
    ).join('\n');

    // Update the field options for invoice_ninja_company_id in child table
    frm.set_df_property('invoice_ninja_company_id', 'options', company_options);

}