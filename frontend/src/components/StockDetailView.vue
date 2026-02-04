<template>
  <section class="stock-detail">
    <div class="detail-head">
      <button class="ghost" @click="emit('back')">Back</button>
      <div class="detail-title">
        <p class="eyebrow">Stock Detail</p>
        <h1>{{ symbol }}</h1>
        <p class="sub">Live + relative metrics (default NIFTY)</p>
      </div>
      <div class="filter-card compact">
        <span class="filter-title">Timeframe</span>
        <select v-model="timeframe">
          <option v-for="tf in timeframes" :key="tf" :value="tf">{{ tf }}</option>
        </select>
      </div>
    </div>

    <section class="card">
      <div class="card-head">
        <h3>Intraday Plan</h3>
        <span class="badge" :class="planStatusClass">{{ planStatus }}</span>
      </div>
      <div v-if="plan && plan.strategy" class="plan-grid">
        <div>
          <p class="metric">Direction</p>
          <h3>{{ plan.direction }}</h3>
        </div>
        <div>
          <p class="metric">Regime</p>
          <h3>{{ plan.regime }}</h3>
        </div>
        <div>
          <p class="metric">Strategy</p>
          <h3>{{ plan.strategy }}</h3>
        </div>
        <div>
          <p class="metric">DTE</p>
          <h3>{{ plan.dte }}</h3>
        </div>
        <div>
          <p class="metric">Entry</p>
          <h3>{{ plan.entry_type }}</h3>
        </div>
        <div>
          <p class="metric">Max Risk</p>
          <h3>{{ formatPct(plan.max_risk_pct) }}</h3>
        </div>
      </div>
      <div v-if="plan && plan.legs && plan.legs.length" class="options-table">
        <div class="row header">
          <span>Leg</span>
          <span>Symbol</span>
          <span>Type</span>
          <span>Strike</span>
          <span>Expiry</span>
          <span>LTP</span>
        </div>
        <div v-for="(leg, idx) in plan.legs" :key="idx" class="row">
          <span>{{ leg.side }}</span>
          <span>{{ leg.symbol }}</span>
          <span>{{ leg.option_type }}</span>
          <span>{{ leg.strike }}</span>
          <span>{{ leg.expiry }}</span>
          <span>{{ formatNum(leg.ltp) }}</span>
        </div>
      </div>
      <div v-else-if="planStatus === 'NO_TRADE'" class="json-block">
        <pre>No trade plan available.</pre>
      </div>
      <p v-if="planError" class="inline-error">{{ planError }}</p>
    </section>

    <section class="card">
      <div class="card-head">
        <h3>Live Data</h3>
        <span class="badge" :class="liveStatusClass">{{ liveStatus }}</span>
      </div>
      <div class="live-summary">
        <div>
          <p class="metric">LTP</p>
          <h3>{{ formatNum(live.ltp) }}</h3>
        </div>
        <div>
          <p class="metric">Change</p>
          <h3>{{ formatNum(live.change) }}</h3>
        </div>
        <div>
          <p class="metric">Timestamp</p>
          <h3>{{ live.timestamp || "-" }}</h3>
        </div>
      </div>
      <div class="kv-grid">
        <div v-for="row in liveFields" :key="row.key" class="kv-row">
          <span>{{ row.key }}</span>
          <span>{{ row.value }}</span>
        </div>
      </div>
      <p v-if="liveError" class="inline-error">{{ liveError }}</p>
    </section>

    <section class="card">
      <div class="card-head">
        <h3>Options & Greeks</h3>
        <span class="badge" :class="optionsStatusClass">{{ optionsStatus }}</span>
      </div>
      <div class="options-controls">
        <div class="filter-card compact">
          <span class="filter-title">{{ expiryLabel }}</span>
          <select v-model="expiry" :disabled="expirySelectDisabled">
            <option value="">Latest</option>
            <option v-for="exp in expiryOptions" :key="exp" :value="exp">{{ exp }}</option>
          </select>
        </div>
        <div class="filter-card compact">
          <span class="filter-title">Type</span>
          <select v-model="optionType">
            <option value="">All</option>
            <option value="CALL">Call</option>
            <option value="PUT">Put</option>
          </select>
        </div>
        <button class="ghost" @click="fetchLive">Refresh</button>
      </div>
      <p v-if="expiriesError" class="inline-error">{{ expiriesError }}</p>

      <div v-if="optionsList.length" class="options-table">
        <div class="row header">
          <span>Type</span>
          <span>Strike</span>
          <span>LTP</span>
          <span>IV</span>
          <span>Delta</span>
          <span>Gamma</span>
        </div>
        <div v-for="(opt, idx) in optionsList" :key="idx" class="row">
          <span>{{ opt.type || opt.optionType || '-' }}</span>
          <span>{{ opt.strike || opt.strikePrice || '-' }}</span>
          <span>{{ opt.ltp || opt.lastTradedPrice || '-' }}</span>
          <span>{{ opt.iv || opt.impliedVolatility || '-' }}</span>
          <span>{{ opt.delta ?? '-' }}</span>
          <span>{{ opt.gamma ?? '-' }}</span>
        </div>
      </div>

      <div v-else class="json-block">
        <pre>{{ pretty(optionsChain) }}</pre>
      </div>

      <div v-if="greeksFields.length" class="greeks-grid">
        <div v-for="item in greeksFields" :key="item.key" class="kv-row">
          <span>{{ item.key }}</span>
          <span>{{ item.value }}</span>
        </div>
      </div>
      <div v-else class="json-block">
        <pre>{{ pretty(greeks) }}</pre>
      </div>
      <p v-if="optionsError" class="inline-error">{{ optionsError }}</p>
    </section>

    <section class="card">
      <div class="card-head">
        <h3>Relative Strength vs Indices</h3>
        <span class="badge" :class="metricsStatusClass">{{ metricsStatus }}</span>
      </div>
      <div class="table">
        <div class="row header">
          <span>Index</span>
          <span>RRS</span>
          <span>RRV</span>
          <span>RVE</span>
          <span>Signal</span>
          <span>Updated</span>
        </div>
        <div v-for="row in metricsRows" :key="row.index" class="row">
          <span>{{ row.index }}</span>
          <span>{{ formatNum(row.rrs) }}</span>
          <span>{{ formatNum(row.rrv) }}</span>
          <span>{{ formatNum(row.rve) }}</span>
          <span :class="signalClass(row.signal)">{{ row.signal }}</span>
          <span>
            <template v-if="row.error">
              <span class="inline-error">{{ row.error }}</span>
            </template>
            <template v-else>{{ row.updated_at || '-' }}</template>
          </span>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  symbol: { type: String, required: true },
  apiBase: { type: String, required: true },
  timeframes: { type: Array, required: true },
  defaultTimeframe: { type: String, required: true },
});

