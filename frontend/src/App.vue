<template>
  <div class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Groww Scanner</p>
        <h1>Relative Strength & Volume Edge</h1>
        <p class="sub">Live snapshot of NIFTY 50 and Bank universe signals.</p>
      </div>
      <div class="controls">
        <label>
          Timeframe
          <select v-model="timeframe">
            <option v-for="tf in timeframes" :key="tf" :value="tf">{{ tf }}</option>
          </select>
        </label>
        <label>
          Signal
          <select v-model="signalFilter">
            <option value="ALL">All</option>
            <option value="TRIGGER_LONG">Trigger Long</option>
            <option value="WATCH">Watch</option>
            <option value="NEUTRAL">Neutral</option>
            <option value="EXIT/AVOID">Exit/Avoid</option>
          </select>
        </label>
        <label>
          Score ≥
          <input type="number" v-model.number="minScore" min="0" max="3" />
        </label>
      </div>
    </header>

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

    <section class="table">
      <div class="table-head">
        <p>Updated: {{ lastUpdated }}</p>
        <p>Rows: {{ filteredRows.length }}</p>
      </div>
      <div class="grid">
        <div class="row header">
          <span>Symbol</span>
          <span>RRS (NIFTY)</span>
          <span>RRV (NIFTY)</span>
          <span>RVE (NIFTY)</span>
          <span>Signal (NIFTY)</span>
          <span>RRS (BANK)</span>
          <span>RRV (BANK)</span>
          <span>RVE (BANK)</span>
          <span>Signal (BANK)</span>
          <span>Best</span>
        </div>
        <div v-for="row in filteredRows" :key="row.symbol" class="row">
          <span class="symbol">{{ row.symbol }}</span>
          <span>{{ formatNum(row.rrs_vs_nifty) }}</span>
          <span>{{ formatNum(row.rrv_vs_nifty) }}</span>
          <span>{{ formatNum(row.rve_vs_nifty) }}</span>
          <span :class="signalClass(row.signal_vs_nifty)">{{ row.signal_vs_nifty }}</span>
          <span>{{ formatNum(row.rrs_vs_bank) }}</span>
          <span>{{ formatNum(row.rrv_vs_bank) }}</span>
          <span>{{ formatNum(row.rve_vs_bank) }}</span>
          <span :class="signalClass(row.signal_vs_bank)">{{ row.signal_vs_bank }}</span>
          <span :class="signalClass(row.best_signal)">{{ row.best_signal }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

const timeframes = ["5m", "15m", "1h", "1d"];
const timeframe = ref("5m");
const signalFilter = ref("ALL");
const minScore = ref(0);

const rows = ref([]);
const benchmarks = ref([]);
const lastUpdated = ref("-");
let socket = null;

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const fetchScanner = async () => {
  const res = await fetch(`${apiBase}/scanner?timeframe=${timeframe.value}`);
  if (!res.ok) return;
  const data = await res.json();
  rows.value = data.rows || [];
  lastUpdated.value = data.ts || "-";
};

const fetchBenchmarks = async () => {
  const res = await fetch(`${apiBase}/benchmarks?timeframe=${timeframe.value}`);
  if (!res.ok) return;
  const data = await res.json();
  benchmarks.value = data.states || [];
};

const connectWS = () => {
  if (socket) {
    socket.close();
  }
  const wsBase = apiBase.replace("http", "ws");
  socket = new WebSocket(`${wsBase}/ws/scanner?timeframe=${timeframe.value}`);
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    rows.value = data.rows || [];
    lastUpdated.value = data.ts || "-";
  };
};

const filteredRows = computed(() => {
  return rows.value.filter((row) => {
    const score = Math.max(row.score_vs_nifty || 0, row.score_vs_bank || 0);
    if (score < minScore.value) return false;
    if (signalFilter.value === "ALL") return true;
    return row.best_signal === signalFilter.value;
  });
});

const benchmarkCards = computed(() => {
  return benchmarks.value.map((b) => ({
    benchmark: b.benchmark,
    regime: b.regime,
    trend: b.trend,
    vol_expansion: b.vol_expansion,
    participation: b.participation,
  }));
});

const formatNum = (value) => {
  if (value === undefined || value === null) return "-";
  return Number(value).toFixed(2);
};

const signalClass = (signal) => {
  if (!signal) return "";
  return signal.toLowerCase().replace("/", "");
};

watch(timeframe, async () => {
  await fetchScanner();
  await fetchBenchmarks();
  connectWS();
});

onMounted(async () => {
  await fetchScanner();
  await fetchBenchmarks();
  connectWS();
});
</script>

<style scoped>
.page {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.hero {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 24px;
  background: linear-gradient(120deg, rgba(43, 213, 118, 0.18), rgba(16, 20, 24, 0.1));
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 24px;
  border-radius: 16px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 3px;
  color: var(--muted);
  font-size: 12px;
}

h1 {
  margin: 8px 0 4px;
  font-size: 32px;
}

.sub {
  color: var(--muted);
}

.controls {
  display: grid;
  gap: 12px;
  align-content: start;
  min-width: 220px;
}

.controls label {
  font-size: 12px;
  color: var(--muted);
  display: grid;
  gap: 6px;
}

select,
input {
  background: var(--panel);
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 8px 10px;
  border-radius: 8px;
}

.benchmarks {
  margin: 24px 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.card {
  background: var(--panel);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 16px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.tag {
  font-weight: 600;
}

.badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.badge.bullish {
  background: rgba(43, 213, 118, 0.2);
  color: var(--accent);
}

.badge.bearish {
  background: rgba(243, 111, 111, 0.2);
  color: var(--danger);
}

.badge.neutral {
  background: rgba(240, 180, 41, 0.2);
  color: var(--accent-2);
}

.card-body {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric {
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.table {
  background: var(--panel);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px;
}

.table-head {
  display: flex;
  justify-content: space-between;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 12px;
}

.grid {
  display: grid;
  gap: 8px;
}

.row {
  display: grid;
  grid-template-columns: 1.2fr repeat(8, 1fr) 1fr;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.row.header {
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.symbol {
  font-weight: 600;
}

.trigger_long {
  color: var(--accent);
}

.watch {
  color: var(--accent-2);
}

.neutral {
  color: var(--muted);
}

.exitavoid {
  color: var(--danger);
}

@media (max-width: 1100px) {
  .row {
    grid-template-columns: 1.5fr repeat(4, 1fr);
    grid-auto-rows: auto;
  }
  .row span:nth-child(n + 6) {
    display: none;
  }
}
</style>
