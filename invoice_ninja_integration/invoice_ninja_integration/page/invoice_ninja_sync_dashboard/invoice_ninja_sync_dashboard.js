frappe.pages['invoice-ninja-sync-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Invoice Ninja Sync Dashboard',
        single_column: true
    });

    const $parent = $(wrapper).find('.layout-main-section');
    $parent.empty();

    // Load Vue3 dashboard
    frappe.require(['invoice_ninja_dashboard.bundle.js'], function() {
        if (window.setup_ij_dashboard_vue) {
            window.setup_ij_dashboard_vue($parent);
        } else {
            console.error('setup_ij_dashboard_vue function not found');
        }
    });

    if (frappe.boot.developer_mode) {
        frappe.hot_update = frappe.hot_update || [];
        frappe.hot_update.push(() => window.setup_ij_dashboard_vue(page.main[0]));
    }
};
