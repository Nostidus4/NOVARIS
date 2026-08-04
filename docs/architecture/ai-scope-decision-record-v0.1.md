# AI Scope Decision Record v0.1

**Status:** DRAFT — discussion record; not an Approved Decision Log or Config Registry.

**Owner:** Nguyễn Anh Tú (AI/ML)

**Scope:** locked prototype only. No code or config has been modified by this record.

## Decisions adopted in this working session

1. AI internals are generic in `N` assets with explicit ticker order/mapping. The current directed scope validates `N=8`; its scenario tensor is `(S, 20, 8)`, with `S=2,000` in development and `S=5,000` for final evidence. This supersedes the stale 500-scenario statement in `CLAUDE.md` pending repository reconciliation.
2. AI owns HMM regime inference and scenario generation. Phúc owns Scenario Validation Gate specification, thresholds, acceptance decision, and sign-off; AI produces the cube, provenance, and raw validation evidence. CVaR, portfolio accounting, candidate selection, QUBO, and Quantum solvers are out of scope.
3. HMM downstream inference must be causal: filtered forward-only probabilities/labels feed Scenario, Risk, and Quantum. Viterbi/smoothed outputs are diagnostics only.
4. HMM candidate feature direction is market-level, not `8 × returns`. Proposed feature family is return, volatility, drawdown, correlation, and relative illiquidity. Exact field contract/config remains pending.
5. Registered HMM seed list proposed for approval: `[101, 202, 303, 404, 505, 606, 707, 808, 909, 1001]`. All registered seed results must be retained and reported.
6. HMM canonical selection direction: stability medoid with deterministic tie-break, not unreported best-seed selection. Exact gates/thresholds remain pending validation calibration.
7. Scenario implementation is generic in `(S, H, N)`; the directed validator requires `S=2,000` for development or `S=5,000` for final evidence, `H=20`, `N=8`, and block length `5`.
8. A scenario day is always the full cross-asset return vector. No independent ticker bootstrap is permitted.

## Regime output contract proposal for Tân verification

### Core causal parquet fields

One row per feature trading date:

- `date` — non-null date.
- `method` — `hmm | rule_based`, non-null.
- `inference_status` — proposed `ok | warmup`; complete model failure is a run/stage failure, not a usable parquet row.
- `filtered_raw_state_id` — `0..2 | null`.
- `filtered_label` — `normal | volatile | stress | null`.
- `p_normal_filtered`, `p_volatile_filtered`, `p_stress_filtered` — floats in `[0,1] | null`.

Rules:

- HMM + `ok`: all three probabilities are finite/non-null and sum to one within config tolerance; label equals their argmax.
- `warmup`: retain the date row; all regime/probability fields are null; no latest-label backfill.
- Rule-based fallback: label may be present but raw HMM state and probabilities are null. It must not be presented as calibrated probability.
- Scenario/Risk/Quantum consume only the `filtered_*` fields.

### Diagnostic-only fields

If included, they must be explicitly named and excluded from downstream conditioning:

- `viterbi_raw_state_id`, `viterbi_label` — global path, non-causal.
- `p_normal_smoothed`, `p_volatile_smoothed`, `p_stress_smoothed` — forward-backward posterior, non-causal.

### Required regime summary provenance

`regime_summary.json` (or a RunContext-written equivalent) must include method, gate status, model/config/data versions, windows, feature contract version, seed-level results for all registered seeds, raw-state-to-semantic-label mapping, state profiles, selection rationale, stability matrices, and fallback reason where applicable.

## Scenario conditioning policy proposal

### Anchor semantics

At evaluation date `t`:

```text
target_regime = filtered_label(t)
```

For each eligible historical anchor date `d`:

```text
filtered_label(d) == target_regime
source return block = [d+1, d+2, ..., d+5]
d + 5 <= t
```

The anchor label is filtered/causal at `d`. The return block deliberately begins at `d+1`, avoiding conditioning on the same return observation that contributed to the state inference at `d`.

