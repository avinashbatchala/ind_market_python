<template>
  <div class="page">
    <header class="site-header">
      <div class="brand">
        <div class="brand-mark"></div>
        <div>
          <p class="brand-title">Groww Scanner</p>
          <p class="brand-sub">Relative strength + volume edge for NIFTY and Bank</p>
        </div>
      </div>
      <nav class="nav">
        <button class="nav-btn" :class="{ active: view === 'scanner' }" @click="setView('scanner')">
          Scanner
        </button>
        <button class="nav-btn" :class="{ active: view === 'scores' }" @click="setView('scores')">
          Scores
        </button>
      </nav>
    </header>

    <section v-if="view === 'scanner'" class="scanner">
      <section class="hero">
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
    </section>

    <section v-else class="scores">
      <section class="scores-hero">
        <div>
          <p class="eyebrow">Scores</p>
          <h1>How we compute and interpret signals</h1>
          <p class="sub">
            Each symbol is evaluated against NIFTY and BANKNIFTY using aligned candles. The three metrics
            below drive the score and signal rules.
          </p>
        </div>
        <div class="scores-facts">
          <div>
            <p class="metric">Window</p>
            <h3>12 bars</h3>
          </div>
          <div>
            <p class="metric">ATR</p>
            <h3>14 bars</h3>
          </div>
          <div>
            <p class="metric">Min aligned</p>
            <h3>30 candles</h3>
          </div>
        </div>
      </section>

      <section class="scores-grid">
        <article class="score-card">
          <h3>RRS — Relative Strength</h3>
          <p>
            Compares the symbol's price move to the benchmark's move, normalized by the symbol's ATR.
          </p>
          <ul class="score-list">
            <li><strong>RRS &gt; 0</strong> = volatility-adjusted outperformance.</li>
            <li><strong>RRS &lt; 0</strong> = underperformance.</li>
          </ul>
        </article>
        <article class="score-card">
          <h3>RRV — Relative Volume</h3>
          <p>
            Checks if the symbol's volume is expanding faster than expected vs the benchmark (3-bar SMA,
            log-smoothed).
          </p>
          <ul class="score-list">
            <li><strong>RRV &gt; 0</strong> = relative volume expansion.</li>
            <li><strong>RRV &lt; 0</strong> = relative contraction.</li>
          </ul>
        </article>
        <article class="score-card">
          <h3>RVE — Relative Volatility Expansion</h3>
          <p>
            Compares ATR expansion between the symbol and the benchmark (ATR uses 14-bar Wilder RMA).
          </p>
          <ul class="score-list">
            <li><strong>RVE &gt; 0</strong> = volatility expanding faster than benchmark.</li>
            <li><strong>RVE &lt; 0</strong> = volatility contracting.</li>
          </ul>
        </article>
      </section>

      <section class="score-breakdown">
        <article class="score-block">
          <h3>Score (0–3)</h3>
          <p>Score counts how many of the three components are positive.</p>
          <div class="formula">score = (RRS &gt; 0) + (RRV &gt; 0) + (RVE &gt; 0)</div>
          <ul class="score-list">
            <li><strong>3</strong> = strength + volume + volatility expansion.</li>
            <li><strong>0</strong> = all three are negative.</li>
          </ul>
        </article>
        <article class="score-block">
          <h3>Signals</h3>
          <ul class="score-list">
            <li><strong>TRIGGER_LONG</strong>: RRS crosses up through 0 and RRV &gt; 0 and RVE &gt; 0.</li>
            <li><strong>WATCH</strong>: RRV &gt; 0 and RVE &gt; 0, but RRS still &lt; 0 and rising.</li>
            <li><strong>EXIT/AVOID</strong>: RRS crosses down through 0 or RRV &lt; 0 or RVE &lt; 0.</li>
            <li><strong>NEUTRAL</strong>: none of the above.</li>
          </ul>
        </article>
      </section>

      <section class="score-footnote">
        <div>
          <h3>Benchmark comparison</h3>
          <p>
            Each symbol is scored against both benchmarks. The UI chooses the better of the two signals
            as <strong>best_signal</strong> using priority:
          </p>
          <div class="formula">TRIGGER_LONG &gt; WATCH &gt; NEUTRAL &gt; EXIT/AVOID</div>
        </div>
        <div>
          <h3>Ranking</h3>
          <p>Rows are ordered by best signal, then by the higher score, then by the higher RVE.</p>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const timeframes = ["5m", "15m", "1h", "1d"];
const timeframe = ref("5m");
const signalFilter = ref("ALL");
const minScore = ref(0);
const view = ref("scanner");

const rows = ref([]);
const benchmarks = ref([]);
const lastUpdated = ref("-");
let socket = null;
let hashListener = null;

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

const stopWS = () => {
  if (socket) {
    socket.close();
    socket = null;
  }
};

const refreshScanner = async () => {
  if (view.value !== "scanner") return;
  await fetchScanner();
  await fetchBenchmarks();
  connectWS();
};

const setView = (next) => {
  view.value = next;
  if (typeof window !== "undefined") {
    window.location.hash = next === "scores" ? "scores" : "";
  }
};

const syncFromHash = () => {
  if (typeof window === "undefined") return;
  view.value = window.location.hash === "#scores" ? "scores" : "scanner";
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
  await refreshScanner();
});

watch(view, async (next) => {
  if (next === "scanner") {
    await refreshScanner();
  } else {
    stopWS();
  }
});

onMounted(async () => {
  syncFromHash();
  hashListener = () => syncFromHash();
  window.addEventListener("hashchange", hashListener);
  if (view.value === "scanner") {
    await refreshScanner();
  }
});

onBeforeUnmount(() => {
  stopWS();
  if (hashListener) {
    window.removeEventListener("hashchange", hashListener);
  }
});
</script>

<style scoped>
.page {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 16px;
  background: rgba(14, 20, 26, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(12px);
  margin-bottom: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(43, 213, 118, 0.6), rgba(240, 180, 41, 0.4));
  box-shadow: 0 12px 30px rgba(43, 213, 118, 0.2);
}

.brand-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.brand-sub {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.nav {
  display: flex;
  gap: 10px;
}

.nav-btn {
  background: transparent;
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-btn:hover {
  border-color: rgba(255, 255, 255, 0.3);
}

.nav-btn.active {
  background: rgba(43, 213, 118, 0.18);
  border-color: rgba(43, 213, 118, 0.4);
  color: var(--accent);
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

.scores {
  display: grid;
  gap: 24px;
}

.scores-hero {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 24px;
  background: linear-gradient(120deg, rgba(240, 180, 41, 0.18), rgba(16, 20, 24, 0.1));
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 24px;
  border-radius: 16px;
}

.scores-facts {
  display: grid;
  gap: 16px;
  align-content: start;
  min-width: 220px;
}

.scores-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.score-card,
.score-block {
  background: var(--panel);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 18px;
}

.score-card h3,
.score-block h3,
.score-footnote h3 {
  margin-top: 0;
}

.score-list {
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--muted);
}

.score-list li {
  margin-bottom: 6px;
}

.score-breakdown {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.formula {
  margin: 12px 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-family: "Space Grotesk", "Segoe UI", sans-serif;
  color: var(--text);
}

.score-footnote {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  background: rgba(20, 28, 34, 0.75);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 18px;
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

@media (max-width: 900px) {
  .site-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .nav {
    width: 100%;
  }
  .nav-btn {
    flex: 1;
  }
}
</style>
