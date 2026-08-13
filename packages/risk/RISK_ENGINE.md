# Risk Engine v1

> **Compatibility documentation only.** Tài liệu này mô tả API nhị phân 8 mã/K=3 của Risk v1.
> Profile `workflow_update` không dùng K=3; flow triển khai V2 nằm tại
> [`RISK_WORKFLOW_IMPLEMENTATION_PLAN.md`](RISK_WORKFLOW_IMPLEMENTATION_PLAN.md) và Product SoT là
> [`docs/workflow-v2.md`](../../docs/workflow-v2.md).

Tài liệu này mô tả implementation hiện tại trong `packages/risk/`. Nguồn chuẩn cho hợp đồng liên
module vẫn là `packages/contracts/`; các tài liệu product rộng hơn không được hiểu là tính năng đã
implement nếu chúng nằm trong phần **Deferred** bên dưới.

## 1. Phạm vi đã khóa

- 8 mã theo đúng `scenario_manifest.ticker_order`.
- 500 scenario, mỗi scenario dài 20 phiên.
- Input là **simple daily returns**, không dùng log returns để tính portfolio wealth.
- Một action bán 20% vị thế hiện tại của đúng một mã và chuyển proceeds sang cash.
- Quantum chọn đúng `K=3`; Risk vẫn chấm true risk cho bitstring sai K và báo violation riêng.
- CVaR 95% là chỉ tiêu chính; 97,5% và 99% là robustness outputs.
- Một lần rebalance trước horizon, sau đó buy-and-hold; không daily rebalance.
- Cash có return bằng 0 trong horizon v1.

## 2. Vị trí trong pipeline

```text
AI scenarios
  scenario_manifest.json + stress_scenarios.npz
                    |
                    v
Risk effects
  baseline_risk.json + action_effects.csv + pairwise_effects.csv
                    |
                    v
Quantum exact/QAOA
  winner bitstring
                    |
                    v
qshield_risk.evaluate
  true before/after net CVaR + violations
```

Risk không import AI hoặc Quantum. CLI chỉ giao tiếp qua `Config`, `ArtifactPaths`, `RunContext` và
artifact contracts. Import hợp lệ theo chiều ngược lại là Quantum gọi public API
`qshield_risk.evaluate` để chấm lại nghiệm bằng true CVaR.

## 3. Input boundary

Run thật đọc:

- `scenario_manifest.json`: phải có `gate_status="PASS"`, `input_source="real"`,
  `return_type="simple"`, đúng shape metadata và ticker order.
- `stress_scenarios.npz`: dùng key `scenarios`; key `ticker_order` phải khớp manifest và Config.
- `sample_portfolio_weights`: ticker-keyed stock weights từ Config.
- `sample_portfolio_cash_weight`: mặc định hiện tại là 0 nếu chưa khai báo.
- cost rates và weight tolerance: phải là giá trị tường minh, không được `null`.

Scenario cube có shape `(S, H, N) = (500, 20, 8)`. Mọi giá trị phải finite và lớn hơn `-1`. Risk
không reorder cube theo portfolio; thay vào đó portfolio weights được map theo ticker sang đúng asset
axis của cube.

`--mock` dùng fixture deterministic do Risk sở hữu và ghi `input_source="mock"`. Fixture này chỉ để
test wiring, không phải baseline evidence. Mock vẫn yêu cầu cost config tường minh để không đưa giả
định phí production vào code.

## 4. Timeline và wealth path

Tại evaluation date, Risk nhận portfolio weights và scenario cube đã được tạo chỉ từ thông tin hợp lệ
đến thời điểm đó. Action được xem như thực hiện một lần trước bước đầu tiên của scenario horizon.

Với simple return `r[s,t,i]`, growth của tài sản là:

```text
G[s,t,i] = product(u=0..t) (1 + r[s,u,i])
```

Portfolio wealth path sau giao dịch là:

```text
W[s,t] = sum_i(stock_amount_after[i] * G[s,t,i]) + cash_amount_after
```

`stock_amount_after` và `cash_amount_after` là amount trên pre-trade NAV=1, không phải normalized
post-cost weights. Không có daily rebalance trong horizon.

Terminal simple return và loss:

```text
R[s] = W[s,H-1] / 1 - 1
L[s] = -R[s] = 1 - W[s,H-1]
```

Loss dương nghĩa là lỗ. Toàn bộ VaR/CVaR được tính trên phân phối loss này.

## 5. VaR, CVaR và drawdown

Tại confidence level `alpha`:

```text
VaR_alpha  = quantile(L, alpha)
CVaR_alpha = mean(L where L >= VaR_alpha)
```

Mọi observation tie tại VaR đều được đưa vào tail, nên `tail_count` có thể lớn hơn đúng
`(1-alpha)*S`. Output luôn ghi tail count thực tế cho từng confidence level.

