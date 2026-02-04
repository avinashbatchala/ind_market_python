<template>
  <section class="manage">
    <section class="manage-hero">
      <div>
        <p class="eyebrow">Manage</p>
        <h1>Watchlists and index mapping</h1>
        <p class="sub">Add stocks and indices, then map each stock to one or more industry indices.</p>
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
            <span>Indices</span>
            <span>Status</span>
            <span class="align-right">Actions</span>
          </div>
          <div v-for="row in pagedStocks" :key="row.id" class="manage-row">
            <span>{{ row.symbol }}</span>
            <span>{{ row.name || "-" }}</span>
            <span>{{ formatIndexList(row.industry_index_symbols) }}</span>
            <span>{{ row.active ? "Active" : "Paused" }}</span>
            <span class="manage-actions">
              <button
                type="button"
                class="icon-btn edit"
                @click="openStockForm(row)"
                aria-label="Edit stock"
                title="Edit stock"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
                </svg>
              </button>
              <button
                type="button"
                class="icon-btn delete"
                @click="openDeleteConfirm(row, 'stock')"
                aria-label="Delete stock"
                title="Delete stock"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="M6 6l1 14h10l1-14" />
                  <path d="M10 11v6" />
                  <path d="M14 11v6" />
                </svg>
              </button>
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
            <span>Data Symbol</span>
            <span>Name</span>
            <span>Status</span>
            <span class="align-right">Actions</span>
          </div>
          <div v-for="row in indices" :key="row.id" class="manage-row">
            <span>{{ row.symbol }}</span>
            <span>{{ row.data_symbol || row.symbol }}</span>
            <span>{{ row.name || "-" }}</span>
            <span>{{ row.active ? "Active" : "Paused" }}</span>
            <span class="manage-actions">
              <button
                type="button"
                class="icon-btn edit"
                @click="openIndexForm(row)"
                aria-label="Edit index"
                title="Edit index"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
                </svg>
              </button>
              <button
                type="button"
                class="icon-btn delete"
                @click="openDeleteConfirm(row, 'index')"
                aria-label="Delete index"
                title="Delete index"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="M6 6l1 14h10l1-14" />
                  <path d="M10 11v6" />
                  <path d="M14 11v6" />
                </svg>
              </button>
            </span>
          </div>
        </div>
      </div>
    </section>

    <section v-if="showStockForm" class="modal-backdrop" @click.self="resetStockForm">
      <div class="modal-card">
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
          <label class="full-row">
            Industry indices
            <div class="checkbox-list">
              <label v-for="idx in indices" :key="idx.id" class="checkbox-row">
                <input
                  type="checkbox"
                  v-model="stockForm.industry_index_symbols"
                  :value="idx.symbol"
                />
                <span>{{ idx.symbol }}</span>
              </label>
            </div>
            <span class="hint">NIFTY is always included by default.</span>
          </label>
          <label class="inline full-row active-toggle">
            <input type="checkbox" v-model="stockForm.active" />
            Active
          </label>
        </div>
        <div class="form-actions">
          <button class="primary" @click="saveStock">Save</button>
          <button class="ghost" @click="resetStockForm">Cancel</button>
        </div>
      </div>
    </section>

    <section v-if="showIndexForm" class="modal-backdrop" @click.self="resetIndexForm">
      <div class="modal-card">
        <h3>{{ indexForm.id ? "Edit index" : "Add index" }}</h3>
        <div class="form-grid">
          <label>
            Symbol
            <input v-model="indexForm.symbol" placeholder="NIFTYIT" />
          </label>
          <label>
            Data symbol
            <input v-model="indexForm.data_symbol" placeholder="NIFTYIT" />
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
      </div>
    </section>

    <section v-if="confirmDialog.show" class="modal-backdrop" @click.self="closeDeleteConfirm">
      <div class="modal-card confirm-card" role="dialog" aria-modal="true">
        <h3>
          Delete {{ confirmDialog.type === "stock" ? "stock" : "index" }}?
        </h3>
        <p class="confirm-sub">
          This removes {{ confirmDialog.label || "this item" }} from your lists. This action cannot be undone.
        </p>
        <div class="form-actions">
          <button class="ghost" @click="closeDeleteConfirm">Cancel</button>
          <button class="danger solid" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

const props = defineProps({
  apiBase: {
    type: String,
    required: true,
  },
});

