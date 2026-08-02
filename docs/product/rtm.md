# Requirements Traceability Matrix (RTM)

Tài liệu này liên kết **Scope Statement → Product Requirement → User Story → Acceptance Criteria →
Quality Gate → Test Evidence** cho toàn bộ Q-SHIELD. Đây là artifact bắt buộc trước khi Product
Scope chuyển từ `Baseline Candidate` sang `Approved`
(`docs/product/mvp_scope.md` §24 mục 7, `docs/product/product_requirements.md` §25).

Owner: Nguyễn Thị Ánh Ngọc (Product Owner). RTM phải được cập nhật mỗi khi một requirement chuyển
trạng thái — không chỉnh sửa RTM đã publish của một run/release đã đóng, mà tạo version mới.

---

## 1. Cách đọc bảng

Mỗi dòng nối một **domain nghiệp vụ** xuyên suốt 4 tài liệu nguồn:

| Cột | Nguồn | Ý nghĩa |
|---|---|---|
| Scope range | `docs/product/mvp_scope.md` (`FUNC-*`, `DATA-*`, `BR-*`, `NFR-*`) | Chức năng/quy tắc được phê duyệt trong phạm vi |
| Requirement range | `docs/product/product_requirements.md` (`PR-<DOMAIN>-*`) | Yêu cầu có thể lập trình/kiểm thử |
| User Story range | `docs/product/user_stories_backlog.md` (`US-<DOMAIN>-*`) | Góc nhìn người dùng, INVEST |
| Acceptance Criteria range | `docs/product/acceptance_criteria.md` (`AC-<DOMAIN>-*`) | Given–When–Then, có mức chặn release |
| Quality Gate | `product_requirements.md` §21 / `acceptance_criteria.md` §16 | Cổng nghiệm thu chặn release |

`Test case (TC-<DOMAIN>-*)` và `Evidence path` chưa tồn tại tại thời điểm viết tài liệu này (chưa có
Test Plan riêng) — cột đó để trống có chủ đích và phải điền khi Test Plan được tạo, theo đúng schema
`acceptance_evidence` ở `acceptance_criteria.md` §2.3.

---

## 2. Ma trận truy xuất chính

| Domain | Scope range | Requirement range | User Story range (Epic) | Acceptance Criteria range | Quality Gate | Module owner |
|---|---|---|---|---|---|---|
| Run & Portfolio Intake | FUNC-001–005 | PR-RUN-001–012 | US-RUN-001–006 (EPIC-01) | AC-RUN-001–012 | GATE-01 Scope/Config | NGOC/TÂN |
| Data, Universe & Eligibility | FUNC-006–010, DATA-001–015 | PR-DAT-001–020 | US-DAT-001–006 (EPIC-02) | AC-DAT-001–014 | GATE-02 Data | MINHANH |
| Market Regime / HMM | FUNC-011–015 | PR-REG-001–015 | US-REG-001–005 (EPIC-03) | AC-REG-001–012 | GATE-03 Regime | TÚ |
| Scenario Engine | FUNC-016–021 | PR-SCN-001–015 | US-SCN-001–005 (EPIC-04) | AC-SCN-001–012 | GATE-04 Scenario | TÚ |
| Risk Engine | FUNC-022–027 | PR-RSK-001–020 | US-RSK-001–003 (EPIC-05) | AC-RSK-001–015 | GATE-05 Risk | PHÚC |
| Candidate Selection & Stress Policy | FUNC-028–036 | PR-CAN-001–015 | US-CAN-001–004 (EPIC-05) | AC-CAN-001–012 | GATE-06 Candidate | PHÚC/TÚ |
| Objective Sampling & QUBO | FUNC-037–047 | PR-QUB-001–017 | US-QNT-001–004 (EPIC-06) | AC-QUB-001–015 | GATE-07 QUBO | TÂN/PHÚC |
| Solver (Exact / QAOA / Classical) | FUNC-048–054 | PR-SLV-001–015 | US-QNT-005–008 (EPIC-06) | AC-SLV-001–013 | GATE-08 Solver | TÂN |
| True Re-ranking, Polishing & Accounting | FUNC-055–068 | PR-FIN-001–018 | US-FIN-001–006 (EPIC-07) | AC-FIN-001–015 | GATE-09 Finance | PHÚC/TÂN |
| Dashboard & Reporting | FUNC-069–077 | PR-UI-001–018 | US-UI-001–006 (EPIC-08) | AC-UI-001–012 | GATE-10 Product | TÂN/NGOC |
| Configuration & Registries | FUNC-078–081 (part) | PR-CFG-001–013 | US-GOV-001–004 (EPIC-09) | AC-GOV-001–014 | GATE-01 Scope/Config | NGOC/TÂN |
| Audit & Reproducibility | FUNC-078–081 (part) | PR-AUD-001–012 | US-AUD-001–002 (EPIC-09) | AC-GOV-001–014 | Toàn bộ 10 gate (cross-cutting) | TÂN |
| Operations & Fallback | FUNC-078–081 (part) | PR-OPS-001–010 | US-OPS-001–002 (EPIC-09) | AC-GOV-001–014 | GATE-08/GATE-10 | TÂN |
| Non-Functional Requirements | NFR-001–023 | PR-NFR-COR/REL/REP/PERF/SEC/UX/EXP/MNT | Rải trong mọi epic (enabler stories, §13 user_stories_backlog.md) | AC-NFR-001–018 | GATE-10 Product | Toàn đội |

