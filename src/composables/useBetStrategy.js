import { computed, ref, watch } from 'vue'

const STORAGE_KEYS = {
  teams: ['team1', 'team2', 'team3'],
  initialStake: 'initialStake',
}

function readStorage(key, fallback = '') {
  if (typeof window === 'undefined') return fallback
  return window.localStorage.getItem(key) ?? fallback
}

export function useBetStrategy() {
  const teamInputs = ref(STORAGE_KEYS.teams.map((key) => readStorage(key)))
  const initialStake = ref(readStorage(STORAGE_KEYS.initialStake, '100'))
  const teams = ref([])
  const activeTeamIndex = ref(-1)
  const queueStatus = ref('STOPPED')
  const running = ref(false)
  const validationError = ref('')

  const step = ref(1)
  const consecutiveLosses = ref(0)
  const currentStake = ref(Number(initialStake.value) || 100)
  const mode = ref('NORMAL')

  const statusText = ref('Остановлен')
  const currentMatch = ref('—')
  const currentScore = ref('—')
  const currentOdds = ref(null)
  const stakeHistory = ref([])

  const normalizedInitialStake = computed(() => Number(initialStake.value) || 0)
  const activeTeam = computed(() => teams.value[activeTeamIndex.value] ?? null)
  const activeTeamPosition = computed(() =>
    activeTeamIndex.value >= 0 ? activeTeamIndex.value + 1 : 0,
  )

  function updateTeamInput(index, value) {
    teamInputs.value[index] = value
    validationError.value = ''
  }

  function updateInitialStake(value) {
    initialStake.value = value
    validationError.value = ''
    if (!running.value && Number(value) > 0) currentStake.value = Number(value)
  }

  function resetSeries() {
    step.value = 1
    consecutiveLosses.value = 0
    currentStake.value = normalizedInitialStake.value
    mode.value = 'NORMAL'
  }

  function startQueue() {
    const enteredTeams = teamInputs.value
      .map((name, sourceIndex) => ({ name: name.trim(), sourceIndex }))
      .filter(({ name }) => name)

    if (!enteredTeams.length) {
      validationError.value = 'Введите хотя бы одну команду'
      return false
    }

    if (!Number.isFinite(normalizedInitialStake.value) || normalizedInitialStake.value <= 0) {
      validationError.value = 'Введите корректную первоначальную сумму'
      return false
    }

    teams.value = enteredTeams.map(({ name, sourceIndex }, index) => ({
      id: sourceIndex + 1,
      name,
      status: index === 0 ? 'ACTIVE' : 'WAITING',
    }))
    activeTeamIndex.value = 0
    queueStatus.value = 'ACTIVE'
    running.value = true
    validationError.value = ''
    stakeHistory.value = []
    resetSeries()
    clearMatchData()
    statusText.value = 'Готов к поиску LIVE-матча'
    return true
  }

  function stopQueue() {
    running.value = false
    queueStatus.value = 'STOPPED'
    statusText.value = 'Остановлен пользователем'
    clearMatchData()
    resetSeries()
  }

  function activateNextTeam() {
    const nextIndex = teams.value.findIndex(
      (team, index) => index > activeTeamIndex.value && team.status === 'WAITING',
    )

    if (nextIndex === -1) {
      finishQueue()
      return false
    }

    activeTeamIndex.value = nextIndex
    teams.value[nextIndex].status = 'ACTIVE'
    resetSeries()
    clearMatchData()
    statusText.value = 'Готов к поиску LIVE-матча'
    return true
  }

  function finishCurrentTeam() {
    if (!running.value || !activeTeam.value) return
    activeTeam.value.status = 'FINISHED'
    resetSeries()
    activateNextTeam()
  }

  function finishQueue() {
    activeTeamIndex.value = -1
    queueStatus.value = 'QUEUE_FINISHED'
    running.value = false
    statusText.value = 'Все команды обработаны'
    clearMatchData()
    resetSeries()
  }

  function addHistory(result, stake) {
    stakeHistory.value.unshift({
      id: `${Date.now()}-${stakeHistory.value.length}`,
      team: activeTeam.value?.name ?? '—',
      result,
      stake,
      step: step.value,
    })
    stakeHistory.value = stakeHistory.value.slice(0, 8)
  }

  function handleLose() {
    if (!running.value || !activeTeam.value) return
    addHistory('LOSE', currentStake.value)
    consecutiveLosses.value += 1
    step.value += 1
    currentStake.value *= 2
    mode.value = consecutiveLosses.value >= 3 ? 'UNTIL_WIN' : 'NORMAL'
    statusText.value = `Проигрыш. Следующая ставка ${formatMoney(currentStake.value)}`
  }

  function handleWin() {
    if (!running.value || !activeTeam.value) return
    addHistory('WIN', currentStake.value)
    resetSeries()
    statusText.value = 'Выигрыш. Серия сброшена, команда остаётся активной'
  }

  function simulateNewMarket() {
    if (!running.value || !activeTeam.value) return
    const opponents = ['Arsenal', 'Liverpool', 'Tottenham', 'Aston Villa']
    const opponent = opponents[Math.floor(Math.random() * opponents.length)]
    currentMatch.value = `${activeTeam.value.name} — ${opponent}`
    currentScore.value = `${Math.floor(Math.random() * 3)}:${Math.floor(Math.random() * 3)}`
    randomizeOdds()
    statusText.value = 'Рынок «Следующий гол» найден'
  }

  function randomizeOdds() {
    if (!running.value) return
    currentOdds.value = Number((1.55 + Math.random() * 1.25).toFixed(2))
  }

  function clearMatchData() {
    currentMatch.value = '—'
    currentScore.value = '—'
    currentOdds.value = null
  }

  function applyBackendState(payload) {
    if (!payload || !Array.isArray(payload.teams)) return
    teams.value = payload.teams.map((team, index) => ({
      id: team.id ?? index + 1,
      name: team.name,
      status: team.status,
    }))
    activeTeamIndex.value = Number(payload.activeTeamIndex ?? -1)
    queueStatus.value = payload.status === 'QUEUE_FINISHED' ? 'QUEUE_FINISHED' : 'ACTIVE'
    running.value = queueStatus.value !== 'QUEUE_FINISHED'
    currentMatch.value = payload.currentMatch ?? '—'
    currentScore.value = payload.currentScore ?? '—'
    currentOdds.value = payload.currentOdds ?? null
    step.value = Number(payload.step ?? 1)
    consecutiveLosses.value = Number(payload.consecutiveLosses ?? 0)
    currentStake.value = Number(payload.currentStake ?? normalizedInitialStake.value)
    mode.value = consecutiveLosses.value >= 3 ? 'UNTIL_WIN' : 'NORMAL'
    statusText.value = payload.status ?? 'Состояние получено'
  }

  watch(
    teamInputs,
    (values) => {
      if (typeof window === 'undefined') return
      values.forEach((value, index) => window.localStorage.setItem(STORAGE_KEYS.teams[index], value))
    },
    { deep: true },
  )

  watch(initialStake, (value) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEYS.initialStake, String(value ?? ''))
    }
  })

  return {
    teamInputs,
    initialStake,
    normalizedInitialStake,
    teams,
    activeTeamIndex,
    activeTeam,
    activeTeamPosition,
    queueStatus,
    running,
    validationError,
    step,
    consecutiveLosses,
    currentStake,
    mode,
    statusText,
    currentMatch,
    currentScore,
    currentOdds,
    stakeHistory,
    updateTeamInput,
    updateInitialStake,
    startQueue,
    stopQueue,
    activateNextTeam,
    finishCurrentTeam,
    finishQueue,
    resetSeries,
    handleWin,
    handleLose,
    simulateNewMarket,
    randomizeOdds,
    applyBackendState,
  }
}

function formatMoney(value) {
  return `${Number(value).toLocaleString('ru-RU')} ₽`
}
