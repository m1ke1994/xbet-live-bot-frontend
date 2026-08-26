<script setup>
import { computed } from 'vue'

const props = defineProps({
  running: Boolean,
  queueStatus: { type: String, required: true },
})

const label = computed(() => {
  if (props.queueStatus === 'QUEUE_FINISHED') return 'Очередь завершена'
  return props.running ? 'Работает' : 'Остановлен'
})
</script>

<template>
  <div class="bot-state" :class="{ online: running, finished: queueStatus === 'QUEUE_FINISHED' }">
    <i></i>
    {{ label }}
  </div>
</template>
