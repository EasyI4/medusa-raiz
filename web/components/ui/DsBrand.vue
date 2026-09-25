<script setup lang="ts">
import DsIcon from "./DsIcon.vue"

withDefaults(defineProps<{
  subtitle?: string
  compact?: boolean
}>(), {
  subtitle: "Assistente de autopeças",
  compact: false,
})
</script>

<template>
  <div class="ds-brand">
    <span class="ds-brand__mark"><DsIcon name="wrench" /></span>
    <div v-if="!compact" class="ds-brand__copy">
      <strong>AUTOCENTER IA</strong>
      <span>{{ subtitle }}</span>
    </div>
  </div>
</template>
