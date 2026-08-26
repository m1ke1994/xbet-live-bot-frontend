<script setup>
defineProps({
  disabled: Boolean,
  queueFinished: Boolean,
})

defineEmits(['lose', 'win', 'matchFinished', 'newMarket', 'randomOdds'])
</script>

<template>
  <section class="panel dev-panel">
    <div>
      <span>DEV-ПАНЕЛЬ · MOCK MODE</span>
      <p>Локальная симуляция событий до подключения backend.</p>
    </div>
    <div class="dev-buttons">
      <button class="danger" :disabled="disabled" @click="$emit('lose')">Сымитировать LOSE</button>
      <button class="success" :disabled="disabled" @click="$emit('win')">Сымитировать WIN</button>
      <button :disabled="disabled" @click="$emit('matchFinished')">MATCH_FINISHED</button>
      <button :disabled="disabled" @click="$emit('newMarket')">Новый рынок</button>
      <button :disabled="disabled" @click="$emit('randomOdds')">Случайный коэффициент</button>
    </div>
    <strong v-if="queueFinished" class="finished-message">BOT STOPPED · QUEUE_FINISHED</strong>
  </section>
</template>
