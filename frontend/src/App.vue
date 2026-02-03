<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark"></div>
        <div>
          <p class="brand-title">Groww Scanner</p>
          <p class="brand-sub">Relative strength + volume edge</p>
        </div>
      </div>

      <nav class="side-nav">
        <button class="side-link" :class="{ active: view === 'bullish' }" @click="setView('bullish')">
          <span class="icon-wrap bull">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M4 8c1-2 3-3 5-3l1 2M20 8c-1-2-3-3-5-3l-1 2M7 14c0-3 2-5 5-5s5 2 5 5-2 5-5 5-5-2-5-5z"
              />
            </svg>
          </span>
          Bullish scanner
        </button>
        <button class="side-link" :class="{ active: view === 'bearish' }" @click="setView('bearish')">
          <span class="icon-wrap bear">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M6 6l-2 2 3 1M18 6l2 2-3 1M7 15c0-3 2-5 5-5s5 2 5 5-2 5-5 5-5-2-5-5z"
              />
            </svg>
          </span>
          Bearish scanner
        </button>
        <button class="side-link" :class="{ active: view === 'scores' }" @click="setView('scores')">
          <span class="icon-wrap info">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 7.5v.1M12 10v6" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </span>
          Scores & docs
        </button>
        <button class="side-link" :class="{ active: view === 'manage' }" @click="setView('manage')">
          <span class="icon-wrap manage">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
              <circle cx="12" cy="12" r="4" />
            </svg>
          </span>
          Manage lists
        </button>
      </nav>

      <div class="sidebar-footer">
        <p class="metric">Benchmark</p>
        <p class="side-note">Mapped industry index</p>
      </div>
    </aside>

    <main class="content">
      <section v-if="view === 'bullish' || view === 'bearish'" class="scanner">
        <section class="hero">
          <div>
            <p class="eyebrow">{{ scannerTitle }}</p>
            <h1>Relative Strength & Volume Edge</h1>
            <p class="sub">Live snapshot of watchlisted stocks vs their industry index.</p>
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
                <option value="TRIGGER_SHORT">Trigger Short</option>
                <option value="WATCH">Watch</option>
                <option value="NEUTRAL">Neutral</option>
                <option value="EXIT/AVOID">Exit/Avoid</option>
              </select>
            </label>
            <div class="range-group compact">
              <div class="range-head">
                <p class="range-title">RRS</p>
                <div class="range-values">
                  <span>{{ formatRange(rrsMin) }}</span>
                  <span>{{ formatRange(rrsMax) }}</span>
                </div>
              </div>
              <div class="range-sliders">
                <input
                  type="range"
                  v-model.number="rrsMin"
                  :min="rangeBounds.min"
                  :max="rangeBounds.max"
                  :step="rangeBounds.step"
                />
                <input
                  type="range"
                  v-model.number="rrsMax"
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
                  <span>{{ formatRange(rrvMin) }}</span>
                  <span>{{ formatRange(rrvMax) }}</span>
                </div>
              </div>
              <div class="range-sliders">
                <input
                  type="range"
                  v-model.number="rrvMin"
                  :min="rangeBounds.min"
                  :max="rangeBounds.max"
                  :step="rangeBounds.step"
                />
                <input
                  type="range"
                  v-model.number="rrvMax"
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
                  <span>{{ formatRange(rveMin) }}</span>
                  <span>{{ formatRange(rveMax) }}</span>
                </div>
              </div>
              <div class="range-sliders">
                <input
                  type="range"
                  v-model.number="rveMin"
                  :min="rangeBounds.min"
                  :max="rangeBounds.max"
                  :step="rangeBounds.step"
                />
                <input
                  type="range"
                  v-model.number="rveMax"
                  :min="rangeBounds.min"
                  :max="rangeBounds.max"
                  :step="rangeBounds.step"
                />
              </div>
            </div>
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
            <span>Index</span>
            <span>RRS</span>
            <span>RRV</span>
            <span>RVE</span>
            <span>Signal</span>
          </div>
          <div v-for="row in filteredRows" :key="row.symbol" class="row">
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

      <section v-else-if="view === 'scores'" class="scores">
        <section class="scores-hero">
          <div>
            <p class="eyebrow">Scores</p>
          <h1>How we compute and interpret signals</h1>
          <p class="sub">
              Each symbol is evaluated against its mapped industry index using aligned candles. The three
              metrics below drive the signal rules and filters.
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
            <h3>Bearish Interpretation</h3>
            <p>Negative values represent relative weakness or contraction versus the benchmark.</p>
            <ul class="score-list">
              <li><strong>RRS &lt; 0</strong> = relative weakness.</li>
              <li><strong>RRV &lt; 0</strong> = relative volume contraction.</li>
              <li><strong>RVE &lt; 0</strong> = relative volatility contraction.</li>
            </ul>
          </article>
          <article class="score-block">
            <h3>Signals</h3>
            <ul class="score-list">
              <li><strong>TRIGGER_LONG</strong>: RRS crosses up through 0 and RRV &gt; 0 and RVE &gt; 0.</li>
              <li><strong>TRIGGER_SHORT</strong>: RRS crosses down through 0 and RRV &lt; 0 and RVE &lt; 0.</li>
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
              Each stock is compared to the industry index you assign on the Manage lists page.
          </p>
        </div>
          <div>
            <h3>Ranking</h3>
            <p>Rows are ordered by signal priority, then by larger absolute RRS and RVE.</p>
          </div>
        </section>
      </section>

      <section v-else class="manage">
        <section class="manage-hero">
          <div>
            <p class="eyebrow">Manage</p>
            <h1>Watchlists and index mapping</h1>
            <p class="sub">Add stocks and indices, then map each stock to its industry index.</p>
          </div>
        </section>

        <section class="manage-grid">
          <div class="manage-card">
            <div class="manage-head">
              <h3>Stocks to Watch</h3>
              <button class="ghost" @click="openStockForm()">Add stock</button>
            </div>
            <div class="manage-table">
              <div class="manage-row header">
                <span>Symbol</span>
                <span>Name</span>
                <span>Index</span>
                <span>Status</span>
                <span>Actions</span>
              </div>
              <div v-for="row in pagedStocks" :key="row.id" class="manage-row">
                <span>{{ row.symbol }}</span>
                <span>{{ row.name || "-" }}</span>
                <span>{{ row.industry_index_symbol || "-" }}</span>
                <span>{{ row.active ? "Active" : "Paused" }}</span>
                <span class="manage-actions">
                  <button class="ghost" @click="openStockForm(row)">Edit</button>
                  <button class="ghost danger" @click="deleteStock(row.id)">Delete</button>
                </span>
              </div>
            </div>
            <div class="pagination">
              <button class="ghost" @click="prevStockPage" :disabled="stockPage === 1">Prev</button>
              <span>Page {{ stockPage }} / {{ stockPageCount }}</span>
              <button class="ghost" @click="nextStockPage" :disabled="stockPage === stockPageCount">Next</button>
              <select v-model.number="stockPageSize">
                <option :value="8">8</option>
                <option :value="12">12</option>
                <option :value="20">20</option>
              </select>
            </div>
          </div>

          <div class="manage-card">
            <div class="manage-head">
              <h3>Indices to Watch</h3>
              <button class="ghost" @click="openIndexForm()">Add index</button>
            </div>
            <div class="manage-table">
              <div class="manage-row header">
                <span>Symbol</span>
                <span>Name</span>
                <span>Status</span>
                <span>Actions</span>
              </div>
              <div v-for="row in indices" :key="row.id" class="manage-row">
                <span>{{ row.symbol }}</span>
                <span>{{ row.name || "-" }}</span>
                <span>{{ row.active ? "Active" : "Paused" }}</span>
                <span class="manage-actions">
                  <button class="ghost" @click="openIndexForm(row)">Edit</button>
                  <button class="ghost danger" @click="deleteIndex(row.id)">Delete</button>
                </span>
              </div>
            </div>
          </div>
        </section>

        <section class="manage-form" v-if="showStockForm">
          <h3>{{ stockForm.id ? "Edit stock" : "Add stock" }}</h3>
          <div class="form-grid">
            <label>
              Symbol
              <input v-model="stockForm.symbol" placeholder="TCS" />
            </label>
            <label>
              Name
              <input v-model="stockForm.name" placeholder="Tata Consultancy Services" />
            </label>
            <label>
              Industry index
              <select v-model="stockForm.industry_index_symbol">
                <option value="">None</option>
                <option v-for="idx in indices" :key="idx.id" :value="idx.symbol">{{ idx.symbol }}</option>
              </select>
            </label>
            <label class="inline">
              <input type="checkbox" v-model="stockForm.active" />
              Active
            </label>
          </div>
          <div class="form-actions">
            <button class="primary" @click="saveStock">Save</button>
            <button class="ghost" @click="resetStockForm">Cancel</button>
          </div>
        </section>

        <section class="manage-form" v-if="showIndexForm">
          <h3>{{ indexForm.id ? "Edit index" : "Add index" }}</h3>
          <div class="form-grid">
            <label>
              Symbol
              <input v-model="indexForm.symbol" placeholder="NIFTYIT" />
            </label>
            <label>
              Name
              <input v-model="indexForm.name" placeholder="Nifty IT" />
            </label>
            <label class="inline">
              <input type="checkbox" v-model="indexForm.active" />
              Active
            </label>
          </div>
          <div class="form-actions">
            <button class="primary" @click="saveIndex">Save</button>
            <button class="ghost" @click="resetIndexForm">Cancel</button>
          </div>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const timeframes = ["5m", "15m", "1h", "1d"];
