# Architecture Review: bilibili-fav-classifier

Generated: 2025-07-22

## Hot Spots (from commit history)

| File | Commits touched | Lines | Role |
|------|----------------|-------|------|
| `classify.py` | 5/5 | 680 | God module — collect + enrich + classify + apply |
| `rules.py` | 1/5 | 184 | Classification rules (added in refactor) |
| `config.py` | 3/5 | 45 | Constants + unused helpers |
| `mappings.py` | 3/5 | 32 | Seed mapping I/O (shallow) |

## Candidates for Deepening

### 1. classify.py — Four Modules in One Trench Coat (STRONG)

**Problem:** 680 lines containing 4 distinct jobs with zero internal separation:
- Lines 67–221: Async Playwright browser automation
- Lines 227–328: Sync HTTP enrichment (requests, serial)
- Lines 333–424: Pure classification orchestration
- Lines 471–680: API apply engine with WAF retry

**Deletion test:** Deleting classify.py concentrates all logic. It is the real core — cannot delete.

**Interface depth:** Only `classify_video` (26 lines) has a testable interface. The other 654 lines have zero direct tests.

**Solution:** Split into 4 modules: `collect.py`, `enrich.py`, `classify.py` (orchestration), `apply.py`. Each gets its own seam, its own tests.

**Before/After:**
```
BEFORE:                          AFTER:
classify.py (680 lines)          collect.py    ~150 lines  (async browser)
  ├─ collect()                   enrich.py     ~100 lines  (sync HTTP + cache)
  ├─ enrich_meta()               classify.py   ~150 lines  (pure orchestration)
  ├─ classify_video()            apply.py      ~250 lines  (API + retry)
  ├─ autoclassify()              __init__.py   re-exports entry points
  ├─ genplan()
  ├─ apply()
  ├─ _fetch_video_meta()
  ├─ _batch_move()
  ├─ _api_get/_api_post
  └─ ...
```

**Benefits:**
- Locality: each module has one reason to change
- Leverage: apply.py can be tested with injected HTTP client; enrich.py can be tested with cached fixtures
- Test surface: each module gets its own test file

### 2. Cookie/CSRF Loading — No Single Seam (STRONG)

**Problem:** The same cookie-parsing pattern appears 3 times in classify.py:
- Line 67: Playwright async save
- Line 227: `_get_session()` (exists but never called by apply)
- Line 524: `apply()` inline reimplementation

`config.get_cookies()` exists but is never called by classify.py.

**Deletion test:** Deleting the duplicates concentrates the pattern into one function.

**Solution:** One `session.py` module: `load_session() -> Session` (cookies + csrf + headers). All 3 call sites use it.

**Benefits:**
- Locality: session lifecycle in one place
- Leverage: test session loading once, all callers benefit
- Eliminates the dead `config.get_cookies()` / `get_csrf()`

### 3. apply() — No Injectable Seams (WORTH EXPLORING)

**Problem:** apply() at lines 513–653 is the most complex function. It reads files, calls APIs, sleeps, creates folders, moves videos — all hardcoded. Zero tests.

**Solution:** Extract an `HttpClient` adapter interface. apply() accepts it as a parameter. Tests pass a fake client that records calls.

**Benefits:**
- Testability: apply logic testable without network
- Locality: retry/sleep logic encapsulated in adapter

### 4. rules.py — Spurious Re-Import (SPECULATIVE)

**Problem:** rules.py:178–184 imports `save_seed_mappings` from mappings.py then re-exports a wrapper. Creates confusion about ownership.

**Solution:** Delete the wrapper. Callers import from mappings.py directly.

### 5. genplan() — Dead Code (SPECULATIVE)

**Problem:** genplan() at lines 427–465 is untested, undocumented in the docstring, and bypasses all classification layers. Appears to be abandoned.

**Solution:** Delete it (or document it as an intentional simplification path).

### 6. Seed Mappings — Silent UP Ambiguity (SPECULATIVE)

**Problem:** A UP主 can appear in multiple folders. Last-write-wins silently. No validation.

**Solution:** Add a validation function that checks for duplicates and warns at load time.

## Top Recommendation

**Candidate #1 (split classify.py)** is the highest-leverage change. It turns a 680-line god module into 4 focused modules, each with its own seam and test surface. The other candidates (#2 cookie centralization, #3 apply seams) naturally follow from the split, as each extracted module gets its own session handling and test strategy.
