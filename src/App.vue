<script setup>
import BotStatus from './components/BotStatus.vue'
import DevControls from './components/DevControls.vue'
import SeriesStatus from './components/SeriesStatus.vue'
import StakeHistory from './components/StakeHistory.vue'
import StrategyForm from './components/StrategyForm.vue'
import TeamQueue from './components/TeamQueue.vue'
import { useBetStrategy } from './composables/useBetStrategy'

const strategy = useBetStrategy()
</script>

<template>
  <main class="app">
    <section class="container">
      <header class="hero">
        <div>
          <div class="overline">LIVE BET CONTROL</div>
          <h1>Автобот</h1>
          <p>
            Очередь команд для стратегии «Следующий гол». Каждая команда проходит
            собственный независимый цикл ставок до завершения её LIVE-матча.
          </p>
        </div>

        <BotStatus :running="strategy.running.value" :queue-status="strategy.queueStatus.value" />
      </header>

      <section class="layout">
        <StrategyForm
          :team-inputs="strategy.teamInputs.value"
          :initial-stake="strategy.initialStake.value"
          :running="strategy.running.value"
          :error="strategy.validationError.value"
          @update:team="strategy.updateTeamInput"
          @update:initial-stake="strategy.updateInitialStake"
          @start="strategy.startQueue"
          @stop="strategy.stopQueue"
        />

        <SeriesStatus
          :active-team="strategy.activeTeam.value"
          :active-position="strategy.activeTeamPosition.value"
          :teams-count="strategy.teams.value.length"
          :status-text="strategy.statusText.value"
          :step="strategy.step.value"
          :current-stake="strategy.currentStake.value"
          :initial-stake="strategy.normalizedInitialStake.value"
          :consecutive-losses="strategy.consecutiveLosses.value"
          :mode="strategy.mode.value"
          :current-match="strategy.currentMatch.value"
          :current-score="strategy.currentScore.value"
          :current-odds="strategy.currentOdds.value"
        />
      </section>

      <section class="dashboard-grid">
        <TeamQueue
          :teams="strategy.teams.value"
          :queue-status="strategy.queueStatus.value"
          :active-team-index="strategy.activeTeamIndex.value"
        />

        <StakeHistory :items="strategy.stakeHistory.value" />
      </section>

      <DevControls
        :disabled="!strategy.running.value"
        :queue-finished="strategy.queueStatus.value === 'QUEUE_FINISHED'"
        @lose="strategy.handleLose"
        @win="strategy.handleWin"
        @match-finished="strategy.finishCurrentTeam"
        @new-market="strategy.simulateNewMarket"
        @random-odds="strategy.randomizeOdds"
      />
    </section>
  </main>
</template>
