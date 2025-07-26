frappe.pages['invoice-ninja-sync-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Invoice Ninja Sync Dashboard',
        single_column: true
    });

    page.main.html(`
        <div class="sync-dashboard">
            <div class="row">
                <div class="col-md-12">
                    <div class="dashboard-card">
                        <h4>${__("Connection Status")}</h4>
                        <div id="connection-status">
                            <span class="status-indicator status-not-tested"></span>
                            <span>${__("Loading...")}</span>
                        </div>
                        <div class="btn-group-custom">
                            <button class="btn btn-sm btn-primary" onclick="testConnection()">
                                ${__("Test Connection")}
                            </button>
                            <button class="btn btn-sm btn-secondary" onclick="refreshDashboard()">
                                ${__("Refresh")}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="dashboard-card">
                        <h4>${__("Sync Control")}</h4>
                        <div id="sync-control">
                            <div class="form-group">
                                <label class="checkbox">
                                    <input type="checkbox" id="auto-sync-toggle" onchange="toggleAutoSync()">
                                    ${__("Enable Automatic Sync")}
                                </label>
                            </div>
                        </div>
                        <div class="btn-group-custom">
                            <button class="btn btn-sm btn-success" onclick="showManualSyncDialog()">
                                ${__("Manual Sync")}
                            </button>
                            <button class="btn btn-sm btn-warning" onclick="clearSyncLogs()">
                                ${__("Clear Old Logs")}
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="dashboard-card">
                        <h4>${__("Sync Configuration")}</h4>
                        <div id="sync-config">
                            ${__("Loading configuration...")}
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-12">
                    <div class="dashboard-card">
                        <h4>${__("Sync Statistics")}</h4>
                        <div id="sync-stats" class="stats-grid">
                            ${__("Loading statistics...")}
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-12">
                    <div class="dashboard-card">
                        <h4>${__("Recent Sync Activity")}</h4>
                        <div id="sync-logs">
                            ${__("Loading logs...")}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);

    // Add custom CSS
    // frappe.dom.add_style(`
    //     .sync-dashboard {
    //         padding: 20px;
    //     }
    //     .dashboard-card {
    //         background: #fff;
    //         border: 1px solid #d1d8dd;
    //         border-radius: 6px;
    //         padding: 20px;
    //         margin-bottom: 20px;
    //         box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    //     }
    //     .dashboard-card h4 {
    //         color: #36414c;
    //         margin-bottom: 15px;
    //         border-bottom: 1px solid #ebeff2;
    //         padding-bottom: 10px;
    //     }
    //     .status-indicator {
    //         display: inline-block;
    //         width: 12px;
    //         height: 12px;
    //         border-radius: 50%;
    //         margin-right: 8px;
    //     }
    //     .status-connected { background-color: #28a745; }
    //     .status-failed { background-color: #dc3545; }
    //     .status-not-tested { background-color: #ffc107; }
    //     .sync-direction {
    //         font-size: 0.9em;
    //         color: #6c757d;
    //     }
    //     .btn-group-custom {
    //         margin-bottom: 15px;
    //     }
    //     .btn-group-custom .btn {
    //         margin-right: 10px;
    //         margin-bottom: 10px;
    //     }
    //     .log-entry {
    //         padding: 10px;
    //         border-left: 3px solid #dee2e6;
    //         margin-bottom: 10px;
    //         background: #f8f9fa;
    //     }
    //     .log-entry.success { border-left-color: #28a745; }
    //     .log-entry.error { border-left-color: #dc3545; }
    //     .log-entry.warning { border-left-color: #ffc107; }
    //     .log-timestamp {
    //         font-size: 0.8em;
    //         color: #6c757d;
    //     }
    //     .stats-grid {
    //         display: grid;
    //         grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    //         gap: 15px;
    //         margin-bottom: 20px;
    //     }
    //     .stat-box {
    //         background: #f8f9fa;
    //         padding: 15px;
    //         border-radius: 6px;
    //         text-align: center;
    //     }
    //     .stat-number {
    //         font-size: 2em;
    //         font-weight: bold;
    //         color: #495057;
    //     }
    //     .stat-label {
    //         color: #6c757d;
    //         font-size: 0.9em;
    //     }
    // `);

    // Load dashboard data
    loadDashboardData();
};

