<script setup>
import { computed } from 'vue'

const props = defineProps({
  activeTeam: { type: Object, default: null },
  activePosition: { type: Number, default: 0 },
  teamsCount: { type: Number, default: 0 },
  statusText: { type: String, required: true },
  step: { type: Number, required: true },
  currentStake: { type: Number, required: true },
  initialStake: { type: Number, required: true },
  consecutiveLosses: { type: Number, required: true },
  mode: { type: String, required: true },
  currentMatch: { type: String, required: true },
  currentScore: { type: String, required: true },
  currentOdds: { type: Number, default: null },
})

const timeline = computed(() => {
  const current = Math.max(props.step, 1)
  const first = Math.max(1, current - 1)
  return [first, first + 1, first + 2].map((step) => ({
    step,
    amount: props.initialStake * 2 ** (step - 1),
  }))
})

function money(value) {
  return Number(value || 0).toLocaleString('ru-RU')
}
</script>

<template>
  <div class="panel monitor">
    <div class="panel-head">
      <div>
        <span>СОСТОЯНИЕ</span>
        <h2>Текущая серия</h2>
      </div>
      <div class="signal" :class="{ online: activeTeam }"></div>
    </div>

    <div class="active-team-card" :class="{ empty: !activeTeam }">
      <div>
        <span>Активная команда</span>
        <strong>{{ activeTeam?.name || 'Очередь не запущена' }}</strong>
      </div>
      <b v-if="activeTeam">Команда {{ activePosition }} из {{ teamsCount }}</b>
    </div>

    <div class="status-card">
      <span>СТАТУС</span>
      <strong>{{ statusText }}</strong>
    </div>

    <div class="stats">
      <article>
        <span>LIVE-матч</span>
        <strong>{{ currentMatch }}</strong>
      </article>
      <article>
        <span>Счёт</span>
        <strong>{{ currentScore }}</strong>
      </article>
      <article>
        <span>Текущая ставка</span>
        <strong>{{ money(currentStake) }} ₽</strong>
      </article>
      <article>
        <span>Коэффициент</span>
        <strong>{{ currentOdds ?? '—' }}</strong>
      </article>
      <article>
        <span>Шаг</span>
        <strong>{{ step }}</strong>
      </article>
      <article>
        <span>Поражений подряд</span>
        <strong>{{ consecutiveLosses }}</strong>
      </article>
    </div>

    <div v-if="mode === 'UNTIL_WIN'" class="chase-badge">ДОГОН ДО ПОБЕДЫ</div>

    <div class="sequence">
      <template v-for="(item, index) in timeline" :key="item.step">
        <i v-if="index">→</i>
        <div :class="{ active: item.step === step }">
          <small>Шаг {{ item.step }}</small>
          <strong>{{ money(item.amount) }} ₽</strong>
        </div>
      </template>
    </div>
  </div>
</template>
