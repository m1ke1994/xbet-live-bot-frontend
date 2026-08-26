<script setup>
defineProps({
  teamInputs: { type: Array, required: true },
  initialStake: { type: [String, Number], required: true },
  running: Boolean,
  error: { type: String, default: '' },
})

defineEmits(['update:team', 'update:initialStake', 'start', 'stop'])
</script>

<template>
  <div class="panel config">
    <div class="panel-head">
      <div>
        <span>НАСТРОЙКА</span>
        <h2>Очередь стратегии</h2>
      </div>
      <b>LIVE</b>
    </div>

    <div class="team-fields">
      <label v-for="(_, index) in teamInputs" :key="index">
        <span>Команда {{ index + 1 }}</span>
        <input
          :value="teamInputs[index]"
          :disabled="running"
          type="text"
          autocomplete="off"
          :placeholder="index === 0 ? 'Например: Manchester United' : 'Необязательно'"
          @input="$emit('update:team', index, $event.target.value)"
        />
      </label>
    </div>

    <label>
      <span>Первоначальная ставка</span>
      <div class="money-input">
        <input
          :value="initialStake"
          :disabled="running"
          type="number"
          min="1"
          step="1"
          @input="$emit('update:initialStake', $event.target.value)"
        />
        <strong>₽</strong>
      </div>
    </label>

    <div class="market">
      <span>Рынок</span>
      <strong>Следующий гол — активная команда</strong>
    </div>

    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <div class="buttons">
      <button class="start" :disabled="running" @click="$emit('start')">Запустить</button>
      <button class="stop" :disabled="!running" @click="$emit('stop')">Остановить</button>
    </div>
  </div>
</template>
