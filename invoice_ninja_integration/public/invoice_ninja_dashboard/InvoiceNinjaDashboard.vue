<script setup>
import { ref, onMounted } from 'vue';
import DashboardHeader from './components/DashboardHeader.vue';
import StatsGrid from './components/StatsGrid.vue';
import CompanyMappings from './components/CompanyMappings.vue';
import SyncControls from './components/SyncControls.vue';
import RecentActivity from './components/RecentActivity.vue';
import SyncLogs from './components/SyncLogs.vue';
import QuickActions from './components/QuickActions.vue';
import ErrorAlert from './components/ErrorAlert.vue';

// Reactive state
const loading = ref(true);
const syncing = ref(false);
const loadingMappings = ref(false);
const error = ref(null);

const stats = ref({
  totalInvoices: 0,
  totalClients: 0,
  pendingPayments: 0,
  overdueInvoices: 0,
  lastSyncTime: null,
  syncStatus: 'idle' // idle, syncing, success, error
});

const recentActivity = ref([]);
const syncLogs = ref([]);
const companyMappings = ref([]);

// Configuration
const config = ref({
  apiUrl: '',
  apiToken: '',
  isConnected: false,
  autoSync: true,
  syncInterval: 60 // minutes
});

// Fetch dashboard data
const fetchDashboardData = async () => {
  try {
    loading.value = true;
    error.value = null;

    // Fetch configuration
    const configResponse = await frappe.call({
      method: 'invoice_ninja_integration.api.get_configuration'
    });

    if (configResponse.message) {
      config.value = { ...config.value, ...configResponse.message };
    }

    // Fetch statistics
    const statsResponse = await frappe.call({
      method: 'invoice_ninja_integration.api.get_dashboard_stats'
    });

    if (statsResponse.message) {
      stats.value = { ...stats.value, ...statsResponse.message };
    }

    // Fetch recent activity
    const activityResponse = await frappe.call({
      method: 'invoice_ninja_integration.api.get_recent_activity',
      args: { limit: 10 }
    });

    if (activityResponse.message) {
      recentActivity.value = activityResponse.message;
    }

    // Fetch sync logs
    const logsResponse = await frappe.call({
      method: 'invoice_ninja_integration.api.get_sync_logs',
      args: { limit: 5 }
    });

    if (logsResponse.message) {
      syncLogs.value = logsResponse.message;
    }

  } catch (err) {
    error.value = err.message || 'Failed to load dashboard data';
    console.error('Dashboard error:', err);
  } finally {
    loading.value = false;
  }
};

// Manual sync
const triggerSync = async (syncType = 'all') => {
  try {
    syncing.value = true;
    stats.value.syncStatus = 'syncing';

    const response = await frappe.call({
      method: 'invoice_ninja_integration.api.trigger_manual_sync',
      args: { sync_type: syncType }
    });

    if (response.message) {
      stats.value.syncStatus = 'success';
      frappe.show_alert({
        message: `${syncType} sync completed successfully`,
        indicator: 'green'
      });

      // Refresh data after sync
      setTimeout(() => {
        fetchDashboardData();
      }, 2000);
    }
  } catch (err) {
    stats.value.syncStatus = 'error';
    frappe.show_alert({
      message: `Sync failed: ${err.message}`,
      indicator: 'red'
    });
  } finally {
    syncing.value = false;
  }
};

// Test connection
const testConnection = async () => {
  try {
    const response = await frappe.call({
      method: 'invoice_ninja_integration.api.test_connection'
    });

    if (response.message && response.message.success) {
      frappe.show_alert({
        message: 'Connection test successful',
        indicator: 'green'
      });
      config.value.isConnected = true;
    } else {
      throw new Error(response.message?.error || 'Connection failed');
    }
  } catch (err) {
    frappe.show_alert({
      message: `Connection test failed: ${err.message}`,
      indicator: 'red'
    });
    config.value.isConnected = false;
  }
};

