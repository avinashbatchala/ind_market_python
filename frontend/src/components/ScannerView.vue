<template>
  <section class="scanner">
    <section class="hero">
      <div>
        <p class="eyebrow">{{ scannerTitle }}</p>
        <h1>Relative Strength & Volume Edge</h1>
        <p class="sub">Live snapshot of watchlisted stocks vs their industry index.</p>
      </div>
    </section>

    <section class="filters-bar">
      <div class="controls">
        <div class="filter-card">
          <span class="filter-title">Timeframe</span>
          <select v-model="timeframeModel">
            <option v-for="tf in timeframes" :key="tf" :value="tf">{{ tf }}</option>
          </select>
        </div>
        <div class="filter-card">
          <span class="filter-title">Signal</span>
          <select v-model="signalModel">
            <option value="ALL">All</option>
            <option value="TRIGGER_LONG">Trigger Long</option>
            <option value="TRIGGER_SHORT">Trigger Short</option>
            <option value="WATCH">Watch</option>
            <option value="NEUTRAL">Neutral</option>
            <option value="EXIT/AVOID">Exit/Avoid</option>
          </select>
        </div>
        <div class="range-group compact">
          <div class="range-head">
            <p class="range-title">RRS</p>
            <div class="range-values">
              <span>{{ formatRange(rrsMinModel) }}</span>
              <span>{{ formatRange(rrsMaxModel) }}</span>
            </div>
          </div>
          <div class="range-sliders">
            <input
              type="range"
              v-model.number="rrsMinModel"
              :min="rangeBounds.min"
              :max="rangeBounds.max"
              :step="rangeBounds.step"
            />
            <input
              type="range"
              v-model.number="rrsMaxModel"
              :min="rangeBounds.min"
              :max="rangeBounds.max"
              :step="rangeBounds.step"
            />
          </div>
        </div>
        <div class="range-group compact">
          <div class="range-head">
            <p class="range-title">RRV</p>
            <div class="range-values">
              <span>{{ formatRange(rrvMinModel) }}</span>
              <span>{{ formatRange(rrvMaxModel) }}</span>
            </div>
          </div>
          <div class="range-sliders">
            <input
              type="range"
              v-model.number="rrvMinModel"
              :min="rangeBounds.min"
              :max="rangeBounds.max"
              :step="rangeBounds.step"
            />
            <input
              type="range"
              v-model.number="rrvMaxModel"
              :min="rangeBounds.min"
              :max="rangeBounds.max"
              :step="rangeBounds.step"
            />
          </div>
        </div>
        <div class="range-group compact">
          <div class="range-head">
            <p class="range-title">RVE</p>
            <div class="range-values">
              <span>{{ formatRange(rveMinModel) }}</span>
              <span>{{ formatRange(rveMaxModel) }}</span>
            </div>
          </div>
          <div class="range-sliders">
            <input
              type="range"
              v-model.number="rveMinModel"
              :min="rangeBounds.min"
              :max="rangeBounds.max"
              :step="rangeBounds.step"
            />
            <input
              type="range"
              v-model.number="rveMaxModel"
              :min="rangeBounds.min"
              :max="rangeBounds.max"
              :step="rangeBounds.step"
            />
          </div>
        </div>
      </div>
    </section>

    <section class="table">
      <div class="table-head">
        <p>Updated: {{ lastUpdated }}</p>
        <p>Rows: {{ filteredRows.length }}</p>
      </div>
      <div class="grid">
        <div class="row header">
          <span>Symbol</span>
          <span>Index</span>
          <span>RRS</span>
          <span>RRV</span>
          <span>RVE</span>
          <span>Signal</span>
        </div>
        <div v-for="row in filteredRows" :key="row.symbol" class="row clickable" @click="emit('open-stock', row.symbol)">
          <span class="symbol">{{ row.symbol }}</span>
          <span>{{ row.benchmark_symbol || "-" }}</span>
          <span>{{ formatNum(row.rrs) }}</span>
          <span>{{ formatNum(row.rrv) }}</span>
          <span>{{ formatNum(row.rve) }}</span>
          <span :class="signalClass(row.signal)">{{ row.signal }}</span>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  scannerTitle: { type: String, required: true },
  timeframes: { type: Array, required: true },
  timeframe: { type: String, required: true },
  signalFilter: { type: String, required: true },
  rangeBounds: { type: Object, required: true },
  rrsMin: { type: Number, required: true },
  rrsMax: { type: Number, required: true },
  rrvMin: { type: Number, required: true },
  rrvMax: { type: Number, required: true },
  rveMin: { type: Number, required: true },
  rveMax: { type: Number, required: true },
  filteredRows: { type: Array, required: true },
  lastUpdated: { type: String, required: true },
});

const emit = defineEmits([
  "update:timeframe",
  "update:signalFilter",
  "update:rrsMin",
  "update:rrsMax",
  "update:rrvMin",
  "update:rrvMax",
  "update:rveMin",
  "update:rveMax",
  "open-stock",
]);

const timeframeModel = computed({
  get: () => props.timeframe,
  set: (value) => emit("update:timeframe", value),
});

const signalModel = computed({
  get: () => props.signalFilter,
  set: (value) => emit("update:signalFilter", value),
});

const rrsMinModel = computed({
  get: () => props.rrsMin,
  set: (value) => emit("update:rrsMin", value),
});

const rrsMaxModel = computed({
  get: () => props.rrsMax,
  set: (value) => emit("update:rrsMax", value),
});

const rrvMinModel = computed({
  get: () => props.rrvMin,
  set: (value) => emit("update:rrvMin", value),
});

const rrvMaxModel = computed({
  get: () => props.rrvMax,
  set: (value) => emit("update:rrvMax", value),
});

const rveMinModel = computed({
  get: () => props.rveMin,
  set: (value) => emit("update:rveMin", value),
});

const rveMaxModel = computed({
  get: () => props.rveMax,
  set: (value) => emit("update:rveMax", value),
});

const formatNum = (value) => {
  if (value === undefined || value === null) return "-";
  return Number(value).toFixed(2);
};

const formatRange = (value) => Number(value).toFixed(2);

const signalClass = (signal) => {
  if (!signal) return "";
  return signal.toLowerCase().replace("/", "");
};
</script>
