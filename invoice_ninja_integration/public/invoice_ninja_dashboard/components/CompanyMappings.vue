<template>
  <div class="dashboard-card mb-6">
    <div class="card-header">
      <h2 class="text-lg font-semibold text-gray-900">🏢 Company Mappings</h2>
      <button @click="$emit('refresh-mappings')" class="refresh-button" :disabled="loading">
        {{ loading ? '...' : '↻ Refresh' }}
      </button>
    </div>

    <div class="card-content">
      <div v-if="mappings.length === 0" class="empty-state">
        <p class="text-gray-600">No company mappings configured</p>
        <button @click="$emit('open-settings')" class="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Configure Mappings
        </button>
      </div>
      <div v-else class="company-mappings-list">
        <div v-for="mapping in mappings" :key="mapping.invoice_ninja_company_id"
             class="mapping-item" :class="{ 'default-mapping': mapping.is_default }">
          <div class="mapping-info">
            <strong>{{ mapping.erpnext_company }}</strong>
            <span class="mapping-arrow">↔</span>
            <span>{{ mapping.invoice_ninja_company_name }}</span>
            <span v-if="mapping.is_default" class="default-badge">Default</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Props
const props = defineProps({
  mappings: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// Emits
defineEmits(['refresh-mappings', 'open-settings']);
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

/* Company Mappings */
.company-mappings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mapping-item {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  transition: all 0.2s;
}

.mapping-item:hover {
  border-color: #2563eb;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.mapping-item.default-mapping {
  border-color: #10b981;
  background: #f0fdf4;
}

.mapping-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.mapping-arrow {
  color: #6b7280;
  font-weight: bold;
}

.default-badge {
  background: #10b981;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 12px;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.empty-state {
  text-align: center;
  padding: 24px;
}

.refresh-button {
  background: none;
  border: 1px solid #e5e7eb;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.refresh-button:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.refresh-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .company-mappings-list {
    gap: 8px;
  }

  .mapping-item {
    padding: 8px;
  }

  .mapping-info {
    font-size: 12px;
    gap: 6px;
  }
}
</style>
