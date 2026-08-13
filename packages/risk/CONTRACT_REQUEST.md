# Contract request: additive Risk Engine V2 fields

Requester: Liêu Hoài Phúc (Risk)

Contract owner: Đỗ Ngọc Tân

Status: proposed; `packages/contracts/` is intentionally unchanged by the Risk implementation.

## Backward-compatible additions requested

1. Extend `BaselineRisk` without removing or renaming `var_0`, `cvar_0`,
   `portfolio_weights`, or `alpha`:
   - `cash_weight: float`
   - `ticker_order: list[str]`
   - `risk_metrics: RiskMetrics`
2. Add `RiskMetrics` with:
   - expected horizon return;
   - worst scenario maximum drawdown;
   - VaR and CVaR at 0.95, 0.975, and 0.99;
   - tail counts, scenario count, and `decimal_nav` units.
3. Add `RiskEvaluation` with before/after `RiskMetrics`, selected action ids/tickers,
   turnover, fee/spread/liquidity breakdown, post-trade NAV/cash/weights, constraint
   violations, and recommendation status.

## Unchanged canonical boundaries

- `ActionEffectsSchema`: `action_id`, `ticker`, `g`, `c`.
- `PairwiseEffectsSchema`: `action_i`, `action_j`, `C_ij`, storing only `i < j`.
- `action_id` remains the zero-based position in `scenario_manifest.ticker_order`.

The current Risk producer validates both canonical DataFrame schemas and writes the proposed
extra baseline fields in a backward-compatible JSON object. The public Risk-owned evaluator
currently returns the proposed evaluation payload through `qshield_risk.RiskEvaluation`.

## Workflow V2 additions requested

The following additions are proposed for Contracts-owner review. Risk does not publish them as
shared canonical schemas until that review is approved.

1. Add public payloads mirroring the Risk-owned types:
   - `RiskPolicy`: version/status/appetite, cash band, CVaR budget, turnover, do-not-sell,
     per-asset caps, optional minimum trade, and regime inputs as provenance only;
   - `ConstraintViolation`: `code`, `field`, `observed`, `limit`, and `message`;
   - `TailUncertainty`: percentile-bootstrap interval, resample count, seed, observed tail
     count, warnings, and `scenario_monte_carlo_only` scope;
   - `CandidateGateResult`: coverage, stability, thresholds, reasons, and separate analysis /
     baseline-handoff decisions.
2. Extend `FinancialObjective` additively with structured constraint details, policy metadata,
   and recommendation status while preserving all existing fields and legacy string violations.
3. Register Risk V2 artifacts with common provenance fields: `run_id`, `profile_id`,
   `profile_status`, `schema_version`, `producer`, `config_version`, `config_hash`,
   `policy_version`, `parent_hashes`, and `gate_status`.
4. Register split labels and manifest fields for `true_objective_samples.parquet`; the Risk
   producer owns true labels, while Quantum owns surrogate coefficients and solver outputs.

Until approved, these fields are Risk-owned extensions. Existing canonical Risk v1 columns and
the zero-based `action_id` convention remain unchanged.
