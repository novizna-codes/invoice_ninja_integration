<script setup>
import { ref, computed, onMounted } from 'vue';

// Reactive state
const loading = ref(false);
</script>

<template>
  <div class="invoice-ninja-dashboard p-6 max-w-7xl mx-auto">
    <Card class="mb-6">
      <template #header>
        <h2 class="text-xl font-semibold">Invoice Ninja Dashboard</h2>
      </template>
      <div v-if="loading" class="text-center py-4">
        <frappe-ui-spinner />
      </div>
      <div v-else>
        <div class="mb-4">
          <!-- Dashboard content goes here -->
          <p>Welcome to Invoice Ninja Dashboard</p>
        </div>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.invoice-ninja-dashboard {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}
</style>