Do not require future labels for days `d+1...d+5` to match the anchor regime. That would condition on regime persistence and change the target distribution.

### Block eligibility

Reject the entire block if any block date has missing/invalid returns, a date gap, or absent assets. Do not fill returns, drop individual assets, or shorten a block.

All accepted daily observations are full return vectors in one explicit ticker order.

### Scenario construction

- Four length-five blocks sampled with replacement from the target-regime anchor pool make one 20-day scenario.
- Repeat for 2,000 scenarios in development or 5,000 scenarios for final evidence.
- Output shape: `(S, 20, 8)`; current directed scope uses `(2,000, 20, 8)` or `(5,000, 20, 8)`.
- Manifest/provenance must retain target regime, conditioning method, seed, candidate/eligible block counts, reuse statistics, ticker order, data/model/config versions, and quality-gate status.

## Scenario open decisions and source gaps

| ID | Decision | Proposal / default for discussion | Source gap or conflict | Owner required |
|---|---|---|---|---|
| MD-00 | Whether PR/AC principles apply to locked scope | Reference principles apply only when non-conflicting and explicitly adopted; locked values override full-design numbers. | `docs/limitations.md §1` distinguishes scopes, but does not define PR/AC applicability. | Ngọc |
| SCN-OD-01 | Rule-based fallback may condition bootstrap | Conditional approval; disclose `regime_method=rule_based`; no probability claim. | Fallback is referenced in `docs/limitations.md §3`, `docs/Structure.md §8`, but no Scenario policy/config exists. | Ngọc / Tú / Phúc |
| SCN-OD-02 | Pool scarcity/reuse as gate metric | Add `eligible_block_count` and reuse metric; calibrate threshold on validation, then lock pre-test. | `configs/scenarios.yaml` has only S/H/block length; `data_contracts.md §4.4` lists validation metrics but no pool/reuse gate. | Ngọc |
| SCN-OD-03 | Hard label vs probability mixture conditioning | Hard `filtered_label(t)` for locked prototype. | `PR-SCN-005` delegates regime-consistent policy; architecture/docs do not choose hard vs mixture. | Phúc / Tú |
| SCN-OD-04 | Reference distribution for scenario validation | Regime-matched realized future returns after eligible anchors, cutoff at evaluation date. | `AC-SCN-008` says historical validation data; it does not define target-regime matching. | Phúc / Tú |
| SCN-OD-05 | Warm-up/null regime behavior | Fail closed; never use latest available label. | No null/warm-up representation in current stub `schemas/regime.py`; product docs only say block when no valid model. | Tân / Tú |
| SCN-OD-06 | State-return time alignment | Filtered anchor label at `d`; returns `d+1...d+5`. | No anchor/index alignment semantics in pipeline or data-contract docs. | Phúc / Tú |
| SCN-OD-07 | Missing/gap/invalid block policy | Reject full block. Data policy itself remains Data Owner responsibility. | `configs/data.yaml` leaves missing policy/min history null; CLAUDE prohibits return forward-fill. | Minh Anh / Tú |
| SCN-OD-08 | Ticker-order artifact and mapping | Persist explicit ticker-order artifact alongside scenario cube; Risk maps by ticker, never position implicitly. | Product docs require ticker order but contracts/path schema are currently stubs. | Tân / Phúc |
| SCN-OD-09 | Scenario manifest ownership | Bootstrap returns metadata; RunContext writes the artifact/metadata. | CLAUDE permits only RunContext to write run metadata; manifest path/format not yet contracted. | Tân |

## Governance rule for unanswered decisions

An unanswered owner decision may use the documented default only in a DRAFT / NON_BASELINE_RUN. The run must record the unresolved decision and applied draft default. It cannot be used as final evidence, UAT evidence, or slide/demo evidence until the designated owner/approver confirms it. Any later decision change requires a new scenario, risk, and optimization run ID.
