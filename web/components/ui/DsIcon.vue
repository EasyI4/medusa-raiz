<script setup lang="ts">
type IconName =
  | "car"
  | "history"
  | "lock"
  | "logout"
  | "mail"
  | "menu"
  | "message"
  | "plus"
  | "search"
  | "send"
  | "shield"
  | "sparkles"
  | "trash"
  | "user"
  | "wrench"
  | "x"

defineProps<{ name: IconName }>()
</script>

<template>
  <svg class="ds-icon" viewBox="0 0 24 24" aria-hidden="true">
    <template v-if="name === 'wrench'">
      <path d="M14.7 6.3a4.5 4.5 0 0 0-5.9 5.9L3 18l3 3 5.8-5.8a4.5 4.5 0 0 0 5.9-5.9l-2.8 2.8-3-3 2.8-2.8Z" />
    </template>
    <template v-else-if="name === 'plus'">
      <path d="M12 5v14M5 12h14" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" />
    </template>
    <template v-else-if="name === 'send'">
      <path d="M12 19V5M6.5 10.5 12 5l5.5 5.5" />
    </template>
    <template v-else-if="name === 'menu'">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </template>
    <template v-else-if="name === 'logout'">
      <path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" />
    </template>
    <template v-else-if="name === 'user'">
      <circle cx="12" cy="8" r="3.5" /><path d="M5 20c.8-4 3.1-6 7-6s6.2 2 7 6" />
    </template>
    <template v-else-if="name === 'mail'">
      <rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" />
    </template>
    <template v-else-if="name === 'lock'">
      <rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </template>
    <template v-else-if="name === 'car'">
      <path d="m5 11 1.5-4h11l1.5 4M3.5 14v-2l2-1h13l2 1v5H3.5v-3Z" /><circle cx="7" cy="17" r="1.5" /><circle cx="17" cy="17" r="1.5" />
    </template>
    <template v-else-if="name === 'message'">
      <path d="M4 5h16v11H8l-4 4V5Z" /><path d="M8 9h8M8 12h5" />
    </template>
    <template v-else-if="name === 'history'">
      <path d="M4 5v5h5M4.7 10A8 8 0 1 1 6 17.3M12 8v5l3 2" />
    </template>
    <template v-else-if="name === 'shield'">
      <path d="M12 3 5 6v5c0 4.6 2.8 8 7 10 4.2-2 7-5.4 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" />
    </template>
    <template v-else-if="name === 'sparkles'">
      <path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3ZM5.5 14l.8 2.2 2.2.8-2.2.8L5.5 20l-.8-2.2-2.2-.8 2.2-.8.8-2.2ZM18 13l.8 2.2 2.2.8-2.2.8L18 19l-.8-2.2L15 16l2.2-.8L18 13Z" />
    </template>
    <template v-else-if="name === 'x'">
      <path d="m6 6 12 12M18 6 6 18" />
    </template>
  </svg>
</template>
