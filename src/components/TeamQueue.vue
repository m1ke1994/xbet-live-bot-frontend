<script setup>
defineProps({
  teams: { type: Array, required: true },
  queueStatus: { type: String, required: true },
  activeTeamIndex: { type: Number, required: true },
})

const labels = {
  WAITING: 'WAITING',
  ACTIVE: 'ACTIVE',
  FINISHED: 'FINISHED',
  SKIPPED: 'SKIPPED',
}

function icon(status) {
  if (status === 'FINISHED') return '✓'
  if (status === 'ACTIVE') return '●'
  if (status === 'SKIPPED') return '–'
  return '○'
}
</script>

<template>
  <section class="panel queue-panel">
    <div class="panel-head compact">
      <div>
        <span>ПОРЯДОК РАБОТЫ</span>
        <h2>Очередь команд</h2>
      </div>
      <b v-if="queueStatus === 'QUEUE_FINISHED'" class="queue-done">QUEUE_FINISHED</b>
    </div>

    <div v-if="teams.length" class="queue-list">
      <article v-for="(team, index) in teams" :key="team.id" :class="team.status.toLowerCase()">
        <span class="queue-number">{{ index + 1 }}</span>
        <div>
          <strong>{{ team.name }}</strong>
          <small v-if="index === activeTeamIndex">Текущая цель</small>
          <small v-else-if="team.status === 'WAITING'">Следующая в очереди</small>
          <small v-else-if="team.status === 'FINISHED'">Матч завершён</small>
        </div>
        <b class="queue-status"><i>{{ icon(team.status) }}</i> {{ labels[team.status] }}</b>
      </article>
    </div>

    <div v-else class="empty-state">Заполните от одной до трёх команд и запустите очередь.</div>
  </section>
</template>
