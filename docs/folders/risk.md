# packages/risk/

**Owner:** Liêu Hoài Phúc
**Vai trò:** CVaR / chi phí / ranking candidate / surrogate samples / rerank / true-objective.
**Workflow-v2:** §12–14 (cash/risk/top-N/action), §17 (walk-forward metrics).
**Implementation flow:** [`packages/risk/RISK_WORKFLOW_IMPLEMENTATION_PLAN.md`](../../packages/risk/RISK_WORKFLOW_IMPLEMENTATION_PLAN.md).

`packages/risk/RISK_ENGINE.md` mô tả compatibility path Risk v1 (8 mã/K=3). Không dùng tài liệu
legacy đó làm flow triển khai cho profile `workflow_update`.

## Nhiệm vụ

- Đánh giá portfolio trên scenario cube: VaR/CVaR (loss), drawdown, cost, liquidity.
- Quy ước: `L = -R`; CVaR trên **loss**; α=0.95 (Rockafellar–Uryasev) — trung bình đuôi, không phải quantile đơn.
- Sinh `g`, `C`, `c` (hoặc four-level tương đương) cho QUBO.
- Chọn dynamic top 10 candidate từ universe 30 mã.
- Rerank bằng true objective + local polishing (±5pp, zero-lock) — owner Phúc.
- True-CVaR benchmark sau solver.

## Cây chính

```text
qshield_risk/
  metrics.py, drawdown.py, costs.py, portfolio.py, actions.py
  evaluate.py, objective.py, normalize.py
  candidates.py, sampling.py
  rerank.py, true_benchmark.py
  cli.py
```

## Được làm

- Import từ `contracts` (+ nhận scenarios từ AI qua artifact/tham số).
- Được import bởi `quantum` cho true CVaR (mũi tên ngược **duy nhất** được phép).
- Position ineligible vẫn tính risk nếu user đang giữ (workflow-v2 §8).

## Không được làm

- Công thức tài chính trong backend/frontend.
- Ép mọi portfolio tăng đúng 10% cash khi đã chuyển sang cash band (CR-WF2-002) — hiện code có thể còn TL-009.
- Bỏ cash khỏi tổng weight — tổng stock + cash = 1.0 sau mọi action.
- Soft-delete outlier.

## Artifact điển hình

- `risk/action_effects.csv`, `candidate_top10.csv` / `candidate_order.json`
- `risk_summary.json`, rerank / recommendation artifacts (profile)

## Context cho Claude

- Test tài chính quan trọng nhất repo: `packages/risk/tests/` — mỗi công thức cần ví dụ tính tay.
- Surrogate samples: không chỉ 211/211 fit — cần holdout (workflow-v2 §15).
- Materiality: cải thiện khi true CVaR giảm đủ ngưỡng relative sau cost.

## Test

```bash
uv run pytest packages/risk -q
```