function loadDashboardData() {
    frappe.call({
        method: 'invoice_ninja_integration.page.invoice_ninja_sync_dashboard.invoice_ninja_sync_dashboard.get_sync_dashboard_data',
        callback: function(r) {
            if (r.message && !r.message.error) {
                updateDashboard(r.message);
            } else {
                frappe.msgprint(__('Error loading dashboard data: ' + (r.message?.error || 'Unknown error')));
            }
        }
    });
}

function updateDashboard(data) {
    // Update connection status
    updateConnectionStatus(data);

    // Update sync control
    updateSyncControl(data);

    // Update sync configuration
    updateSyncConfiguration(data);

    // Update statistics
    updateSyncStatistics(data);

    // Update logs
    updateSyncLogs(data);
}

function updateConnectionStatus(data) {
    const statusEl = document.getElementById('connection-status');
    let statusClass = 'status-not-tested';
    let statusText = data.connection_status || 'Not Tested';

    if (data.connection_status === 'Connected') {
        statusClass = 'status-connected';
    } else if (data.connection_status === 'Failed') {
        statusClass = 'status-failed';
    }

    statusEl.innerHTML = `
        <span class="status-indicator ${statusClass}"></span>
        <span>${statusText}</span>
        ${data.last_sync_time ? `<br><small class="text-muted">Last sync: ${data.last_sync_time}</small>` : ''}
    `;
}

function updateSyncControl(data) {
    const toggleEl = document.getElementById('auto-sync-toggle');
    if (toggleEl) {
        toggleEl.checked = data.sync_enabled || false;
    }
}

function updateSyncConfiguration(data) {
    const configEl = document.getElementById('sync-config');
    if (!data.sync_config) {
        configEl.innerHTML = __('No configuration found');
        return;
    }

    let configHtml = '';
    Object.keys(data.sync_config).forEach(key => {
        const config = data.sync_config[key];
        const enabledBadge = config.enabled ?
            '<span class="badge badge-success">Enabled</span>' :
            '<span class="badge badge-secondary">Disabled</span>';

        configHtml += `
            <div class="mb-2">
                <strong>${key.replace('_', ' ').toUpperCase()}</strong> ${enabledBadge}
                ${config.enabled ? `<br><span class="sync-direction">${config.direction}</span>` : ''}
            </div>
        `;
    });

    configEl.innerHTML = configHtml;
}

function updateSyncStatistics(data) {
    const statsEl = document.getElementById('sync-stats');
    if (!data.sync_stats) {
        statsEl.innerHTML = __('No statistics available');
        return;
    }

    let statsHtml = `
        <div class="stat-box">
            <div class="stat-number">${data.sync_stats.failed_syncs || 0}</div>
            <div class="stat-label">${__('Failed Syncs')}</div>
        </div>
    `;

    if (data.sync_stats.successful_syncs) {
        data.sync_stats.successful_syncs.forEach(stat => {
            statsHtml += `
                <div class="stat-box">
                    <div class="stat-number">${stat.count}</div>
                    <div class="stat-label">${stat.sync_type} Syncs</div>
                </div>
            `;
        });
    }

    statsEl.innerHTML = statsHtml;
}

function updateSyncLogs(data) {
    const logsEl = document.getElementById('sync-logs');
    if (!data.sync_logs) {
        logsEl.innerHTML = __('No logs available');
        return;
    }

    let logsHtml = '';

    // Display job logs
    if (data.sync_logs.job_logs && data.sync_logs.job_logs.length > 0) {
        logsHtml += '<h6>Background Jobs</h6>';
        data.sync_logs.job_logs.slice(0, 10).forEach(log => {
            const logClass = log.status === 'finished' ? 'success' :
                           log.status === 'failed' ? 'error' : 'warning';

            logsHtml += `
                <div class="log-entry ${logClass}">
                    <strong>${log.job_name || 'Unknown Job'}</strong>
                    <span class="badge badge-${logClass === 'success' ? 'success' : 'danger'}">${log.status}</span>
                    <div class="log-timestamp">${log.creation}</div>
                    ${log.exc_info ? `<small class="text-danger">${log.exc_info}</small>` : ''}
                </div>
            `;
        });
    }

    // Display error logs
    if (data.sync_logs.error_logs && data.sync_logs.error_logs.length > 0) {
        logsHtml += '<h6>Error Logs</h6>';
        data.sync_logs.error_logs.slice(0, 5).forEach(log => {
            logsHtml += `
                <div class="log-entry error">
                    <strong>${log.method || 'Unknown Method'}</strong>
                    <div class="log-timestamp">${log.creation}</div>
                    <small>${log.error.substring(0, 200)}${log.error.length > 200 ? '...' : ''}</small>
                </div>
            `;
        });
    }

    if (!logsHtml) {
        logsHtml = __('No recent sync activity');
    }

    logsEl.innerHTML = logsHtml;
}