const stocks = ref([]);
const indices = ref([]);
const showStockForm = ref(false);
const showIndexForm = ref(false);
const stockForm = ref({
  id: null,
  symbol: "",
  name: "",
  industry_index_symbols: [],
  active: true,
});
const indexForm = ref({
  id: null,
  symbol: "",
  data_symbol: "",
  name: "",
  active: true,
});
const stockPage = ref(1);
const stockPageSize = ref(12);
const confirmDialog = ref({
  show: false,
  type: null,
  id: null,
  label: "",
});

const fetchStocks = async () => {
  const res = await fetch(`${props.apiBase}/admin/stocks`);
  if (!res.ok) return;
  stocks.value = await res.json();
};

const fetchIndices = async () => {
  const res = await fetch(`${props.apiBase}/admin/indices`);
  if (!res.ok) return;
  indices.value = await res.json();
};

const refreshManage = async () => {
  await Promise.all([fetchStocks(), fetchIndices()]);
};

const formatIndexList = (values) => {
  if (!Array.isArray(values) || values.length === 0) return "-";
  return values.join(", ");
};

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

watch(stockPageSize, () => {
  stockPage.value = 1;
});

const openStockForm = (row = null) => {
  if (row) {
    stockForm.value = {
      id: row.id,
      symbol: row.symbol,
      name: row.name || "",
      industry_index_symbols: Array.isArray(row.industry_index_symbols)
        ? [...row.industry_index_symbols]
        : [],
      active: row.active,
    };
  } else {
    stockForm.value = { id: null, symbol: "", name: "", industry_index_symbols: [], active: true };
  }
  showStockForm.value = true;
  showIndexForm.value = false;
};

const resetStockForm = () => {
  showStockForm.value = false;
  stockForm.value = { id: null, symbol: "", name: "", industry_index_symbols: [], active: true };
};

const saveStock = async () => {
  if (!stockForm.value.symbol) return;
  const payload = {
    symbol: stockForm.value.symbol.trim().toUpperCase(),
    name: stockForm.value.name || null,
    active: stockForm.value.active,
    industry_index_symbols: Array.isArray(stockForm.value.industry_index_symbols)
      ? stockForm.value.industry_index_symbols
      : [],
  };
  if (stockForm.value.id) {
    await fetch(`${props.apiBase}/admin/stocks/${stockForm.value.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    await fetch(`${props.apiBase}/admin/stocks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  await refreshManage();
  resetStockForm();
};

const deleteStock = async (id) => {
  await fetch(`${props.apiBase}/admin/stocks/${id}`, { method: "DELETE" });
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
    indexForm.value = {
      id: row.id,
      symbol: row.symbol,
      data_symbol: row.data_symbol || row.symbol,
      name: row.name || "",
      active: row.active,
    };
  } else {
    indexForm.value = { id: null, symbol: "", data_symbol: "", name: "", active: true };
  }
  showIndexForm.value = true;
  showStockForm.value = false;
};

const resetIndexForm = () => {
  showIndexForm.value = false;
  indexForm.value = { id: null, symbol: "", data_symbol: "", name: "", active: true };
};

const saveIndex = async () => {
  if (!indexForm.value.symbol) return;
  const payload = {
    symbol: indexForm.value.symbol.trim().toUpperCase(),
    data_symbol: indexForm.value.data_symbol
      ? indexForm.value.data_symbol.trim().toUpperCase()
      : null,
    name: indexForm.value.name || null,
    active: indexForm.value.active,
  };
  if (indexForm.value.id) {
    await fetch(`${props.apiBase}/admin/indices/${indexForm.value.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } else {
    await fetch(`${props.apiBase}/admin/indices`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  await refreshManage();
  resetIndexForm();
};

const deleteIndex = async (id) => {
  await fetch(`${props.apiBase}/admin/indices/${id}`, { method: "DELETE" });
  await refreshManage();
};

const openDeleteConfirm = (row, type) => {
  confirmDialog.value = {
    show: true,
    type,
    id: row.id,
    label: row.symbol || row.name || "",
  };
};

const closeDeleteConfirm = () => {
  confirmDialog.value = { show: false, type: null, id: null, label: "" };
};

const confirmDelete = async () => {
  if (!confirmDialog.value.id) return;
  if (confirmDialog.value.type === "stock") {
    await deleteStock(confirmDialog.value.id);
  } else if (confirmDialog.value.type === "index") {
    await deleteIndex(confirmDialog.value.id);
  }
  closeDeleteConfirm();
};

onMounted(async () => {
  await refreshManage();
});
</script>
