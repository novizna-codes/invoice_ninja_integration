<template>
  <div v-if="error" class="alert alert-error mb-6">
    <div class="alert-content">
      <strong>Error:</strong> {{ error }}
      <button @click="$emit('close-error')" class="alert-close">&times;</button>
    </div>
  </div>
</template>

<script setup>
// Props
const props = defineProps({
  error: {
    type: String,
    default: null
  }
});

// Emits
defineEmits(['close-error']);
</script>

<style scoped>
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
</style>