// Dashboard Actions
function testConnection() {
    frappe.call({
        method: 'invoice_ninja_integration.page.invoice_ninja_sync_dashboard.invoice_ninja_sync_dashboard.test_connection',
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({message: __('Connection successful!'), indicator: 'green'});
            } else {
                frappe.show_alert({message: __('Connection failed!'), indicator: 'red'});
            }
            refreshDashboard();
        }
    });
}

function refreshDashboard() {
    loadDashboardData();
}

function toggleAutoSync() {
    const enabled = document.getElementById('auto-sync-toggle').checked;

    frappe.call({
        method: 'invoice_ninja_integration.page.invoice_ninja_sync_dashboard.invoice_ninja_sync_dashboard.toggle_auto_sync',
        args: { enable: enabled },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({message: r.message.message, indicator: 'green'});
            } else {
                frappe.show_alert({message: r.message?.error || 'Error toggling auto sync', indicator: 'red'});
                // Revert checkbox
                document.getElementById('auto-sync-toggle').checked = !enabled;
            }
        }
    });
}

function showManualSyncDialog() {
    let d = new frappe.ui.Dialog({
        title: __('Manual Sync'),
        fields: [
            {
                label: __('Sync Type'),
                fieldname: 'sync_type',
                fieldtype: 'Select',
                options: ['', 'Customer', 'Invoice', 'Quote', 'Product', 'Payment'],
                reqd: 1
            },
            {
                label: __('Sync Direction'),
                fieldname: 'sync_direction',
                fieldtype: 'Select',
                options: ['', 'Invoice Ninja to ERPNext', 'ERPNext to Invoice Ninja'],
                reqd: 1
            },
            {
                label: __('Record ID (Optional)'),
                fieldname: 'record_id',
                fieldtype: 'Data',
                description: __('Leave empty to sync all records')
            }
        ],
        primary_action_label: __('Start Sync'),
        primary_action: function(values) {
            startManualSync(values);
            d.hide();
        }
    });
    d.show();
}

function startManualSync(values) {
    if (!values) {
        // Get values from dialog if not passed
        values = {
            sync_type: document.getElementById('sync-type')?.value,
            sync_direction: document.getElementById('sync-direction')?.value,
            record_id: document.getElementById('record-id')?.value || null
        };
    }

    if (!values.sync_type || !values.sync_direction) {
        frappe.msgprint(__('Please select sync type and direction'));
        return;
    }

    frappe.call({
        method: 'invoice_ninja_integration.page.invoice_ninja_sync_dashboard.invoice_ninja_sync_dashboard.manual_sync',
        args: values,
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                setTimeout(refreshDashboard, 2000); // Refresh after 2 seconds
            } else {
                frappe.show_alert({
                    message: r.message?.error || 'Sync failed',
                    indicator: 'red'
                });
            }
        }
    });
}

function clearSyncLogs() {
    frappe.confirm(__('Are you sure you want to clear old sync logs?'), function() {
        frappe.call({
            method: 'invoice_ninja_integration.page.invoice_ninja_sync_dashboard.invoice_ninja_sync_dashboard.clear_sync_logs',
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({message: r.message.message, indicator: 'green'});
                    refreshDashboard();
                } else {
                    frappe.show_alert({message: r.message?.error || 'Failed to clear logs', indicator: 'red'});
                }
            }
        });
    });
}
