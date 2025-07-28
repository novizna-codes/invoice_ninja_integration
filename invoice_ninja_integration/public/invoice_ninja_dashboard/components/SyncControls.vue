<template>
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
            @click="$emit('trigger-sync', 'all')"
            :disabled="syncing || loading"
            class="btn btn-primary"
          >
            <span v-if="syncing" class="loading-spinner-sm"></span>
            {{ syncing ? 'Syncing...' : 'Full Sync' }}
          </button>

          <div class="sync-options">
            <button
              @click="$emit('trigger-sync', 'customers')"
              :disabled="syncing || loading"
              class="btn btn-secondary"
            >
              Sync Customers
            </button>
            <button
              @click="$emit('trigger-sync', 'invoices')"
              :disabled="syncing || loading"
              class="btn btn-secondary"
            >
              Sync Invoices
            </button>
            <button
              @click="$emit('trigger-sync', 'payments')"
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
</template>

<script setup>
// Props
const props = defineProps({
  stats: {
    type: Object,
    required: true
  },
  config: {
    type: Object,
    required: true
  },
  syncing: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// Emits
defineEmits(['trigger-sync']);

// Helper functions
const formatDate = (dateString) => {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleString();
};
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

/* Responsive */
@media (max-width: 768px) {
  .sync-controls {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
