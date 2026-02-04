<template>
  <div class="shell">
    <SidebarNav :view="view" @change="setView" />

    <main class="content">
      <StockDetailView
        v-if="isStockRoute"
        :symbol="stockSymbol"
        :api-base="apiBase"
        :timeframes="timeframes"
        :default-timeframe="timeframe"
        @back="navigateHome"
      />

      <ScannerView
        v-else-if="view === 'bullish' || view === 'bearish'"
        :scanner-title="scannerTitle"
        :timeframes="timeframes"
        :range-bounds="rangeBounds"
        :filtered-rows="filteredRows"
        :last-updated="lastUpdated"
        v-model:timeframe="timeframe"
        v-model:signalFilter="signalFilter"
        v-model:rrsMin="rrsMin"
        v-model:rrsMax="rrsMax"
        v-model:rrvMin="rrvMin"
        v-model:rrvMax="rrvMax"
        v-model:rveMin="rveMin"
        v-model:rveMax="rveMax"
        @open-stock="navigateToStock"
      />

      <IndicesView
        v-else-if="view === 'indices'"
        :timeframes="timeframes"
        :benchmark-cards="benchmarkCards"
        :last-updated="benchUpdated"
        v-model:timeframe="timeframe"
      />

      <ScoresView v-else-if="view === 'scores'" />

      <ManageView v-else :api-base="apiBase" />
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import SidebarNav from "./components/SidebarNav.vue";
import ScannerView from "./components/ScannerView.vue";
import IndicesView from "./components/IndicesView.vue";
import ScoresView from "./components/ScoresView.vue";
import ManageView from "./components/ManageView.vue";
import StockDetailView from "./components/StockDetailView.vue";

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
const benchUpdated = ref("-");
let socket = null;
let hashListener = null;
let popListener = null;

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const routePath = ref(typeof window !== "undefined" ? window.location.pathname : "/");

const isStockRoute = computed(() => routePath.value.startsWith("/stocks/"));
const stockSymbol = computed(() => {
  if (!isStockRoute.value) return "";
  const parts = routePath.value.split("/");
  return decodeURIComponent(parts[2] || "").toUpperCase();
});

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
  benchUpdated.value = data.ts || "-";
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

const setView = (next) => {
  if (isStockRoute.value) {
    navigateHome();
  }
  view.value = next;
  if (typeof window !== "undefined") {
    window.location.hash = next;
  }
};

const navigateToStock = (symbol) => {
  if (typeof window === "undefined") return;
  stopWS();
  const path = `/stocks/${encodeURIComponent(symbol)}`;
  window.history.pushState({}, "", path);
  routePath.value = path;
};

const navigateHome = () => {
  if (typeof window === "undefined") return;
  window.history.pushState({}, "", "/");
  routePath.value = "/";
  if (view.value === "bullish" || view.value === "bearish") {
    refreshScanner();
  }
};

const syncFromHash = () => {
  if (typeof window === "undefined") return;
  const hash = window.location.hash.replace("#", "");
  if (hash === "bearish" || hash === "scores" || hash === "bullish" || hash === "manage" || hash === "indices") {
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

const passesRange = (value, min, max) => {
  if (value === undefined || value === null || Number.isNaN(value)) return false;
  return value >= min && value <= max;
};

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

const benchmarkCards = computed(() => {
  return benchmarks.value.map((b) => ({
    benchmark: b.benchmark,
    regime: b.regime,
    trend: b.trend,
    vol_expansion: b.vol_expansion,
    participation: b.participation,
  }));
});

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
  if (view.value === "bullish" || view.value === "bearish") {
    await refreshScanner();
    return;
  }
  if (view.value === "indices") {
    await fetchBenchmarks();
  }
});

watch(view, async (next) => {
  if (next === "scores" || next === "manage") {
    stopWS();
    return;
  }
  if (next === "indices") {
    stopWS();
    await fetchBenchmarks();
    return;
  }
  signalFilter.value = "ALL";
  await refreshScanner();
});

clampRange(rrsMin, rrsMax);
clampRange(rrvMin, rrvMax);
clampRange(rveMin, rveMax);

onMounted(async () => {
  syncFromHash();
  hashListener = () => syncFromHash();
  window.addEventListener("hashchange", hashListener);
  popListener = () => {
    routePath.value = window.location.pathname || "/";
  };
  window.addEventListener("popstate", popListener);
  if (view.value === "indices") {
    await fetchBenchmarks();
  } else if (view.value !== "scores" && view.value !== "manage" && !isStockRoute.value) {
    await refreshScanner();
  }
});

onBeforeUnmount(() => {
  stopWS();
  if (hashListener) {
    window.removeEventListener("hashchange", hashListener);
  }
  if (popListener) {
    window.removeEventListener("popstate", popListener);
  }
});
</script>