// Company mappings functions
const fetchCompanyMappings = async () => {
  try {
    const response = await frappe.call({
      method: 'invoice_ninja_integration.api.get_company_mappings'
    });

    if (response.message && response.message.success) {
      companyMappings.value = response.message.mappings || [];
    }
  } catch (err) {
    console.error('Error fetching company mappings:', err);
  }
};

const refreshCompanyMappings = async () => {
  try {
    loadingMappings.value = true;
    await fetchCompanyMappings();

    frappe.show_alert({
      message: 'Company mappings refreshed',
      indicator: 'green'
    });
  } catch (err) {
    frappe.show_alert({
      message: `Failed to refresh mappings: ${err.message}`,
      indicator: 'red'
    });
  } finally {
    loadingMappings.value = false;
  }
};

// Navigation functions
const openConfiguration = () => {
  frappe.set_route('Form', 'Invoice Ninja Settings');
};

const openSettings = () => {
  frappe.set_route('Form', 'Invoice Ninja Settings');
};

const openSyncLogs = () => {
  frappe.set_route('List', 'Invoice Ninja Sync Logs');
};

const openInvoiceList = () => {
  frappe.set_route('List', 'Sales Invoice', { 'invoice_ninja_id': ['!=', ''] });
};

const openCustomerList = () => {
  frappe.set_route('List', 'Customer', { 'invoice_ninja_id': ['!=', ''] });
};

// Event handlers
const handleCloseError = () => {
  error.value = null;
};

// Computed properties removed - moved to individual components

onMounted(() => {
  fetchDashboardData();
  fetchCompanyMappings();

  // Auto-refresh every 30 seconds
  const refreshInterval = setInterval(() => {
    if (!loading.value && !syncing.value) {
      fetchDashboardData();
      fetchCompanyMappings();
    }
  }, 30000);

  // Cleanup interval on unmount
  return () => {
    clearInterval(refreshInterval);
  };
});
</script>

<template>
  <div class="invoice-ninja-dashboard p-6 max-w-7xl mx-auto">
    <!-- Error Alert -->
    <ErrorAlert
      :error="error"
      @close-error="handleCloseError"
    />

    <!-- Header Section -->
    <DashboardHeader
      :config="config"
      :stats="stats"
      @test-connection="testConnection"
      @open-configuration="openConfiguration"
    />

    <!-- Main Stats Grid -->
    <StatsGrid
      :stats="stats"
      :loading="loading"
      @open-invoice-list="openInvoiceList"
      @open-customer-list="openCustomerList"
    />

    <!-- Company Mappings -->
    <CompanyMappings
      :mappings="companyMappings"
      :loading="loadingMappings"
      @refresh-mappings="refreshCompanyMappings"
      @open-settings="openSettings"
    />

    <!-- Sync Controls -->
    <SyncControls
      :stats="stats"
      :config="config"
      :syncing="syncing"
      :loading="loading"
      @trigger-sync="triggerSync"
    />

    <!-- Two Column Layout -->
    <div class="dashboard-grid">
      <!-- Recent Activity -->
      <RecentActivity
        :activity="recentActivity"
        :loading="loading"
        @refresh-data="fetchDashboardData"
      />

      <!-- Sync Logs -->
      <SyncLogs
        :logs="syncLogs"
        :loading="loading"
        @open-sync-logs="openSyncLogs"
      />
    </div>

    <!-- Quick Actions Footer -->
    <QuickActions
      @open-configuration="openConfiguration"
      @open-sync-logs="openSyncLogs"
      @open-invoice-list="openInvoiceList"
      @open-customer-list="openCustomerList"
    />
  </div>
</template>

<style scoped>
.invoice-ninja-dashboard {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  min-height: 100vh;
  background-color: #f8fafc;
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .invoice-ninja-dashboard {
    padding: 1rem;
  }
}
</style>