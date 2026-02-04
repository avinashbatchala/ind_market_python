<template>
  <section class="indices">
    <section class="hero">
      <div>
        <p class="eyebrow">Indices</p>
        <h1>Index Regime Dashboard</h1>
        <p class="sub">Momentum + volume snapshot for watched indices.</p>
      </div>
    </section>

    <section class="filters-bar">
      <div class="controls indices-controls">
        <div class="filter-card">
          <span class="filter-title">Timeframe</span>
          <select v-model="timeframeModel">
            <option v-for="tf in timeframes" :key="tf" :value="tf">{{ tf }}</option>
          </select>
        </div>
      </div>
    </section>

    <section class="table-head">
      <p>Updated: {{ lastUpdated }}</p>
      <p>Indices: {{ benchmarkCards.length }}</p>
    </section>

    <section class="benchmarks">
      <div v-for="card in benchmarkCards" :key="card.benchmark" class="card">
        <div class="card-head">
          <span class="tag">{{ card.benchmark }}</span>
          <span class="badge" :class="card.regime.toLowerCase()">{{ card.regime }}</span>
        </div>
        <div class="card-body">
          <div>
            <p class="metric">Trend</p>
            <h3>{{ formatNum(card.trend) }}</h3>
          </div>
          <div>
            <p class="metric">Vol Expansion</p>
            <h3>{{ formatNum(card.vol_expansion) }}</h3>
          </div>
          <div>
            <p class="metric">Participation</p>
            <h3>{{ formatNum(card.participation) }}</h3>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  timeframes: { type: Array, required: true },
  timeframe: { type: String, required: true },
  benchmarkCards: { type: Array, required: true },
  lastUpdated: { type: String, required: true },
});

const emit = defineEmits(["update:timeframe"]);

const timeframeModel = computed({
  get: () => props.timeframe,
  set: (value) => emit("update:timeframe", value),
});

const formatNum = (value) => {
  if (value === undefined || value === null) return "-";
  return Number(value).toFixed(2);
};
</script>
