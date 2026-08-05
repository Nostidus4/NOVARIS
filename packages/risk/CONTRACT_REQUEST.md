# Contract request: Risk Engine v1

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
