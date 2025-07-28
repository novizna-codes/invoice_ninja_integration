<script setup>
import { ref, computed, onMounted } from 'vue';

// Reactive state
const loading = ref(true);
const syncing = ref(false);
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

// Navigation functions
const openConfiguration = () => {
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

// Computed properties
const connectionStatus = computed(() => {
  if (!config.value.apiUrl || !config.value.apiToken) {
    return { text: 'Not Configured', color: 'text-gray-500', bg: 'bg-gray-100' };
  }
  if (config.value.isConnected) {
    return { text: 'Connected', color: 'text-green-700', bg: 'bg-green-100' };
  }
  return { text: 'Disconnected', color: 'text-red-700', bg: 'bg-red-100' };
});

const syncStatusDisplay = computed(() => {
  switch (stats.value.syncStatus) {
    case 'syncing':
      return { text: 'Syncing...', color: 'text-blue-700', bg: 'bg-blue-100' };
    case 'success':
      return { text: 'Up to date', color: 'text-green-700', bg: 'bg-green-100' };
    case 'error':
      return { text: 'Sync Error', color: 'text-red-700', bg: 'bg-red-100' };
    default:
      return { text: 'Idle', color: 'text-gray-700', bg: 'bg-gray-100' };
  }
});

const formatDate = (dateString) => {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleString();
};

const formatActivityType = (type) => {
  const types = {
    'customer_sync': 'Customer Sync',
    'invoice_sync': 'Invoice Sync',
    'payment_sync': 'Payment Sync',
    'quote_sync': 'Quote Sync',
    'product_sync': 'Product Sync',
    'error': 'Error'
  };
  return types[type] || type;
};

onMounted(() => {
  fetchDashboardData();
  
  // Auto-refresh every 30 seconds
  const refreshInterval = setInterval(() => {
    if (!loading.value && !syncing.value) {
      fetchDashboardData();
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
    <div v-if="error" class="alert alert-error mb-6">
      <div class="alert-content">
        <strong>Error:</strong> {{ error }}
        <button @click="error = null" class="alert-close">&times;</button>
      </div>
    </div>

    <!-- Header Section -->
    <div class="dashboard-header mb-6">
      <div class="header-content">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Invoice Ninja Integration</h1>
          <p class="text-gray-600 mt-1">Manage your Invoice Ninja synchronization and data</p>
        </div>
        <div class="header-actions">
          <div class="status-badges">
            <span :class="['status-badge', connectionStatus.bg, connectionStatus.color]">
              {{ connectionStatus.text }}
            </span>
            <span :class="['status-badge', syncStatusDisplay.bg, syncStatusDisplay.color]">
              {{ syncStatusDisplay.text }}
            </span>
          </div>
          <button @click="testConnection" class="btn btn-outline">
            Test Connection
          </button>
          <button @click="openConfiguration" class="btn btn-primary">
            Configure
          </button>
        </div>
      </div>
    </div>

    <!-- Main Stats Grid -->
    <div class="stats-grid mb-8">
      <div class="stat-card clickable" @click="openInvoiceList">
        <div class="stat-icon stat-icon-blue">
          📄
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ loading ? '...' : stats.totalInvoices }}</div>
          <div class="stat-label">Total Invoices</div>
          <div class="stat-sublabel">Synced from Invoice Ninja</div>
        </div>
      </div>
      
      <div class="stat-card clickable" @click="openCustomerList">
        <div class="stat-icon stat-icon-green">
          👥
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ loading ? '...' : stats.totalClients }}</div>
          <div class="stat-label">Total Clients</div>
          <div class="stat-sublabel">Synced customers</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon stat-icon-orange">
          💰
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ loading ? '...' : stats.pendingPayments }}</div>
          <div class="stat-label">Pending Payments</div>
          <div class="stat-sublabel">Awaiting payment</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon stat-icon-red">
          ⚠️
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ loading ? '...' : stats.overdueInvoices }}</div>
          <div class="stat-label">Overdue Invoices</div>
          <div class="stat-sublabel">Past due date</div>
        </div>
      </div>
    </div>

    <!-- Sync Controls -->
    <div class="dashboard-card mb-6">
      <div class="card-header">
        <h2 class="text-lg font-semibold text-gray-900">Synchronization Controls</h2>
        <div class="text-sm text-gray-500">
          Last sync: {{ formatDate(stats.lastSyncTime) }}
        </div>
      </div>
      
      <div class="card-content">
        <div class="sync-controls">
          <div class="sync-buttons">
            <button 
              @click="triggerSync('all')" 
              :disabled="syncing || loading"
              class="btn btn-primary"
            >
              <span v-if="syncing" class="loading-spinner-sm"></span>
              {{ syncing ? 'Syncing...' : 'Full Sync' }}
            </button>
            
            <div class="sync-options">
              <button 
                @click="triggerSync('customers')" 
                :disabled="syncing || loading"
                class="btn btn-secondary"
              >
                Sync Customers
              </button>
              <button 
                @click="triggerSync('invoices')" 
                :disabled="syncing || loading"
                class="btn btn-secondary"
              >
                Sync Invoices
              </button>
              <button 
                @click="triggerSync('payments')" 
                :disabled="syncing || loading"
                class="btn btn-secondary"
              >
                Sync Payments
              </button>
            </div>
          </div>
          
          <div class="sync-info">
            <div class="info-item">
              <span class="info-label">Auto Sync:</span>
              <span :class="config.autoSync ? 'text-green-600' : 'text-gray-600'">
                {{ config.autoSync ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">Sync Interval:</span>
              <span class="text-gray-600">{{ config.syncInterval }} minutes</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Two Column Layout -->
    <div class="dashboard-grid">
      <!-- Recent Activity -->
      <div class="dashboard-card">
        <div class="card-header">
          <h3 class="text-lg font-semibold text-gray-900">Recent Activity</h3>
          <button @click="fetchDashboardData" class="btn-refresh">
            🔄
          </button>
        </div>
        
        <div class="card-content">
          <div v-if="loading" class="text-center py-4">
            <div class="loading-spinner"></div>
          </div>
          
          <div v-else-if="recentActivity.length === 0" class="text-center py-8 text-gray-500">
            No recent activity
          </div>
          
          <div v-else class="activity-list">
            <div 
              v-for="activity in recentActivity" 
              :key="activity.id"
              class="activity-item"
            >
              <div class="activity-content">
                <div class="activity-title">
                  {{ formatActivityType(activity.type) }}
                </div>
                <div class="activity-description">
                  {{ activity.description }}
                </div>
                <div class="activity-time">
                  {{ formatDate(activity.created_at) }}
                </div>
              </div>
              <div :class="['activity-status', activity.status === 'success' ? 'status-success' : 'status-error']">
                {{ activity.status }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sync Logs -->
      <div class="dashboard-card">
        <div class="card-header">
          <h3 class="text-lg font-semibold text-gray-900">Sync Logs</h3>
          <button @click="openSyncLogs" class="btn btn-sm btn-outline">
            View All
          </button>
        </div>
        
        <div class="card-content">
          <div v-if="loading" class="text-center py-4">
            <div class="loading-spinner"></div>
          </div>
          
          <div v-else-if="syncLogs.length === 0" class="text-center py-8 text-gray-500">
            No sync logs available
          </div>
          
          <div v-else class="logs-list">
            <div 
              v-for="log in syncLogs" 
              :key="log.id"
              class="log-item"
            >
              <div class="log-content">
                <div class="log-title">
                  {{ log.sync_type }} - {{ log.entity_type }}
                </div>
                <div class="log-message">
                  {{ log.message }}
                </div>
                <div class="log-time">
                  {{ formatDate(log.created_at) }}
                </div>
              </div>
              <div :class="['log-status', log.status === 'success' ? 'status-success' : 'status-error']">
                {{ log.status }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions Footer -->
    <div class="dashboard-card mt-6">
      <div class="card-header">
        <h3 class="text-lg font-semibold text-gray-900">Quick Actions</h3>
      </div>
      
      <div class="card-content">
        <div class="quick-actions">
          <button @click="openConfiguration" class="action-button">
            <div class="action-icon">⚙️</div>
            <div class="action-content">
              <div class="action-title">Configuration</div>
              <div class="action-description">Manage API settings and sync preferences</div>
            </div>
          </button>
          
          <button @click="openSyncLogs" class="action-button">
            <div class="action-icon">📋</div>
            <div class="action-content">
              <div class="action-title">Sync Logs</div>
              <div class="action-description">View detailed synchronization history</div>
            </div>
          </button>
          
          <button @click="openInvoiceList" class="action-button">
            <div class="action-icon">📄</div>
            <div class="action-content">
              <div class="action-title">Synced Invoices</div>
              <div class="action-description">Browse invoices from Invoice Ninja</div>
            </div>
          </button>
          
          <button @click="openCustomerList" class="action-button">
            <div class="action-icon">👥</div>
            <div class="action-content">
              <div class="action-title">Synced Customers</div>
              <div class="action-description">Manage synchronized customer data</div>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.invoice-ninja-dashboard {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  min-height: 100vh;
  background-color: #f8fafc;
}

/* Header Styles */
.dashboard-header {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.status-badges {
  display: flex;
  gap: 0.5rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

/* Alert Styles */
.alert {
  border-radius: 8px;
  padding: 1rem;
}

.alert-error {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.alert-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: inherit;
  padding: 0;
  margin-left: 1rem;
}

/* Card Styles */
.dashboard-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.card-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  padding: 1.5rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.2s;
}

.stat-card.clickable {
  cursor: pointer;
}

.stat-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.stat-icon-blue { background-color: #dbeafe; }
.stat-icon-green { background-color: #d1fae5; }
.stat-icon-orange { background-color: #fed7aa; }
.stat-icon-red { background-color: #fecaca; }

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 1.875rem;
  font-weight: bold;
  color: #1f2937;
  line-height: 1;
}

.stat-label {
  color: #374151;
  font-size: 0.875rem;
  font-weight: 600;
  margin-top: 0.25rem;
}

.stat-sublabel {
  color: #6b7280;
  font-size: 0.75rem;
  margin-top: 0.125rem;
}

/* Sync Controls */
.sync-controls {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 2rem;
  flex-wrap: wrap;
}

.sync-buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sync-options {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sync-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item {
  display: flex;
  gap: 0.5rem;
}

.info-label {
  font-weight: 500;
  color: #374151;
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

/* Activity Lists */
.activity-list, .logs-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.activity-item, .log-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
}

.activity-content, .log-content {
  flex: 1;
}

.activity-title, .log-title {
  font-weight: 500;
  color: #1f2937;
  font-size: 0.875rem;
}

.activity-description, .log-message {
  color: #6b7280;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.activity-time, .log-time {
  color: #9ca3af;
  font-size: 0.6875rem;
  margin-top: 0.25rem;
}

.activity-status, .log-status {
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
}

.status-success {
  background-color: #d1fae5;
  color: #065f46;
}

.status-error {
  background-color: #fecaca;
  color: #991b1b;
}

/* Quick Actions */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.action-button:hover {
  border-color: #2563eb;
  background-color: #f8fafc;
}

.action-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.action-content {
  flex: 1;
}

.action-title {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.action-description {
  color: #6b7280;
  font-size: 0.75rem;
}

/* Button Styles */
.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: none;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #2563eb;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1d4ed8;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #e5e7eb;
}

.btn-outline {
  background-color: transparent;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-outline:hover:not(:disabled) {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
}

.btn-refresh {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.btn-refresh:hover {
  background-color: #f3f4f6;
}

/* Loading Spinners */
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

.loading-spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Responsive Design */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .sync-controls {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>