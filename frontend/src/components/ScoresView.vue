<template>
  <section class="scores">
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
</template>
