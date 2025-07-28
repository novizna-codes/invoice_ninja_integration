import { createApp } from 'vue';
import InvoiceNinjaDashboard from './InvoiceNinjaDashboard.vue';

// A simple function to mount your Vue app
function setup_ij_dashboard_vue(wrapper) {
  const app = createApp(InvoiceNinjaDashboard);
  app.mount(wrapper.get(0));
  return app;
}

// Make it available globally for Frappe
window.setup_ij_dashboard_vue = setup_ij_dashboard_vue;
frappe.ui.setup_ij_dashboard_vue = setup_ij_dashboard_vue;

export default setup_ij_dashboard_vue;
