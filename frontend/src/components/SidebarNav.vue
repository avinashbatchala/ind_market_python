<template>
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
      <button class="side-link" :class="{ active: view === 'indices' }" @click="setView('indices')">
        <span class="icon-wrap info">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 18h16M6 16V8M12 16V5M18 16v-7" />
          </svg>
        </span>
        Indices
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
</template>

<script setup>
const props = defineProps({
  view: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["change"]);

const setView = (next) => {
  emit("change", next);
};
</script>
