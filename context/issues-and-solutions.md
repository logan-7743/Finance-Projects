# Issues and Solutions

Problems encountered, root causes, and the fixes that worked. Read this before starting work to avoid repeating known mistakes.

---

## 2026-05-30 — `create-next-app` scaffolded frontend under `backend/frontend`

**Symptom:** The frontend scaffold appeared in `backend/frontend` instead of top-level `frontend/`.

**Root cause:** The persisted shell working directory was `backend/` when `npx create-next-app frontend ...` ran.

**Fix:** Stop the stalled install, move `backend/frontend` to top-level `frontend/`, then run a clean `npm install` from the correct directory.

**Dead ends (do not retry):** Do not assume shell commands start from the workspace root. Always set `working_directory` explicitly for scaffolding commands.

---

## 2026-05-30 — Backend editable install failed due multiple top-level packages

**Symptom:** `pip install -e ".[dev]"` failed with `Multiple top-level packages discovered in a flat-layout: ['app', 'quant']`.

**Root cause:** `setuptools` automatic package discovery refuses ambiguous flat layouts when more than one top-level package is present.

**Fix:** Add explicit setuptools package discovery in `backend/pyproject.toml`:

```toml
[tool.setuptools.packages.find]
include = ["app*", "quant*"]
```

**Dead ends (do not retry):** Do not rely on default package discovery for this backend layout.

---

## 2026-05-31 — Yahoo Finance rate limits via yfinance (`429` / "Too Many Requests")

**Symptom:** Loading AAPL (or any ticker) returned `Failed to fetch history for 'AAPL': Too Many Requests. Rate limited. Try after a while.`

**Root cause:** yfinance scrapes Yahoo Finance without a commercial license. Parallel history + quote requests, React dev double-mounting, and `ticker.info` for quotes all increase request volume until Yahoo returns HTTP 429.

**Fix:**
- Backend: in-memory TTL cache (5 min history, 1 min quotes), exponential backoff retries on rate-limit errors, quotes use `fast_info` only (skip `ticker.info`), API returns HTTP 429 with a clear message.
- Frontend: fetch history first (chart), then quote; quote failure no longer blocks the chart; parse FastAPI `detail` JSON for readable errors.

**Dead ends (do not retry):** Do not fire history and quote in parallel against yfinance during local dev. Do not call `ticker.info` on every quote refresh.

---

## 2026-05-31 — Dev reloads still caused avoidable market-data calls

**Symptom:** Even with backend TTL cache, local development occasionally hit Yahoo 429s after page reloads.

**Root cause:** The dashboard still fetched data in `useEffect` on load for every mount. Reloads/remounts caused unnecessary API calls.

**Fix:**
- Frontend now uses browser cache-first behavior (localStorage keyed by symbol/range).
- Startup only fetches if cache is missing.
- Added manual **Refresh** button for explicit network updates.
- Refresh uses incremental history fetch (`since=<last_bar_time>`) and merges only new bars.

**Dead ends (do not retry):** Do not auto-refresh market data on component mount when local cache already exists.

---

## 2026-05-31 — Crypto symbols were error-prone for Yahoo format

**Symptom:** Entering common crypto shorthand (`BTC`, `ETH/USD`, `SOLUSD`) often failed unless users knew Yahoo's exact `BASE-USD` symbol format.

**Root cause:** Backend accepted symbols verbatim and did not normalize common crypto input formats.

**Fix:** Added backend symbol normalization for known crypto bases, mapping shorthand inputs to Yahoo format (`BTC-USD`, etc.), and added frontend quick crypto presets.

**Dead ends (do not retry):** Do not rely on users always typing Yahoo-specific crypto ticker formatting manually.

---

## 2026-05-31 — React lint rule blocked localStorage hydration via effect

**Symptom:** Frontend lint failed with `react-hooks/set-state-in-effect` when loading cached indicator configs by calling `setIndicatorConfigs(...)` inside `useEffect`.

**Root cause:** The new React lint rule discourages synchronous state-setting in effect bodies when the value can be derived during initialization.

**Fix:** Switched to lazy `useState` initialization that reads localStorage once on component init, plus safe `window` guards in cache helpers for SSR safety.

**Dead ends (do not retry):** Do not hydrate simple localStorage-backed state by immediately setting state in a mount effect when lazy initialization is viable.

---

## 2026-05-31 — lightweight-charts custom price scale crash in oscillator rendering

**Symptom:** Dashboard crashed with `Trying to apply price scale options with incorrect ID` when indicators with oscillator panes (e.g., OBV) were active.

**Root cause:** `priceScale(...).applyOptions(...)` ran before any series had been added with that custom `priceScaleId`, so the chart model rejected the unknown scale ID.

**Fix:** Add indicator series first (which creates the scale), then apply scale options. Use stable per-indicator oscillator scale IDs.

**Dead ends (do not retry):** Do not apply options to arbitrary custom scale IDs before a bound series exists.

---

## 2026-05-31 — Core test collection could fail when optional market-data deps are missing

**Symptom:** Test collection failed with `ModuleNotFoundError: No module named 'yfinance'` even when running tests that do not use the yfinance data source.

**Root cause:** `quant.data.__init__` eagerly imported `YFinanceSource`, forcing `yfinance` to be installed just to import base data types like `OHLCVBar`.

**Fix:** Made `YFinanceSource` import optional in `quant.data.__init__` via `try/except ModuleNotFoundError`, allowing core quant modules/tests to import without yfinance in minimal environments.

**Dead ends (do not retry):** Do not make package-level imports eagerly depend on optional provider SDKs unless absolutely necessary.

---

## Template

```
## YYYY-MM-DD — Short description of the problem

**Symptom:** What the error or failure looked like.

**Root cause:** Why it happened.

**Fix:** What resolved it.

**Dead ends (do not retry):** Approaches that did not work, so we don't repeat them.
```
