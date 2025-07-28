<template>
  <div class="dashboard-card mt-6">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-gray-900">Quick Actions</h3>
    </div>

    <div class="card-content">
      <div class="quick-actions">
        <button @click="$emit('open-configuration')" class="action-button">
          <div class="action-icon">⚙️</div>
          <div class="action-content">
            <div class="action-title">Configuration</div>
            <div class="action-description">Manage API settings and sync preferences</div>
          </div>
        </button>

        <button @click="$emit('open-sync-logs')" class="action-button">
          <div class="action-icon">📋</div>
          <div class="action-content">
            <div class="action-title">Sync Logs</div>
            <div class="action-description">View detailed synchronization history</div>
          </div>
        </button>

        <button @click="$emit('open-invoice-list')" class="action-button">
          <div class="action-icon">📄</div>
          <div class="action-content">
            <div class="action-title">Synced Invoices</div>
            <div class="action-description">Browse invoices from Invoice Ninja</div>
          </div>
        </button>

        <button @click="$emit('open-customer-list')" class="action-button">
          <div class="action-icon">👥</div>
          <div class="action-content">
            <div class="action-title">Synced Customers</div>
            <div class="action-description">Manage synchronized customer data</div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
// Emits
defineEmits(['open-configuration', 'open-sync-logs', 'open-invoice-list', 'open-customer-list']);
</script>

<style scoped>
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

/* Responsive */
@media (max-width: 768px) {
  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
