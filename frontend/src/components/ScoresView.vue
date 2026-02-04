<template>
  <section class="scores">
    <section class="scores-hero">
      <div>
        <p class="eyebrow">Scores</p>
        <h1>How we compute and interpret signals (geek mode)</h1>
        <p class="sub">
          Each symbol is evaluated against its mapped industry index using aligned candles. The three
          metrics below drive the signal rules and filters, and the intraday options decision tree
          builds on those same signals.
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
        <h3>Core notation + alignment</h3>
        <p>
          We align symbol and benchmark candles by timestamp intersection. No forward fill. Warmup
          periods emit NaN until enough bars exist.
        </p>
        <pre class="score-code"><code>ΔS_t = close_S[t] - close_S[t-L]
ΔB_t = close_B[t] - close_B[t-L]</code></pre>
      </article>
      <article class="score-block">
        <h3>ATR + smoothing</h3>
        <p>
          ATR is Wilder RMA of True Range. It normalizes moves by typical volatility so we compare
          apples to apples.
        </p>
        <pre class="score-code"><code>TR_t = max(
  high_t - low_t,
  abs(high_t - close_{t-1}),
  abs(low_t - close_{t-1})
)
ATR_t = WilderRMA(TR_t, L)</code></pre>
      </article>
      <article class="score-block">
        <h3>Power‑surge protection</h3>
        <p>
          We floor denominators and clamp extreme benchmark “power” to prevent blow‑ups during quiet
          sessions.
        </p>
        <pre class="score-code"><code>floor_t = rolling_quantile(den, q=0.05, window=252)
safe_div(num, den, floor) = num / max(den, floor)
power = clip(power, -pmax, +pmax)</code></pre>
      </article>
    </section>

    <section class="scores-grid">
      <article class="score-card">
        <h3>RRS formula</h3>
        <pre class="score-code"><code>power_t    = clip( safe_div(ΔB_t, ATR_B_t, floor_B), ±pmax )
expected_t = power_t * ATR_S_t
RRS_t      = safe_div(ΔS_t - expected_t, ATR_S_t, floor_S)</code></pre>
        <p>
          Intuition: if the benchmark moved by X ATR units, we expect the symbol to move by the
          same volatility‑scaled amount. RRS is the residual outperformance.
        </p>
      </article>
      <article class="score-card">
        <h3>RRV formula (volume variability)</h3>
        <pre class="score-code"><code>v_t   = log(max(volume_t, 1))  (default)
v_t   = SMA(v_t, smooth)
dv_t  = v_t - v_{t-1}  (winsorized optional)
var_t = sqrt( WilderRMA(dv_t^2, L) )
RRV_t = safe_div(ΔS_t - power*var_S, var_S, floor_S)</code></pre>
        <p>
          Intuition: RRV answers “Did price move more than expected given relative volume
          variability?”
        </p>
      </article>
      <article class="score-card">
        <h3>RVE formula (volatility expansion)</h3>
        <pre class="score-code"><code>ATR_S_t = WilderRMA(TR_S_t, atr_period)
ATR_B_t = WilderRMA(TR_B_t, atr_period)
dATR_t  = ATR_t - ATR_{t-1}
var_t   = sqrt( WilderRMA(dATR_t^2, L) )
RVE_t   = safe_div(ΔATR_S - power*var_S, var_S, floor_S)</code></pre>
        <p>
          Intuition: RVE measures whether the symbol’s volatility is expanding faster (or slower)
          than the benchmark’s volatility expansion.
        </p>
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

    <section class="score-breakdown">
      <article class="score-block">
        <h3>Intraday options decision tree</h3>
        <p>
          This runs on 5‑minute bars and is deterministic. It uses RRS/RRV/RVE + Groww option chain
          IV to choose a strategy.
        </p>
        <pre class="score-code"><code>Time gate: 09:25–14:45 IST
BULL if:
  rrs_mkt &gt; 0.5 AND rrs_sec &gt; 0 AND rrs_sec_vs_mkt ≥ 0
BEAR if:
  rrs_mkt &lt; -0.5 AND rrs_sec &lt; 0 AND rrs_sec_vs_mkt ≤ 0

Regime:
  BUY_PREMIUM  if rve &gt; 0.3 and iv_atm ≤ iv_ref
  SELL_PREMIUM if rve &lt; -0.3 and iv_atm ≥ iv_ref</code></pre>
      </article>
      <article class="score-block">
        <h3>Strategy selection</h3>
        <pre class="score-code"><code>BULL:
  BUY_PREMIUM + rrv&gt;0 → BUY_CALL
  SELL_PREMIUM → BULL_PUT_SPREAD
  else → BULL_CALL_SPREAD

BEAR:
  BUY_PREMIUM + rrv&lt;0 → BUY_PUT
  SELL_PREMIUM → BEAR_CALL_SPREAD
  else → BEAR_PUT_SPREAD</code></pre>
      </article>
      <article class="score-block">
        <h3>Greeks + liquidity filters</h3>
        <p>Contracts are filtered before scoring:</p>
        <pre class="score-code"><code>open_interest ≥ OI_min
volume ≥ VOL_min
ltp ≥ ltp_min
spread_pct ≤ spread_max
theta_ratio = abs(theta)/ltp ≤ theta_ratio_max</code></pre>
      </article>
      <article class="score-block">
        <h3>Option scoring (heuristic)</h3>
        <pre class="score-code"><code>score = -|delta - target|/span
      + 0.2*ln(1+OI) + 0.1*ln(1+Vol)
      - 1.5*theta_ratio - 0.5*spread_pct
      - iv_penalty (for buy options)</code></pre>
        <p>
          The highest score wins. Spreads use a short leg in the 0.15–0.30 abs‑delta band and a
          further OTM hedge leg.
        </p>
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