Expected horizon return là mean của terminal simple returns. Maximum drawdown được tính từ wealth,
không tính trực tiếp từ returns:

```text
running_peak[s,t] = max(initial_NAV, W[s,0], ..., W[s,t])
drawdown[s,t]     = W[s,t] / running_peak[s,t] - 1
```

`worst_scenario_max_drawdown` là giá trị âm nhỏ nhất trên toàn bộ scenario và horizon. Initial NAV=1
được đưa vào running peak, vì vậy transaction cost có thể tạo drawdown ngay tại bước đầu.

## 6. Action, cost và accounting

Với action `i` được chọn:

```text
sale_i      = 0.20 * current_weight_i
gross_sales = sum_i(sale_i)
```

Cost rates là decimal rates trên gross sold notional:

```text
fee_cost       = gross_sales * fee
spread_cost    = gross_sales * spread
liquidity_cost = gross_sales * liquidity_penalty
total_cost     = fee_cost + spread_cost + liquidity_cost
```

Post-trade accounting:

```text
stock_amount_after[i] = current_weight_i - sale_i
cash_amount_after     = cash_before + gross_sales - total_cost
NAV_after             = 1 - total_cost
```

Amounts phải reconcile về `NAV_after`. Normalized post-trade weights được tính bằng cách chia amounts
cho `NAV_after` và phải cộng lại bằng 1 trong `weight_sum_tolerance`. Input portfolio sai không được
auto-normalize.

Turnover v1 là tổng gross stock weight đã bán trên pre-trade NAV=1.

## 7. QUBO effects

Risk tách gross risk effect và transaction cost để tránh double-count:

```text
g_i  = CVaR_0 - CVaR_i_gross
R_ij = CVaR_0 - CVaR_ij_gross
C_ij = g_i + g_j - R_ij
c_i  = transaction_cost(action_i)
```

`gross` nghĩa là sale proceeds đã chuyển sang cash nhưng cost chưa bị trừ. `g`, `C_ij` và `c` dùng
raw decimal-NAV units; Risk v1 không scale component. `pairwise_effects.csv` chỉ ghi cặp `i < j`.
Quantum chịu trách nhiệm chuyển các cặp này sang matrix convention mà không double-count.

## 8. Public evaluator

Public entry point:

```python
qshield_risk.evaluate(
    bitstring,
    scenarios,
    ticker_order,
    weights,
    cash_weight,
    config,
)
```

Evaluator thực hiện full post-cost accounting và trả:

- before/after `RiskMetrics`;
- selected action ids và tickers;
- turnover và cost breakdown;
- NAV, cash và normalized weights sau giao dịch;
- constraint violations;
- `improves_cvar` hoặc `no_improvement` theo true net CVaR 95%.

Bitstring phải dài 8 và chỉ chứa 0/1. Sai cardinality K không làm mất true risk result; violation được
trả riêng. Sai shape hoặc giá trị bitstring là malformed input và bị reject.

## 9. Artifacts và provenance

CLI `qshield-risk effects` ghi ba canonical artifacts sau khi toàn bộ validation pass:

- `baseline_risk.json`;
- `action_effects.csv` — đúng 8 rows;
- `pairwise_effects.csv` — đúng 28 rows `i < j`.

`RunContext` ghi config snapshot, data version, metrics summary và logs. Trong dev mode, Risk xóa stale
canonical outputs trước khi xử lý để run fail không để lại artifact cũ trông như kết quả mới.

Các trường mở rộng `cash_weight`, `ticker_order`, nested `risk_metrics` và `RiskEvaluation` đang chờ
Contracts owner phê duyệt theo `CONTRACT_REQUEST.md`. Risk không tự sửa shared schema.

## 10. Reproduce và verify

Từ repository root:

```text
uv sync --all-packages
uv run pytest packages/risk -q
uv run pytest packages/contracts/tests/test_schemas_risk.py -q
uv run ruff check packages/risk
uv run mypy packages/risk/src/qshield_risk
```

Run thật chỉ hợp lệ khi Scenario Gate PASS và `configs/base.yaml` có approved cost/tolerance values.
Không thay `null` bằng một con số ngầm chỉ để lệnh chạy qua.

## 11. Deferred, không có trong v1

- Confidence interval và low-tail stability warning cho CVaR 99%.
- Low/base/high cost sensitivity.
- Canonical composite `financial_objective()` và component scaling.
- Cross-regime guardrail hoặc weighted-regime objective.
- Dynamic transition smoothing, persistent portfolio state và buy-back.
- Variable K, universe lớn hơn 8 mã hoặc broker execution.

Q-SHIELD là decision-support prototype. Risk Engine không gửi lệnh giao dịch và không được mô tả như
một hệ thống bảo đảm lợi nhuận hoặc quantum advantage.