const emit = defineEmits(["back"]);

const timeframe = ref(props.defaultTimeframe);
const expiry = ref("");
const optionType = ref("");
const expiriesLoading = ref(false);
const expiriesError = ref("");
const expiryList = ref([]);
const plan = ref(null);
const planError = ref("");
const planLoading = ref(false);

const live = ref({});
const liveError = ref("");
const liveLoading = ref(false);

const optionsChain = ref(null);
const greeks = ref(null);
const optionsError = ref("");

const metricsRows = ref([]);
const metricsLoading = ref(false);
const metricsError = ref("");

let poller = null;

const fetchLive = async () => {
  liveLoading.value = true;
  liveError.value = "";
  optionsError.value = "";
  try {
    const params = new URLSearchParams();
    if (expiry.value) params.set("expiry", expiry.value);
    if (expiry.value) params.set("expiry_date", expiry.value);
    if (optionType.value) params.set("option_type", optionType.value);
    const res = await fetch(`${props.apiBase}/stocks/${props.symbol}/live?${params.toString()}`);
    if (!res.ok) {
      liveError.value = `Failed to load live data (${res.status})`;
      return;
    }
    const data = await res.json();
    live.value = data;
    optionsChain.value = data.options_chain || null;
    greeks.value = data.greeks || null;
    if (data.errors) {
      optionsError.value = Object.values(data.errors).join(" | ");
    }
  } catch (err) {
    liveError.value = String(err);
  } finally {
    liveLoading.value = false;
  }
};

const fetchPlan = async () => {
  planLoading.value = true;
  planError.value = "";
  try {
    const res = await fetch(`${props.apiBase}/stocks/${props.symbol}/intraday-plan`);
    if (!res.ok) {
      planError.value = `Failed to load plan (${res.status})`;
      return;
    }
    const data = await res.json();
    plan.value = data.plan;
  } catch (err) {
    planError.value = String(err);
  } finally {
    planLoading.value = false;
  }
};
const fetchExpiries = async () => {
  expiriesLoading.value = true;
  expiriesError.value = "";
  try {
    const res = await fetch(`${props.apiBase}/stocks/${props.symbol}/expiries`);
    if (!res.ok) {
      expiriesError.value = `Failed to load expiries (${res.status})`;
      return;
    }
    const data = await res.json();
    const list = Array.isArray(data.expiries) ? data.expiries : [];
    expiryList.value = list;
    if (list.length) {
      expiry.value = list[0];
    }
  } catch (err) {
    expiriesError.value = String(err);
  } finally {
    expiriesLoading.value = false;
  }
};

const fetchMetrics = async () => {
  metricsLoading.value = true;
  metricsError.value = "";
  try {
    const res = await fetch(
      `${props.apiBase}/stocks/${props.symbol}/relative-metrics?interval=${timeframe.value}`
    );
    if (!res.ok) {
      metricsError.value = `Failed to load metrics (${res.status})`;
      return;
    }
    const data = await res.json();
    metricsRows.value = data.rows || [];
  } catch (err) {
    metricsError.value = String(err);
  } finally {
    metricsLoading.value = false;
  }
};

