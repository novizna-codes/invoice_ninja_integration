<template>
  <div class="dashboard-card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-gray-900">Sync Logs</h3>
      <button @click="$emit('open-sync-logs')" class="btn btn-sm btn-outline">
        View All
      </button>
    </div>

    <div class="card-content">
      <div v-if="loading" class="text-center py-4">
        <div class="loading-spinner"></div>
      </div>

      <div v-else-if="logs.length === 0" class="text-center py-8 text-gray-500">
        No sync logs available
      </div>

      <div v-else class="logs-list">
        <div
          v-for="log in logs"
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
</template>

<script setup>
// Props
const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// Emits
defineEmits(['open-sync-logs']);

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

.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
}

.btn-outline {
  background-color: transparent;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-outline:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

/* Loading Spinner */
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Logs List */
.logs-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.log-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
}

.log-content {
  flex: 1;
}

.log-title {
  font-weight: 500;
  color: #1f2937;
  font-size: 0.875rem;
}

.log-message {
  color: #6b7280;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.log-time {
  color: #9ca3af;
  font-size: 0.6875rem;
  margin-top: 0.25rem;
}

.log-status {
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

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
