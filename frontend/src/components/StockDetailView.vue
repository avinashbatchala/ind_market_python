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
          <input v-if="expiriesError" v-model="expiry" placeholder="YYYY-MM-DD" />
        </div>
        <div class="filter-card compact">
          <span class="filter-title">Trading Symbol</span>
          <input v-model="tradingSymbol" placeholder="NIFTY25O1425100CE" />
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
const tradingSymbol = ref("");
const expiriesLoading = ref(false);
const expiriesError = ref("");

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
    if (tradingSymbol.value) params.set("trading_symbol", tradingSymbol.value);
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
    const list = data.expiries || [];
    if (Array.isArray(list) && list.length) {
      expiry.value = list[0];
      optionsChain.value = optionsChain.value; // no-op to keep reactivity
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
  return Object.entries(quote)
    .slice(0, 12)
    .map(([key, value]) => ({ key, value: formatValue(value) }));
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
  const chainExpiries = expiries.value;
  if (chainExpiries.length) return chainExpiries;
  return [];
});

const expirySelectDisabled = computed(() => expiriesLoading.value);

const expiryLabel = computed(() => {
  if (expiriesLoading.value) return "Loading...";
  if (expiriesError.value) return "Expiry (manual)";
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

const formatValue = (value) => {
  if (value === null || value === undefined) return "-";
  if (typeof value === "object") return JSON.stringify(value);
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
  await fetchExpiries();
  await fetchLive();
  await fetchMetrics();
  poller = setInterval(fetchLive, 15000);
});

onBeforeUnmount(() => {
  if (poller) clearInterval(poller);
});
</script>
