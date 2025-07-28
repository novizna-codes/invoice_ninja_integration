<template>
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
        <button @click="$emit('test-connection')" class="btn btn-outline">
          Test Connection
        </button>
        <button @click="$emit('open-configuration')" class="btn btn-primary">
          Configure
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

// Props
const props = defineProps({
  config: {
    type: Object,
    required: true
  },
  stats: {
    type: Object,
    required: true
  }
});

// Emits
defineEmits(['test-connection', 'open-configuration']);

// Computed properties
const connectionStatus = computed(() => {
  if (!props.config.apiUrl || !props.config.apiToken) {
    return { text: 'Not Configured', color: 'text-gray-500', bg: 'bg-gray-100' };
  }
  if (props.config.isConnected) {
    return { text: 'Connected', color: 'text-green-700', bg: 'bg-green-100' };
  }
  return { text: 'Disconnected', color: 'text-red-700', bg: 'bg-red-100' };
});

const syncStatusDisplay = computed(() => {
  switch (props.stats.syncStatus) {
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
</script>

<style scoped>
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

.btn-primary {
  background-color: #2563eb;
  color: white;
}

.btn-primary:hover {
  background-color: #1d4ed8;
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

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
