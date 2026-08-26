<script setup>
defineProps({ items: { type: Array, required: true } })
</script>

<template>
  <section class="panel history-panel">
    <div class="panel-head compact">
      <div>
        <span>ПОСЛЕДНИЕ СОБЫТИЯ</span>
        <h2>История ставок</h2>
      </div>
    </div>

    <div v-if="items.length" class="history-list">
      <article v-for="item in items" :key="item.id">
        <div>
          <strong>{{ item.team }}</strong>
          <small>Шаг {{ item.step }} · {{ item.stake.toLocaleString('ru-RU') }} ₽</small>
        </div>
        <b :class="item.result.toLowerCase()">{{ item.result }}</b>
      </article>
    </div>
    <div v-else class="empty-state">Здесь появятся результаты тестовых ставок.</div>
  </section>
</template>
