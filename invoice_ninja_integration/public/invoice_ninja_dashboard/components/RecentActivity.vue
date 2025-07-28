<template>
  <div class="dashboard-card">
    <div class="card-header">
      <h3 class="text-lg font-semibold text-gray-900">Recent Activity</h3>
      <button @click="$emit('refresh-data')" class="btn-refresh">
        🔄
      </button>
    </div>

    <div class="card-content">
      <div v-if="loading" class="text-center py-4">
        <div class="loading-spinner"></div>
      </div>

      <div v-else-if="activity.length === 0" class="text-center py-8 text-gray-500">
        No recent activity
      </div>

      <div v-else class="activity-list">
        <div
          v-for="item in activity"
          :key="item.id"
          class="activity-item"
        >
          <div class="activity-content">
            <div class="activity-title">
              {{ formatActivityType(item.type) }}
            </div>
            <div class="activity-description">
              {{ item.description }}
            </div>
            <div class="activity-time">
              {{ formatDate(item.created_at) }}
            </div>
          </div>
          <div :class="['activity-status', item.status === 'success' ? 'status-success' : 'status-error']">
            {{ item.status }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Props
const props = defineProps({
  activity: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// Emits
defineEmits(['refresh-data']);

// Helper functions
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

/* Loading Spinner */
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Activity List */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.activity-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
}

.activity-content {
  flex: 1;
}

.activity-title {
  font-weight: 500;
  color: #1f2937;
  font-size: 0.875rem;
}

.activity-description {
  color: #6b7280;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.activity-time {
  color: #9ca3af;
  font-size: 0.6875rem;
  margin-top: 0.25rem;
}

.activity-status {
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