const liveFields = computed(() => {
  const quote = live.value?.quote;
  if (!quote || typeof quote !== "object") return [];
  const rows = [];
  if (quote.ohlc && typeof quote.ohlc === "object") {
    rows.push({ key: "ohlc_open", value: formatValue(quote.ohlc.open) });
    rows.push({ key: "ohlc_high", value: formatValue(quote.ohlc.high) });
    rows.push({ key: "ohlc_low", value: formatValue(quote.ohlc.low) });
    rows.push({ key: "ohlc_close", value: formatValue(quote.ohlc.close) });
  }
  if (quote.depth && typeof quote.depth === "object") {
    const bestBuy = Array.isArray(quote.depth.buy) ? quote.depth.buy[0] : null;
    const bestSell = Array.isArray(quote.depth.sell) ? quote.depth.sell[0] : null;
    if (bestBuy) {
      rows.push({ key: "best_bid_price", value: formatValue(bestBuy.price) });
      rows.push({ key: "best_bid_qty", value: formatValue(bestBuy.quantity) });
    }
    if (bestSell) {
      rows.push({ key: "best_ask_price", value: formatValue(bestSell.price) });
      rows.push({ key: "best_ask_qty", value: formatValue(bestSell.quantity) });
    }
  }
  const skipKeys = new Set(["ohlc", "depth"]);
  for (const [key, value] of Object.entries(quote)) {
    if (skipKeys.has(key)) continue;
    if (value === null || value === undefined) {
      rows.push({ key, value: "-" });
      continue;
    }
    if (typeof value === "object") continue;
    rows.push({ key, value: formatValue(value) });
  }
  return rows;
});

const expiries = computed(() => {
  const data = optionsChain.value;
  if (!data || typeof data !== "object") return [];
  const candidates = [
    data.expiries,
    data.expiryDates,
    data.expiry_dates,
    data.data?.expiries,
    data.data?.expiryDates,
  ];
  for (const entry of candidates) {
    if (Array.isArray(entry)) return entry;
  }
  return [];
});

const expiryOptions = computed(() => {
  if (expiryList.value.length) return expiryList.value;
  const chainExpiries = expiries.value;
  if (chainExpiries.length) return chainExpiries;
  return [];
});

const expirySelectDisabled = computed(() => expiriesLoading.value);

const expiryLabel = computed(() => {
  if (expiriesLoading.value) return "Loading...";
  return "Expiry";
});

const optionsList = computed(() => {
  const data = optionsChain.value;
  if (!data) return [];
  if (Array.isArray(data)) return data;
  const nested = data.options || data.data?.options || data.data?.optionChain;
  if (Array.isArray(nested)) return nested;
  return [];
});

const greeksFields = computed(() => {
  const data = greeks.value;
  if (!data || typeof data !== "object") return [];
  const payload = data.greeks || data.data?.greeks || data;
  if (!payload || typeof payload !== "object") return [];
  return Object.entries(payload).map(([key, value]) => ({
    key,
    value: formatValue(value),
  }));
});

const liveStatus = computed(() => {
  if (liveLoading.value) return "LOADING";
  if (liveError.value) return "ERROR";
  return "READY";
});

const planStatus = computed(() => {
  if (planLoading.value) return "LOADING";
  if (planError.value) return "ERROR";
  if (!plan.value) return "NO_TRADE";
  return "READY";
});

const planStatusClass = computed(() => {
  if (planLoading.value) return "neutral";
  if (planError.value) return "bearish";
  if (!plan.value) return "no_data";
  return "bullish";
});
const liveStatusClass = computed(() => {
  if (liveLoading.value) return "neutral";
  if (liveError.value) return "bearish";
  return "bullish";
});

const optionsStatus = computed(() => {
  if (liveLoading.value) return "LOADING";
  if (optionsError.value) return "ERROR";
  return "READY";
});

const optionsStatusClass = computed(() => {
  if (liveLoading.value) return "neutral";
  if (optionsError.value) return "bearish";
  return "bullish";
});

const metricsStatus = computed(() => {
  if (metricsLoading.value) return "LOADING";
  if (metricsError.value) return "ERROR";
  return "READY";
});

const metricsStatusClass = computed(() => {
  if (metricsLoading.value) return "neutral";
  if (metricsError.value) return "bearish";
  return "bullish";
});

const formatNum = (value) => {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return Number(value).toFixed(2);
};

const formatPct = (value) => {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return `${(Number(value) * 100).toFixed(2)}%`;
};

const formatValue = (value) => {
  if (value === null || value === undefined) return "-";
  if (typeof value === "object") return "-";
  return String(value);
};

const pretty = (value) => {
  if (!value) return "-";
  try {
    return JSON.stringify(value, null, 2);
  } catch (e) {
    return String(value);
  }
};

const signalClass = (signal) => {
  if (!signal) return "";
  return signal.toLowerCase().replace("/", "");
};

watch(timeframe, async () => {
  await fetchMetrics();
});

onMounted(async () => {
  await fetchPlan();
  await fetchExpiries();
  await fetchLive();
  await fetchMetrics();
  poller = setInterval(fetchLive, 15000);
});

onBeforeUnmount(() => {
  if (poller) clearInterval(poller);
});
</script>
