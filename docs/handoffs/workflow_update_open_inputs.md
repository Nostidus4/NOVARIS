# Workflow Update — Open Inputs and Owner Handoff

Tài liệu này liệt kê các đầu vào còn thiếu để chuyển đường chạy development
`NON_BASELINE_RUN` thành baseline UAT chính thức sau 3 approval gate.

Đường code `30 → top-10 → 20-bit → exact-fallback → rerank → true-benchmark` đã có
(`qshield-pipeline workflow-update`). Không dùng artifact development làm bằng chứng UAT.
Giá trị trong `configs/provisional/workflow_update_downstream.yaml` = Decision-package
đã map máy đọc được (xem `docs/handoffs/decision_package_config_map.md`), nhưng vẫn
cần owner sign-off gate trước khi đổi status.

Checklist ngắn: `docs/handoffs/team_lead_decision_todolist.md`.

## 0. Registry giá trị (đã map Decision-package — chờ gate)

Nguồn máy đọc được: `configs/provisional/workflow_update_downstream.yaml`
(`workflow-update-decision-package-v3`).

| TL | Trạng thái code | Còn cần owner |
|---|---|---|
| TL-001…004 Data | CLOSED in code (universe_30, evidence ADJ_UNVERIFIED, eligibility) | Data Gate sign-off / evidence thật từng mã |
| TL-005 scenarios 5000 | CLOSED in config | Scenario Gate trên cube 30 |
| TL-007…011 costs/cash/ranking | CLOSED in config + risk | Product Gate |
| TL-012 QAOA seeds | CLOSED in config; runtime 20-qubit hang → exact fallback | Perf note / optional 10-seed khi khả thi |
| TL-014 surrogate thresholds | PROVISIONAL in config | Owners chốt số qua ask doc |
| TL-015…018 benchmark/rerank/materiality | CLOSED in code (`benchmark-true`, materiality 1%) | Product Gate |
| TL-019…023 governance/underfill/fallback | CLOSED in pipeline guards | 3 gate signatures |

## 1. Data gate

Owner chính: Nguyễn Đỗ Minh Anh. Approver sản phẩm: Nguyễn Thị Ánh Ngọc.

- [x] Code: `universe_30_asof_20260803.csv`, eligibility, DQ, evidence report (có thể ADJ_UNVERIFIED)
- [ ] Sign-off Evidence adjusted close từng mã (không chấp nhận silent close→adj)
- [ ] Checksum/version universe + Source Registry quyền dùng
- [x] Data range TL-003 trong config (`asset_train_start` / `test_end`)

## 2. Scenario gate

Producer: Nguyễn Anh Tú. Reviewer/approver gate: Liêu Hoài Phúc.

- [x] Code: cube `(S, 20, N)` với S=5000 trong provisional; gate validation CLI
- [ ] Sign-off thresholds + exception policy trên cube 30 mã
- [ ] Xác nhận `gate_status=PASS` artifact dùng cho UAT

## 3. Transaction cost và accounting

Owner: Liêu Hoài Phúc. Approver: Nguyễn Thị Ánh Ngọc.

- [x] Code: fee+spread vs liquidity tách (TL-008); Decision costs trong provisional
- [ ] Product Gate approve sensitivity low/base/high nếu cần báo cáo chính thức

## 4. Candidate ranking / rerank / materiality

- [x] Code: top-10 dynamic, rerank top-20, polish ±5pp, materiality 1%, `benchmark-true`
- [ ] Product Gate trên `final_recommendation.json` + `true_benchmark.json`

## 5. Quantum / GATE-08

- [x] Code: BenchmarkReport contract, NON_FINAL seed floor, timeout budget hooks, exact fallback
- [ ] Full 10-seed QAOA 20-qubit runtime trên máy reference (hiện hang → exact-only)
- [ ] Peak memory + hardware fields điền số thật khi chạy notebook 04

## 6. Không làm / không tuyên bố

- Không quantum advantage
- Không trộn `demo_fast` với `workflow_update`
- Không đổi provisional thresholds sau khi đã nhìn kết quả final