---

## 3. Cổng nghiệm thu (Quality Gates) — tổng hợp điều kiện pass

| Gate | Điều kiện tối thiểu | Owner | Chặn release |
|---|---|---|---:|
| GATE-01 Scope/Config | Scope, Decision Log và Config Registry nhất quán; không giá trị nào mâu thuẫn | NGOC | Có |
| GATE-02 Data | Schema, temporal integrity, eligibility, Data Quality Report pass | MINHANH | Có |
| GATE-03 Regime | HMM converged, ổn định qua seed, diễn giải được kinh tế | TÚ | Có |
| GATE-04 Scenario | Scenario validation (moments, tail, tương quan chéo) pass | TÚ/PHÚC | Có |
| GATE-05 Risk | Unit test CVaR/cost/turnover/accounting pass | PHÚC | Có |
| GATE-06 Candidate | Top-K deterministic, coverage & cash policy hợp lệ | PHÚC | Có |
| GATE-07 QUBO | Surrogate validation pass, QUBO hash khóa | TÂN/PHÚC | Có |
| GATE-08 Solver | Exact reference + QAOA/classical benchmark cùng QUBO hash, không cherry-pick seed | TÂN | Có |
| GATE-09 Finance | True re-ranking, zero-lock, bound ±5pp (nếu bật), accounting reconcile pass | PHÚC | Có |
| GATE-10 Product | Dashboard khớp artifact, UAT pass, disclaimer hiển thị | NGOC | Có |

Một requirement chỉ chuyển `Verified` khi toàn bộ Acceptance Criteria P0 liên quan ở trạng thái
`PASS` và gate tương ứng đạt (`acceptance_criteria.md` §18 "Definition of Accepted").

---

## 4. Trạng thái hiện tại

Tại thời điểm viết tài liệu này, `packages/*/src` và `backend/src` là scaffold (module, hàm và
`configs/*.yaml` đã có đường dẫn nhưng thân hàm/tham số **chưa được hiện thực**). Vì vậy:

- Toàn bộ `Acceptance Criteria` ở trạng thái `NOT_RUN`.
- Chưa có Test Plan/Test Case (`TC-*`) chính thức — cột test case trong bảng §2 chưa thể điền.
- RTM này mô tả **đích cần đạt** (theo Product Requirements baseline), không mô tả tiến độ code.
  Theo dõi tiến độ triển khai thực tế qua `docs/Structure.md` §4 (phân công) và nhánh git tương ứng
  từng `packages/<module>/`.
- **Lưu ý quan trọng:** phạm vi kỹ thuật đã khóa trong `CLAUDE.md` (8 mã, K=3, một mức giảm 20%) hẹp
  hơn phạm vi mô tả trong Product Requirements (30 mã, top 10, 4 mức hành động, polishing ±5pp). Khi
  requirement nào thuộc phần đã bị thu hẹp (ví dụ toàn bộ nhóm `PR-CAN-*` về top-10 selection, hoặc
  `PR-FIN-007–012` về polishing), phải gắn `DEFERRED` với lý do "ngoài phạm vi R1 đã khóa" thay vì để
  `NOT_RUN` vô thời hạn. Xem `docs/limitations.md` §1 để biết bảng đối chiếu đầy đủ.

## 5. Cách cập nhật RTM

1. Khi một requirement được implement: thêm `test_case_ids`, `evidence_paths`, `run_id` vào Acceptance
   Evidence tương ứng (`acceptance_criteria.md` §2.3), rồi cập nhật dòng domain liên quan trong bảng
   §2 với trạng thái mới.
2. Không tự thêm cột hay đổi ID đã publish; mọi thay đổi cấu trúc RTM là thay đổi Config
   Registry-level, cần Product Owner phê duyệt (`mvp_scope.md` §22).
3. RTM chỉ được coi là "hoàn tất" khi mọi `PR-*` P0/P1 có ít nhất một `AC-*` và mọi `AC-*` P0 có
   `PASS` evidence trước UAT sign-off.
