<template>
  <div class="stats-grid mb-8">
    <div class="stat-card clickable" @click="$emit('open-invoice-list')">
      <div class="stat-icon stat-icon-blue">
        📄
      </div>
      <div class="stat-content">
        <div class="stat-number">{{ loading ? '...' : stats.totalInvoices }}</div>
        <div class="stat-label">Total Invoices</div>
        <div class="stat-sublabel">Synced from Invoice Ninja</div>
      </div>
    </div>

    <div class="stat-card clickable" @click="$emit('open-customer-list')">
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
</template>

<script setup>
// Props
const props = defineProps({
  stats: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// Emits
defineEmits(['open-invoice-list', 'open-customer-list']);
</script>

<style scoped>
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

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
