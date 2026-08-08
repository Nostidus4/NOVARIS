# packages/ai/

**Owner:** Nguyễn Anh Tú
**Vai trò:** Regime HMM + sinh / validate kịch bản stress.
**Workflow-v2:** §10 (regime), §11 (scenarios).

## Nhiệm vụ

- Train Gaussian HMM 3 state; gán nhãn **theo thống kê** (return/vol/drawdown), không theo state id.
- Output posterior: `p_normal`, `p_volatile`, `p_stress` + confidence.
- Moving-block bootstrap regime-conditioned → scenario cube `(S, H, N)`.
- Scenario validation (moment, tail, correlation, reuse…).
- CVAE chỉ challenger — mặc định tắt cho đến khi bootstrap pass.

## Cây chính

```text
qshield_ai/
  regime/{train,labeling,feature_set,selection,evaluate,output}.py
  scenarios/{bootstrap,validate}.py
  scenarios/cvae/{model,train,sample}.py   # optional
  baseline/rule_based_regime.py            # fallback khi HMM fail
  cli.py
```

## Được làm

- Multi-seed đã đăng ký trong `configs/base.yaml` — báo hết, không cherry-pick.
- Scenario pool chỉ dùng dữ liệu `<= t` tại evaluation date.
- Soft/hard regime conditioning theo config đã duyệt.

## Không được làm

- Giả định `state 0 = Normal` (bug im lặng — CLAUDE quy tắc 7).
- Bootstrap từng ticker độc lập (mất tương quan chéo) — lấy nguyên vector N tài sản/ngày.
- Dùng outcome `t+1..t+H` để sinh recommendation tại `t`.
- Thêm feature HMM ngoài contract đã khóa (giữ đúng số feature trong config).

## Artifact điển hình

- `regime/regime_daily.parquet`, `regime_summary.json`
- `scenarios/stress_scenarios.npz` + validation / gate JSON

## Context cho Claude

- `workflow_update`: S=2000|5000, N=30 (xem `configs/base.yaml` / profile).
- Stress sample rỗng / reuse cao → WARN/FAIL theo Scenario Gate (workflow-v2 §11).
- Fallback rule-based phải disclose `regime_method`.

## Test

```bash
uv run pytest packages/ai -q
```