const timeframe = ref("5m");
const signalFilter = ref("ALL");
const rangeBounds = { min: -5, max: 5, step: 0.1 };
const rrsMin = ref(rangeBounds.min);
const rrsMax = ref(rangeBounds.max);
const rrvMin = ref(rangeBounds.min);
const rrvMax = ref(rangeBounds.max);
const rveMin = ref(rangeBounds.min);
const rveMax = ref(rangeBounds.max);
const view = ref("bullish");

const rows = ref([]);
const benchmarks = ref([]);
const lastUpdated = ref("-");
const stocks = ref([]);
const indices = ref([]);
const showStockForm = ref(false);
const showIndexForm = ref(false);
const stockForm = ref({
  id: null,
  symbol: "",
  name: "",
  industry_index_symbol: "",
  active: true,
});
const indexForm = ref({
  id: null,
  symbol: "",
  name: "",
  active: true,
});
const stockPage = ref(1);
const stockPageSize = ref(12);
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

const fetchStocks = async () => {
  const res = await fetch(`${apiBase}/admin/stocks`);
  if (!res.ok) return;
  stocks.value = await res.json();
};

const fetchIndices = async () => {
  const res = await fetch(`${apiBase}/admin/indices`);
  if (!res.ok) return;
  indices.value = await res.json();
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
  if (view.value !== "bullish" && view.value !== "bearish") return;
  await fetchScanner();
  await fetchBenchmarks();
  connectWS();
};

