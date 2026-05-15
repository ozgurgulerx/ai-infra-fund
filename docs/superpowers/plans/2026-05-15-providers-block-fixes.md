# Providers Block Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four high-priority issues surfaced in the review of commit `f131880` (providers block) so the YAML config can be safely consumed by a future fetcher without producing 404s or losing secret-injection sites.

**Architecture:** The validator at `packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py` already parses a `providers:` list in YAML into typed `AIEquityProvider` dataclasses (in-flight uncommitted work). We extend that validator with a new `cik_fanout` dimension and a required `secret_env_var` field when `requires_secret: true`, then fix the YAML data so SEC EDGAR URL templates use the CIK shape, FRED/Finnhub templates expose API-key placeholders, and one provider's identifier is renamed for consistency. Schema-level checks fail loudly at load time so a future consumer never sees malformed provider config.

**Tech Stack:** Python 3.12 dataclasses, PyYAML, pytest (unittest-style classes, see `tests/test_local_input_validators.py` for the existing pattern).

---

## Pre-flight (do once before Task 1)

**Working tree has uncommitted in-flight validator work** at `packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py` (adds `AIEquityProvider` dataclass + `_provider()` validator + `PROVIDER_DATA_CLASSES` constant). Confirm with the user whether to:

- (a) commit that in-flight work first as a separate baseline commit, then apply this plan on top, or
- (b) bundle the in-flight work into the first commit of this plan.

Either way, do **not** revert it — it implements review issue #3 (schema validation). The plan below assumes the in-flight code is your starting point.

Also check that `tests/test_provider_seeder.py` (also uncommitted) exists and covers basic provider parsing — if so, your new tests should sit alongside it and not duplicate.

---

## Task 1: Add `cik_fanout` dimension to the validator

The SEC EDGAR API takes a zero-padded CIK in the URL path, not a ticker query parameter. Today the validator only accepts `ticker_fanout | series_fanout | theme_fanout`. We need a fourth dimension so SEC can declare CIK-based URLs cleanly.

**Files:**

- Modify: `packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py` (the `AIEquityProvider` dataclass at line ~35 and the `_provider()` validator at line ~97)
- Test: `tests/test_local_input_validators.py` (add a new test method on the existing `LocalInputValidatorTests` class)

- [ ] **Step 1: Write the failing test for happy-path cik_fanout**

Add to `tests/test_local_input_validators.py` inside `class LocalInputValidatorTests(unittest.TestCase)`:

```python
    def test_provider_accepts_cik_fanout_with_cik_placeholder(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )

        raw = {
            "version": 1,
            "entries": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "themes": ["ai_accelerators"],
                    "sector_tags": ["semiconductors"],
                    "priority": "critical",
                }
            ],
            "providers": [
                {
                    "source_id": "source_api_sec_edgar",
                    "source_name": "SEC EDGAR",
                    "source_type": "filings_api",
                    "base_url": "https://data.sec.gov",
                    "license_label": "public",
                    "data_class": "public_evidence",
                    "reliability_score": 0.98,
                    "requires_secret": False,
                    "cik_fanout": True,
                    "url_templates": [
                        "https://data.sec.gov/submissions/CIK{cik}.json",
                    ],
                }
            ],
        }

        watchlist = validate_ai_equity_watchlist(raw)

        self.assertEqual(1, len(watchlist.providers))
        provider = watchlist.providers[0]
        self.assertTrue(provider.cik_fanout)
        self.assertFalse(provider.ticker_fanout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_provider_accepts_cik_fanout_with_cik_placeholder -v`

Expected: FAIL — either `AttributeError: 'AIEquityProvider' object has no attribute 'cik_fanout'` or `ValueError` from the fanout-dimension count check.

- [ ] **Step 3: Add `cik_fanout` to the dataclass**

Modify `packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py` — find the `AIEquityProvider` dataclass and add `cik_fanout: bool` after the existing `theme_fanout: bool` line:

