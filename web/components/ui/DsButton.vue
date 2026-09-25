<script setup lang="ts">
import DsIcon from "./DsIcon.vue"

type IconName = "car" | "history" | "lock" | "logout" | "mail" | "menu" | "message" | "plus" | "search" | "send" | "shield" | "sparkles" | "trash" | "user" | "wrench" | "x"

withDefaults(defineProps<{
  variant?: "primary" | "secondary" | "ghost" | "danger"
  size?: "sm" | "md" | "lg"
  icon?: IconName
  iconOnly?: boolean
  block?: boolean
}>(), {
  variant: "primary",
  size: "md",
  icon: undefined,
  iconOnly: false,
  block: false,
})
</script>

<template>
  <button
    class="ds-button"
    :class="[
      `ds-button--${variant}`,
      `ds-button--${size}`,
      { 'ds-button--icon': iconOnly, 'ds-button--block': block },
    ]"
  >
    <DsIcon v-if="icon" :name="icon" />
    <slot />
  </button>
</template>