const refreshManage = async () => {
  await Promise.all([fetchStocks(), fetchIndices()]);
};

const setView = (next) => {
  view.value = next;
  if (typeof window !== "undefined") {
    window.location.hash = next;
  }
};

const syncFromHash = () => {
  if (typeof window === "undefined") return;
  const hash = window.location.hash.replace("#", "");
  if (hash === "bearish" || hash === "scores" || hash === "bullish" || hash === "manage") {
    view.value = hash;
  } else {
    view.value = "bullish";
  }
};

const viewSignalSet = computed(() => {
  if (view.value === "bullish") return new Set(["TRIGGER_LONG", "WATCH"]);
  if (view.value === "bearish") return new Set(["TRIGGER_SHORT", "EXIT/AVOID"]);
  return null;
});

const scannerTitle = computed(() => (view.value === "bearish" ? "Bearish Scanner" : "Bullish Scanner"));

const filteredRows = computed(() => {
  const filterSet = viewSignalSet.value;
  return rows.value.filter((row) => {
    if (filterSet && !filterSet.has(row.signal)) return false;
    if (!passesRange(row.rrs, rrsMin.value, rrsMax.value)) return false;
    if (!passesRange(row.rrv, rrvMin.value, rrvMax.value)) return false;
    if (!passesRange(row.rve, rveMin.value, rveMax.value)) return false;
    if (signalFilter.value === "ALL") return true;
    return row.signal === signalFilter.value;
  });
});

const pagedStocks = computed(() => {
  const start = (stockPage.value - 1) * stockPageSize.value;
  return stocks.value.slice(start, start + stockPageSize.value);
});

const stockPageCount = computed(() => {
  return Math.max(1, Math.ceil(stocks.value.length / stockPageSize.value));
});