```python
@dataclass(frozen=True, slots=True)
class AIEquityProvider:
    source_id: str
    source_name: str
    source_type: str
    base_url: str
    license_label: str
    data_class: str
    reliability_score: float
    requires_secret: bool
    ticker_fanout: bool
    series_fanout: tuple[str, ...]
    theme_fanout: bool
    cik_fanout: bool
    url_templates: tuple[str, ...]
```

- [ ] **Step 4: Extend `_provider()` to read and validate cik_fanout**

In the same file, in `_provider()`, find the `theme_fanout = bool(raw.get("theme_fanout", False))` line and add immediately after:

```python
    cik_fanout = bool(raw.get("cik_fanout", False))
```

Then find the `fanout_flags` list and replace it with:

```python
    fanout_flags = [
        ("ticker_fanout", ticker_fanout),
        ("series_fanout", bool(series_fanout)),
        ("theme_fanout", theme_fanout),
        ("cik_fanout", cik_fanout),
    ]
```

Then find the existing `if theme_fanout and not all(...)` block and add immediately after it:

```python
    if cik_fanout and not all("{cik}" in t for t in url_templates):
        raise ValueError(
            f"provider {index} declares cik_fanout but a url_template "
            f"is missing the {{cik}} placeholder"
        )
```

Finally, in the `return AIEquityProvider(...)` block, add `cik_fanout=cik_fanout,` after `theme_fanout=theme_fanout,`.

- [ ] **Step 5: Run test to verify happy-path passes**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_provider_accepts_cik_fanout_with_cik_placeholder -v`

Expected: PASS.

- [ ] **Step 6: Write the failing test for missing {cik} placeholder rejection**

Add to `tests/test_local_input_validators.py`:

```python
    def test_provider_rejects_cik_fanout_without_cik_placeholder(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )

        raw = {
            "version": 1,
            "entries": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "themes": ["ai_accelerators"],
                    "sector_tags": ["semiconductors"],
                    "priority": "critical",
                }
            ],
            "providers": [
                {
                    "source_id": "source_api_sec_edgar",
                    "source_name": "SEC EDGAR",
                    "source_type": "filings_api",
                    "base_url": "https://data.sec.gov",
                    "license_label": "public",
                    "data_class": "public_evidence",
                    "reliability_score": 0.98,
                    "requires_secret": False,
                    "cik_fanout": True,
                    "url_templates": [
                        "https://data.sec.gov/submissions/CIK0001045810.json",
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, r"\{cik\} placeholder"):
            validate_ai_equity_watchlist(raw)
```

- [ ] **Step 7: Run test to verify it passes (rejection works)**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_provider_rejects_cik_fanout_without_cik_placeholder -v`

Expected: PASS (Step 4 already implemented the rejection path).

- [ ] **Step 8: Commit**

```bash
git add packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py tests/test_local_input_validators.py
git commit -m "feat: add cik_fanout dimension to provider validator

Adds a fourth fanout dimension (cik_fanout) to AIEquityProvider so SEC
EDGAR can declare CIK-based URL templates instead of being shoehorned
into ticker_fanout. The validator enforces {cik} placeholder presence
when cik_fanout is true, matching the existing ticker/series/theme
fanout enforcement."
```

---

## Task 2: Require `secret_env_var` when `requires_secret: true`

Today `requires_secret: true` is a flag with no location. A consumer would have to guess which env var holds the key. Add a required `secret_env_var:` field whenever `requires_secret` is true, validated by the loader.

**Files:**

- Modify: `packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py`
- Test: `tests/test_local_input_validators.py`

- [ ] **Step 1: Write the failing test for the rejection path**

Add to `tests/test_local_input_validators.py`:

```python
    def test_provider_requires_secret_env_var_when_requires_secret_is_true(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )

        raw = {
            "version": 1,
            "entries": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "themes": ["ai_accelerators"],
                    "sector_tags": ["semiconductors"],
                    "priority": "critical",
                }
            ],
            "providers": [
                {
                    "source_id": "source_api_fred",
                    "source_name": "FRED",
                    "source_type": "macro_api",
                    "base_url": "https://api.stlouisfed.org/fred",
                    "license_label": "public",
                    "data_class": "public_market_data",
                    "reliability_score": 0.99,
                    "requires_secret": True,
                    "series_fanout": ["DFF"],
                    "url_templates": [
                        "https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}",
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, r"secret_env_var"):
            validate_ai_equity_watchlist(raw)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_provider_requires_secret_env_var_when_requires_secret_is_true -v`

Expected: FAIL — the YAML currently parses with no error.

- [ ] **Step 3: Add `secret_env_var` to the dataclass**

In `watchlist.py`, modify `AIEquityProvider` to add the field (default `None` so existing rows without secrets are unaffected):

```python
@dataclass(frozen=True, slots=True)
class AIEquityProvider:
    source_id: str
    source_name: str
    source_type: str
    base_url: str
    license_label: str
    data_class: str
    reliability_score: float
    requires_secret: bool
    secret_env_var: str | None
    ticker_fanout: bool
    series_fanout: tuple[str, ...]
    theme_fanout: bool
    cik_fanout: bool
    url_templates: tuple[str, ...]
```

- [ ] **Step 4: Validate `secret_env_var` in `_provider()`**

In `_provider()`, find the `requires_secret = bool(raw.get("requires_secret", False))` line and add immediately after:

```python
    raw_env = raw.get("secret_env_var")
    if requires_secret:
        if not isinstance(raw_env, str) or not raw_env.strip():
            raise ValueError(
                f"provider {index} declares requires_secret=true but is missing "
                f"a non-empty secret_env_var"
            )
        secret_env_var: str | None = raw_env.strip()
    elif raw_env is not None and not isinstance(raw_env, str):
        raise ValueError(
            f"provider {index} secret_env_var must be a string when present"
        )
    else:
        secret_env_var = raw_env.strip() if isinstance(raw_env, str) and raw_env.strip() else None
```

Then in the `return AIEquityProvider(...)` block, add `secret_env_var=secret_env_var,` after `requires_secret=requires_secret,`.

- [ ] **Step 5: Run test to verify rejection works**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_provider_requires_secret_env_var_when_requires_secret_is_true -v`

Expected: PASS.

- [ ] **Step 6: Write the failing test for the accept path**

Add to `tests/test_local_input_validators.py`:

```python
    def test_provider_accepts_secret_env_var_when_requires_secret_is_true(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import (
            validate_ai_equity_watchlist,
        )

        raw = {
            "version": 1,
            "entries": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "themes": ["ai_accelerators"],
                    "sector_tags": ["semiconductors"],
                    "priority": "critical",
                }
            ],
            "providers": [
                {
                    "source_id": "source_api_fred",
                    "source_name": "FRED",
                    "source_type": "macro_api",
                    "base_url": "https://api.stlouisfed.org/fred",
                    "license_label": "public",
                    "data_class": "public_market_data",
                    "reliability_score": 0.99,
                    "requires_secret": True,
                    "secret_env_var": "FRED_API_KEY",
                    "series_fanout": ["DFF"],
                    "url_templates": [
                        "https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}",
                    ],
                }
            ],
        }

        watchlist = validate_ai_equity_watchlist(raw)
        self.assertEqual("FRED_API_KEY", watchlist.providers[0].secret_env_var)
```

- [ ] **Step 7: Run test to verify accept path passes**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_provider_accepts_secret_env_var_when_requires_secret_is_true -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py tests/test_local_input_validators.py
git commit -m "feat: require secret_env_var when provider requires_secret is true

Adds a secret_env_var field to AIEquityProvider that must be a
non-empty string when requires_secret is true. This locates the
secret at config time instead of forcing the consumer to invent
its own env-var-name convention."
```

---

## Task 3: Fix SEC EDGAR URL templates in the YAML

The current SEC URLs use a fake `?frontier_ticker={ticker}` parameter and would 404. SEC EDGAR's real endpoints take a zero-padded CIK in the path. Switch SEC to `cik_fanout: true` (added in Task 1) and provide a separate `cik_lookup_url` so a future consumer can build the ticker→CIK map from SEC's published file.

**Files:**

- Modify: `config/ai_equity_watchlist.yaml` (the `source-api-sec-edgar` block at the top of `providers:`)
- Modify: `packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py` (optional `cik_lookup_url` field)
- Test: `tests/test_watchlist_frontend_parity.py` and the full suite

- [ ] **Step 1: Write the failing test that the production YAML loads cleanly**

Add to `tests/test_local_input_validators.py`:

```python
    def test_production_watchlist_yaml_loads_and_sec_provider_uses_cik_fanout(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        root = Path(__file__).resolve().parents[1]
        watchlist = load_ai_equity_watchlist(root / "config" / "ai_equity_watchlist.yaml")

        sec = next(
            (p for p in watchlist.providers if "sec" in p.source_id.lower()),
            None,
        )
        self.assertIsNotNone(sec, "expected an SEC EDGAR provider in the YAML")
        self.assertTrue(sec.cik_fanout, "SEC provider must declare cik_fanout")
        self.assertFalse(sec.ticker_fanout)
        for template in sec.url_templates:
            self.assertIn("{cik}", template)
            self.assertNotIn("{ticker}", template)
```

Add `from pathlib import Path` to the top of the file if not already imported (it is — line 3).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_production_watchlist_yaml_loads_and_sec_provider_uses_cik_fanout -v`

Expected: FAIL — current YAML has `ticker_fanout: true` and `{ticker}` placeholders for SEC.

- [ ] **Step 3: Optionally extend the dataclass with `cik_lookup_url`**

In `watchlist.py`, add `cik_lookup_url: str | None` to `AIEquityProvider` (default to `None` so other providers are unaffected). In `_provider()`, after the `cik_fanout = bool(...)` line:

```python
    raw_lookup = raw.get("cik_lookup_url")
    if raw_lookup is not None and not isinstance(raw_lookup, str):
        raise ValueError(f"provider {index} cik_lookup_url must be a string when present")
    cik_lookup_url: str | None = raw_lookup.strip() if isinstance(raw_lookup, str) and raw_lookup.strip() else None
```

Add `cik_lookup_url=cik_lookup_url,` to the `return AIEquityProvider(...)` block.

- [ ] **Step 4: Fix the YAML SEC entry**

In `config/ai_equity_watchlist.yaml`, replace the `source-api-sec-edgar` provider block with:

```yaml
- source_id: source_api_sec_edgar
  source_name: SEC EDGAR
  source_type: filings_api
  base_url: https://data.sec.gov
  license_label: public
  data_class: public_evidence
  reliability_score: 0.98
  requires_secret: false
  cik_fanout: true
  cik_lookup_url: https://www.sec.gov/files/company_tickers.json
  url_templates:
    - https://data.sec.gov/submissions/CIK{cik}.json
    - https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
```

Note the source_id has also been switched to snake_case (`source_api_sec_edgar`) for consistency with the rest of the codebase. CIKs in `company_tickers.json` are integers; the consumer is responsible for zero-padding to 10 digits before substitution.

- [ ] **Step 5: Run all watchlist + parity tests**

Run: `python -m pytest tests/test_local_input_validators.py tests/test_watchlist_frontend_parity.py tests/test_equity_research_monitoring.py -v`

Expected: all pass, including the new SEC test from Step 1.

- [ ] **Step 6: Commit**

```bash
git add config/ai_equity_watchlist.yaml packages/core/src/ai_infra_fund_core/local_inputs/watchlist.py tests/test_local_input_validators.py
git commit -m "fix: correct SEC EDGAR provider URL templates

SEC EDGAR's submissions and XBRL endpoints take a zero-padded CIK in
the path, not a ticker query parameter. Switch the SEC provider to
the new cik_fanout dimension with {cik} placeholders, expose the
official company_tickers.json file via a new cik_lookup_url field
so a future consumer can build the ticker->CIK map at fetch time,
and normalize the source_id to snake_case."
```

---

## Task 4: Add API-key placeholders + `secret_env_var` to FRED and Finnhub

Both FRED and Finnhub require an API key. Their URL templates currently omit the `&api_key=` / `&token=` parameter, and there's no `secret_env_var` (added in Task 2).

**Files:**

- Modify: `config/ai_equity_watchlist.yaml` (FRED and Finnhub provider blocks)
- Test: `tests/test_local_input_validators.py`

- [ ] **Step 1: Write the failing test asserting the production YAML has API-key placeholders for secret providers**

Add to `tests/test_local_input_validators.py`:

```python
    def test_production_secret_providers_have_api_key_placeholder_and_env_var(self) -> None:
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        root = Path(__file__).resolve().parents[1]
        watchlist = load_ai_equity_watchlist(root / "config" / "ai_equity_watchlist.yaml")

        secret_providers = [p for p in watchlist.providers if p.requires_secret]
        self.assertTrue(secret_providers, "expected at least one requires_secret provider")
        for provider in secret_providers:
            self.assertIsNotNone(
                provider.secret_env_var,
                f"{provider.source_id} declares requires_secret but has no secret_env_var",
            )
            for template in provider.url_templates:
                self.assertTrue(
                    "{api_key}" in template or "{api_token}" in template,
                    f"{provider.source_id} url_template lacks an api-key placeholder: {template}",
                )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_production_secret_providers_have_api_key_placeholder_and_env_var -v`

Expected: FAIL — neither FRED nor Finnhub have `secret_env_var` set, and templates lack the api-key placeholders.

- [ ] **Step 3: Fix the FRED entry in YAML**

In `config/ai_equity_watchlist.yaml`, replace the `source-api-fred` provider block with:

```yaml
- source_id: source_api_fred
  source_name: FRED (St. Louis Fed)
  source_type: macro_api
  base_url: https://api.stlouisfed.org/fred
  license_label: public
  data_class: public_market_data
  reliability_score: 0.99
  requires_secret: true
  secret_env_var: FRED_API_KEY
  series_fanout:
    - DFF
    - DGS10
    - T10Y2Y
    - INDPRO
    - CPIAUCSL
    - PCEPI
    - PPIACO
    - ELEINDM01USM189S
  url_templates:
    - https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&file_type=json&api_key={api_key}
```

- [ ] **Step 4: Fix the Finnhub entry in YAML**

Replace the `source-api-finnhub` block with:

```yaml
- source_id: source_api_finnhub
  source_name: Finnhub
  source_type: news_event_api
  base_url: https://finnhub.io/api/v1
  license_label: public_free_tier
  data_class: public_evidence
  reliability_score: 0.85
  requires_secret: true
  secret_env_var: FINNHUB_API_KEY
  ticker_fanout: true
  url_templates:
    - https://finnhub.io/api/v1/company-news?symbol={ticker}&token={api_token}
```

- [ ] **Step 5: Run the new test + full watchlist suite**

Run: `python -m pytest tests/test_local_input_validators.py tests/test_watchlist_frontend_parity.py tests/test_equity_research_monitoring.py -v`

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add config/ai_equity_watchlist.yaml tests/test_local_input_validators.py
git commit -m "fix: add api-key placeholders and secret_env_var to FRED and Finnhub

Both providers require an API key. Add the {api_key}/{api_token}
placeholders to their url_templates and the new secret_env_var
field (FRED_API_KEY, FINNHUB_API_KEY) so the consumer can locate
the secret at fetch time. Also normalise their source_id values
to snake_case."
```

---

## Task 5: Normalize remaining `source_id` values to snake_case

Now that SEC/FRED/Finnhub have been renamed, the remaining four providers (yfinance, Stooq, GDELT) still use kebab-case. Rename for consistency with the rest of the codebase.

**Files:**

- Modify: `config/ai_equity_watchlist.yaml`
- Test: `tests/test_local_input_validators.py`

- [ ] **Step 1: Write the failing test asserting all source_ids are snake_case**

Add to `tests/test_local_input_validators.py`:

```python
    def test_production_provider_source_ids_are_snake_case(self) -> None:
        import re
        from ai_infra_fund_core.local_inputs.watchlist import load_ai_equity_watchlist

        root = Path(__file__).resolve().parents[1]
        watchlist = load_ai_equity_watchlist(root / "config" / "ai_equity_watchlist.yaml")
        snake_case = re.compile(r"^[a-z][a-z0-9_]*$")

        offenders = [p.source_id for p in watchlist.providers if not snake_case.match(p.source_id)]
        self.assertFalse(
            offenders,
            f"provider source_ids must be snake_case; got: {offenders}",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_local_input_validators.py::LocalInputValidatorTests::test_production_provider_source_ids_are_snake_case -v`

Expected: FAIL — listing the remaining kebab-case IDs (`source-api-yfinance`, `source-api-stooq`, `source-api-gdelt`).

- [ ] **Step 3: Rename the remaining three source_ids in the YAML**

In `config/ai_equity_watchlist.yaml`:

```
source-api-yfinance  ->  source_api_yfinance
source-api-stooq     ->  source_api_stooq
source-api-gdelt     ->  source_api_gdelt
```

Use a single-pass edit, one rename at a time, to keep the diff minimal.

- [ ] **Step 4: Run the new test + full suite to confirm no regressions**

Run: `python -m pytest tests/test_local_input_validators.py tests/test_watchlist_frontend_parity.py tests/test_equity_research_monitoring.py -v`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add config/ai_equity_watchlist.yaml tests/test_local_input_validators.py
git commit -m "chore: normalise remaining provider source_ids to snake_case

yfinance, Stooq, and GDELT now match SEC/FRED/Finnhub. A new test
keeps the convention enforced going forward."
```

---

## Task 6: Run full test suite + deploy

Final guard against regression: run everything, then redeploy backend (api + worker images carry the YAML).

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q`

Expected: all previously-passing tests still pass. Earlier in the session 313/388 of the suite was green (the 1 failure is in untracked code outside this plan's scope).

- [ ] **Step 2: Confirm with the user whether to deploy**

The YAML now lives in api+worker images via `COPY config /app/config`. To roll the fixed providers into prod, ask the user: "Plan tasks complete. Deploy api+worker now, or wait for a consumer?"

If yes, invoke the `deploy` skill with the `backend` argument.

If no, stop here — the local commits stack behind the existing 8 unpushed commits.

---

## Out of scope (deferred from the review)

These were flagged in the review but are not addressed by this plan:

- **GDELT query quality** — switching from bare ticker to quoted company name. Needs a `company_name_fanout` dimension or per-template substitution variables, which is a bigger refactor than is justified before a consumer exists.
- **License-label accuracy** for yfinance and Stooq (e.g., `public_personal_use_attribution_required`). The validator doesn't enforce a label vocabulary today — adding one is a separate plan.
- **Schema reconciliation with `SourcePolicy`** (`source_name` vs `publisher`). The two schemas serve different purposes (evidence-policy vs fetch-provider); merging them is a design decision worth its own brainstorm.
- **Rate-limiting hints per `source_type`** (e.g., SEC's 10 req/s cap and `User-Agent` requirement). These belong in the consumer, not the static config.

Open a follow-up issue for each if and when a consumer lands.