watch(stockPageCount, (count) => {
  if (stockPage.value > count) {
    stockPage.value = count;
  }
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

const formatRange = (value) => Number(value).toFixed(2);

const signalClass = (signal) => {
  if (!signal) return "";
  return signal.toLowerCase().replace("/", "");
};

const passesRange = (value, min, max) => {
  if (value === undefined || value === null || Number.isNaN(value)) return false;
  return value >= min && value <= max;
};

const clampRange = (minRef, maxRef) => {
  watch(minRef, (val) => {
    if (val > maxRef.value) {
      maxRef.value = val;
    }
  });
  watch(maxRef, (val) => {
    if (val < minRef.value) {
      minRef.value = val;
    }
  });
};

watch(timeframe, async () => {
  await refreshScanner();
});

watch(view, async (next) => {
  if (next === "scores") {
    stopWS();
    return;
  }
  if (next === "manage") {
    stopWS();
    await refreshManage();
    return;
  }
  signalFilter.value = "ALL";
  await refreshScanner();
});

watch(stockPageSize, () => {
  stockPage.value = 1;
});

clampRange(rrsMin, rrsMax);
clampRange(rrvMin, rrvMax);
clampRange(rveMin, rveMax);

onMounted(async () => {
  syncFromHash();
  hashListener = () => syncFromHash();
  window.addEventListener("hashchange", hashListener);
  if (view.value === "manage") {
    await refreshManage();
  } else if (view.value !== "scores") {
    await refreshScanner();
  }
});

onBeforeUnmount(() => {
  stopWS();
  if (hashListener) {
    window.removeEventListener("hashchange", hashListener);
  }
});

const openStockForm = (row = null) => {
  if (row) {
    stockForm.value = {
      id: row.id,
      symbol: row.symbol,
      name: row.name || "",
      industry_index_symbol: row.industry_index_symbol || "",
      active: row.active,
    };
  } else {
    stockForm.value = { id: null, symbol: "", name: "", industry_index_symbol: "", active: true };
  }
  showStockForm.value = true;
  showIndexForm.value = false;
};

const resetStockForm = () => {
  showStockForm.value = false;
  stockForm.value = { id: null, symbol: "", name: "", industry_index_symbol: "", active: true };
};

const saveStock = async () => {
  if (!stockForm.value.symbol) return;
  const payload = {
    symbol: stockForm.value.symbol.trim().toUpperCase(),
    name: stockForm.value.name || null,
    active: stockForm.value.active,
    industry_index_symbol: stockForm.value.industry_index_symbol || null,
  };
  if (stockForm.value.id) {
    await fetch(`${apiBase}/admin/stocks/${stockForm.value.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    await fetch(`${apiBase}/admin/stocks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  await refreshManage();
  resetStockForm();
};

const deleteStock = async (id) => {
  await fetch(`${apiBase}/admin/stocks/${id}`, { method: "DELETE" });
  await refreshManage();
};

const nextStockPage = () => {
  if (stockPage.value < stockPageCount.value) {
    stockPage.value += 1;
  }
};

const prevStockPage = () => {
  if (stockPage.value > 1) {
    stockPage.value -= 1;
  }
};

const openIndexForm = (row = null) => {
  if (row) {
    indexForm.value = { id: row.id, symbol: row.symbol, name: row.name || "", active: row.active };
  } else {
    indexForm.value = { id: null, symbol: "", name: "", active: true };
  }
  showIndexForm.value = true;
  showStockForm.value = false;
};

const resetIndexForm = () => {
  showIndexForm.value = false;
  indexForm.value = { id: null, symbol: "", name: "", active: true };
};

const saveIndex = async () => {
  if (!indexForm.value.symbol) return;
  const payload = {
    symbol: indexForm.value.symbol.trim().toUpperCase(),
    name: indexForm.value.name || null,
    active: indexForm.value.active,
  };
  if (indexForm.value.id) {
    await fetch(`${apiBase}/admin/indices/${indexForm.value.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    await fetch(`${apiBase}/admin/indices`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  await refreshManage();
  resetIndexForm();
};

const deleteIndex = async (id) => {
  await fetch(`${apiBase}/admin/indices/${id}`, { method: "DELETE" });
  await refreshManage();
};
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  padding: 24px 20px;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(10, 14, 18, 0.9);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(43, 213, 118, 0.6), rgba(240, 180, 41, 0.4));
  box-shadow: 0 12px 30px rgba(43, 213, 118, 0.2);
}

.brand-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.brand-sub {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.side-nav {
  display: grid;
  gap: 10px;
}

.side-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.side-link:hover {
  border-color: rgba(255, 255, 255, 0.3);
}

.side-link.active {
  background: rgba(43, 213, 118, 0.18);
  border-color: rgba(43, 213, 118, 0.4);
  color: var(--accent);
}

.icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.icon-wrap svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
  stroke-width: 1.6;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-wrap.bull {
  color: var(--accent);
  background: rgba(43, 213, 118, 0.15);
}

.icon-wrap.bear {
  color: var(--danger);
  background: rgba(243, 111, 111, 0.15);
}

.icon-wrap.info {
  color: var(--accent-2);
  background: rgba(240, 180, 41, 0.15);
}

.icon-wrap.manage {
  color: var(--muted);
  background: rgba(141, 162, 181, 0.15);
}

.sidebar-footer {
  margin-top: auto;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(20, 28, 34, 0.6);
}

.side-note {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.content {
  padding: 32px;
  max-width: 1400px;
  width: 100%;
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
  grid-template-columns: 140px 160px repeat(3, minmax(180px, 1fr));
  gap: 12px;
  align-content: start;
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

.range-group {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 10px;
  background: rgba(15, 20, 26, 0.6);
  display: grid;
  gap: 10px;
}

.range-group.compact {
  padding: 8px 10px;
  gap: 6px;
}

.range-group.compact .range-values {
  font-size: 11px;
}

.range-title {
  margin: 0;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
}

.range-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.range-values {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}

.range-sliders {
  display: grid;
  gap: 6px;
}

.range-sliders input[type="range"] {
  accent-color: var(--accent);
}

.range-group.compact .range-sliders input[type="range"] {
  height: 4px;
}

@media (max-width: 1200px) {
  .controls {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }
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

.badge.no_data {
  background: rgba(141, 162, 181, 0.2);
  color: var(--muted);
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
  grid-template-columns: 1.3fr 1fr repeat(3, 1fr) 1.2fr;
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

.trigger_short {
  color: var(--danger);
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

.manage {
  display: grid;
  gap: 24px;
}

.manage-hero {
  padding: 18px 22px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(20, 28, 34, 0.7);
}

.manage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.manage-card {
  background: var(--panel);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px;
  display: grid;
  gap: 12px;
  align-content: start;
}

.manage-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.manage-table {
  display: grid;
  gap: 8px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  color: var(--muted);
  font-size: 12px;
}

.manage-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr 1.2fr 0.8fr 1fr;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
  align-items: center;
  font-size: 12px;
}

.manage-row.header {
  background: transparent;
  border: none;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 11px;
}

.manage-actions {
  display: flex;
  gap: 8px;
}

.manage-form {
  background: var(--panel);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 18px;
  display: grid;
  gap: 12px;
}

.form-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.form-grid label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

.form-grid label.inline {
  grid-template-columns: 18px 1fr;
  align-items: center;
  gap: 8px;
}

.form-actions {
  display: flex;
  gap: 10px;
}

.ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--text);
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 12px;
  cursor: pointer;
}

.ghost.danger {
  border-color: rgba(243, 111, 111, 0.4);
  color: var(--danger);
}

.primary {
  background: rgba(43, 213, 118, 0.2);
  border: 1px solid rgba(43, 213, 118, 0.4);
  color: var(--accent);
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 12px;
  cursor: pointer;
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

.score-footnote {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  background: rgba(20, 28, 34, 0.75);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 18px;
}

@media (max-width: 1200px) {
  .shell {
    grid-template-columns: 200px minmax(0, 1fr);
  }
}

@media (max-width: 1100px) {
  .row {
    grid-template-columns: 1.4fr repeat(2, 1fr);
    grid-auto-rows: auto;
  }
  .row span:nth-child(n + 4) {
    display: none;
  }
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: sticky;
    top: 0;
    z-index: 2;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }
  .side-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .side-link {
    flex-direction: column;
    gap: 6px;
    text-align: center;
  }
  .content {
    padding: 24px;
  }
}
</style>
