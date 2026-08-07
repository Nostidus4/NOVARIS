# AI Input Proposal v0.1 — Tú cần gì, từ ai, để chạy được Regime + Scenarios

**Status:** DRAFT — đề xuất để các owner xác nhận. Không có code/config nào bị sửa bởi tài liệu này.

**Owner:** Nguyễn Anh Tú (AI/ML)

**Đối tượng đọc:** Minh Anh (Data), Tân (Contracts/Pipeline/Backend), Phúc (Risk), Ngọc (PO/duyệt config).

**Căn cứ:** `docs/archive/ai-scope-decision-record-v0.1.md` (DR v0.1, archived),
`docs/architecture/ai-decisions-v0.2.md` (quyết định hiện hành),
`packages/contracts/src/qshield_contracts/schemas/features.py` (Feature Contract v0.1),
trạng thái repo tại commit `05d787e`.

**Phạm vi tài liệu:** chỉ nói về **đầu vào** mà AI cần nhận. Không đề xuất thay đổi công thức của
module khác, không lấn sang CVaR/QUBO/solver.

---

## 0. TL;DR — mỗi người cần đưa gì

| Người | Thứ AI chờ nhiều nhất | Chặn stage nào | Mức |
|---|---|---|---|
| **Minh Anh** | 8 mã + thứ tự chuẩn, `date_range` train/val/test, `returns.parquet` có log return, **cột volume/giá trị khớp lệnh** cho feature illiquidity, lịch phiên giao dịch chuẩn | Toàn bộ Regime + Scenarios | P0 |
| **Tân** | `Config`, `ArtifactPaths`, `RunContext`, `validate_or_raise`, `mocks/*`, `schemas/regime.py`, `schemas/scenarios.py` — hiện đều là stub một dòng | AI không ghi được artifact nào đúng quy tắc 8/13 | P0 |
| **Phúc** | Đơn vị return của tensor kịch bản (log hay simple) + ngày đánh giá `t` + spec Scenario Validation Gate (metric, ngưỡng, ai ký) | Scenarios không có tiêu chí pass/fail | P0 |
| **Ngọc** | Chốt `S = 500` hay `2.000/5.000`; fallback rule-based có được dùng làm evidence không | Kích thước tensor + tư cách bằng chứng của run | P0 |
| **Tú (tự làm)** | HMM, labeling, selection, bootstrap engine, validation metrics, baseline, test — chạy trên fixture tự sinh | — | Đang làm |

Chi tiết từng mục ở §3. Thứ tự cần theo thời gian ở §5.

---

## 1. Trạng thái repo tại `05d787e` — cơ sở của mọi phát biểu bên dưới

Đây là bằng chứng cho cột "đã có / chưa có" trong các bảng sau, không phải phàn nàn.

| Thứ | Đường dẫn | Trạng thái thực |
|---|---|---|
| Feature Contract v0.1 | `schemas/features.py` | **Đã có, chạy được**, có test |
| Schema returns / regime / scenarios / risk / optimization | `schemas/*.py` | Stub 1 dòng comment |
| `Config`, `ArtifactPaths`, `RunContext`, `validate_or_raise` | `contracts/*.py` | Stub 1 dòng comment |
| `mocks/returns.py`, `mocks/features.py`, `mocks/regime.py` | `contracts/mocks/` | Stub 1 dòng comment |
| Data: returns, features, split, manifest, loaders | `packages/data/` | Stub 1 dòng comment |
| AI: regime, scenarios, baseline | `packages/ai/` | Stub 1 dòng comment; chỉ `cli.py` có khung Typer `NotImplementedError` |
| `configs/universe.yaml` | `tickers`, `sample_portfolio_weights`, `snapshot_date` | Toàn bộ `null` |
| `configs/data.yaml` | `source`, 6 mốc `date_range`, `missing_data_policy`, `min_history_sessions` | Toàn bộ `null` |
| `configs/regime.yaml` | `seeds.values`, `features` | `null` (n_states/n_iter/covariance_type đã khóa) |
| `configs/scenarios.yaml` | `seed` | `null`; `num_scenarios: 500` đang là giá trị khóa |
| `configs/base.yaml` | `seed` | `null` |

**Hệ quả quan trọng:** giả định trong `CLAUDE.md` rằng "cả 5 người bắt đầu từ ngày 1 trên mock" hiện
**chưa thành lập** — `contracts/mocks/` chưa hiện thực. Vì vậy AI đang tự sinh fixture nội bộ trong
`packages/ai/tests/` (xem §4), và sẽ bỏ fixture đó ngay khi `mocks/` có thật. Đây là lý do
IN-CTR-08 được xếp P0.

---

## 2. Rà soát DR v0.1 — những điểm cần sửa trước khi coi là ổn

Tổng thể DR v0.1 **dùng được làm cơ sở**: nó đúng vai (AI sinh cube + evidence, Phúc sở hữu gate),
đúng nguyên tắc nhân quả (filtered-only xuống downstream, Viterbi/smoothed chỉ là chẩn đoán), đúng
quy tắc 7 (gán nhãn theo thống kê), không tự tiện sửa config, và có governance rule cho quyết định
chưa trả lời. Sáu điểm dưới đây cần xử lý.

| ID | Vấn đề | Vì sao đáng sửa | Đề xuất | Owner |
|---|---|---|---|---|
| DR-R-01 | DR §1 tuyên bố `S=2.000/5.000` **supersedes** `CLAUDE.md` | Năm nguồn đang khóa `500`: `CLAUDE.md`, `configs/scenarios.yaml` (`num_scenarios: 500`), `docs/architecture/data_contracts.md §4.4`, `docs/limitations.md §1`, và `docs/Structure.md` (bàn giao của chính Tú ghi "tensor 500×20×8", "đủ 500 kịch bản đúng shape"). `limitations.md §1` xếp việc quay lại thiết kế gốc là **Change Request** theo `mvp_scope.md §22`, không phải điều chỉnh nhỏ. Một DR do AI sở hữu không đủ thẩm quyền supersede scope đã khóa. | Hạ DR §1 xuống thành **đề xuất mở** (`SCN-OD-10`), owner Ngọc. AI hiện thực generic `(S,H,N)` nên đổi `S` là đổi config, không đổi code. Mặc định chạy `S=500` cho tới khi có phê duyệt. | Ngọc |
| DR-R-02 | Feature Contract v0.1 được commit vào `packages/contracts/` (package của Tân), trong khi `configs/regime.yaml: features` vẫn `null` | Hai nguy cơ: (a) commit chéo quyền sở hữu chưa có review của Tân; (b) rủi ro hai nguồn sự thật giữa contract-in-code và config, vi phạm tinh thần quy tắc 8. | Tân review và nhận ownership file. Chốt: danh sách feature **sống trong contract code**, còn `configs/regime.yaml` chỉ ghi `feature_contract_version: v0.1` — cấu hình tham chiếu contract, không lặp lại danh sách. | Tân + Tú |
| DR-R-03 | `market_illiquidity_relative_20d` khai `window_sessions=250` | Tên field nói 20 phiên, trường nói 250. Consumer nào tính warm-up hoặc kiểm tra window theo `window_sessions` sẽ hiểu sai. Hai cửa sổ ở đây là khác nhau về bản chất: 20 phiên trung bình, 250 phiên baseline. | Tách thành `window_sessions=20` và thêm `baseline_window_sessions=250`; giữ nguyên tên field và `warmup_sessions=250` của contract. Version bump `v0.1` → `v0.2` nếu Tân xác nhận đây là breaking. | Tú |
| DR-R-04 | Fallback rule-based: DR nói "label có, probability null"; `data_contracts.md §4.3` nói `regime_daily.parquet` có **3 cột xác suất tổng = 1**, và `docs/Structure.md` đặt điều kiện xong việc của Tú là "có probability chứ không chỉ hard label" | Nếu schema bắt buộc non-null thì fallback không ghi được dòng nào; nếu nới lỏng thì mọi consumer downstream phải xử lý null. Ngoài ra một run chỉ có fallback sẽ không đạt điều kiện xong việc của chính stage AI — đây là lý do IN-PO-02 phải được trả lời sớm. Phải quyết trước khi Tân viết `schemas/regime.py`, không phải sau. | Nới schema cho phép null cho `p_*` khi `method=rule_based` hoặc `inference_status=warmup`, kèm invariant: `method=hmm AND inference_status=ok ⇒ ba xác suất non-null và tổng = 1 ± tolerance`. | Tân + Tú |
| DR-R-05 | DR không định nghĩa **ngày đánh giá `t`** | Toàn bộ §"Anchor semantics" phụ thuộc `filtered_label(t)`, nhưng `t` là do Risk/PO chọn (ngày định giá danh mục), không phải AI tự chọn. Thiếu `t` thì không sinh được cube cuối cùng, dù engine đã xong. | Thêm quyết định mở `SCN-OD-11`: `t` = ngày giao dịch cuối của test period, hoặc một ngày được ghi trong `configs/`. Owner Phúc/Ngọc. | Phúc/Ngọc |
| DR-R-06 | DR không nêu **đơn vị/quy ước return** của tensor `(S,H,N)` | Risk tính `L_s = -R^(H)_{p,s}`; cộng dồn 20 ngày bằng tổng log return hay tích `(1+r)` cho kết quả khác nhau. Đây là nguồn lỗi dấu/đơn vị điển hình đã được `CLAUDE.md` cảnh báo. | Thêm quyết định mở `SCN-OD-12`, owner Phúc. Đề xuất mặc định của AI: tensor chứa **log return theo ngày**, ghi rõ trong manifest (`return_type: log`). | Phúc |

Một điểm nhỏ: `HMM_FEATURE_CONTRACT_V1.validate_or_raise()` gọi ở cuối `features.py` so chính hằng số
với chính nó nên luôn pass — nó là smoke-check lúc import, không phải kiểm định. Giá trị thật của
`validate_or_raise()` nằm ở phía consumer. Không phải lỗi, chỉ cần không nhầm nó là bằng chứng.

---

## 3. Đầu vào theo từng thành viên

Ký hiệu trạng thái: **CÓ** = dùng được ngay · **STUB** = có file, chưa có nội dung · **CHƯA** = chưa
tồn tại ở bất kỳ nguồn nào.

### 3.1. Nguyễn Đỗ Minh Anh — Data

Đây là nhánh chặn nặng nhất: không có returns thật thì cả HMM lẫn bootstrap đều không có gì để chạy
ngoài fixture.

| ID | AI cần | Dạng cụ thể | Dùng để làm gì | Trạng thái | Mức |
|---|---|---|---|---|---|
| IN-DATA-01 | Danh sách 8 mã + **thứ tự chuẩn** + `snapshot_date` | `configs/universe.yaml: tickers` (list 8 chuỗi, thứ tự có ý nghĩa) | Trục `N` của tensor `(S,20,8)`; mọi feature cross-sectional; mapping ticker cho Risk | CHƯA (`null`) | P0 |
| IN-DATA-02 | Mốc train / validation / test | 6 field `date_range` trong `configs/data.yaml` | Scaler `fit` **chỉ** trên train (quy tắc 4); cắt anchor pool; chọn `t` | CHƯA (`null`) | P0 |
| IN-DATA-03 | `returns.parquet` đúng schema | Long format `(date, ticker)`, có `log_return` và `simple_return`, đã điều chỉnh corporate action | Input trực tiếp của cả 5 feature và của block bootstrap | STUB | P0 |
| IN-DATA-04 | **Volume / giá trị khớp lệnh** | Cột `volume` và (ưu tiên) `turnover_value` VND theo `(date, ticker)` | Feature #5 `market_illiquidity_relative_20d` (Amihud cần mẫu số thanh khoản). Hiện `data_contracts.md §4.1` **không** liệt kê cột này, dù `PR-DAT-005` yêu cầu `volume` ở mức PRS | CHƯA trong hợp đồng artifact | P0 |
| IN-DATA-05 | Chính sách ngày thiếu / không hợp lệ | `missing_data_policy`, `min_history_sessions` + cách **đánh dấu**: giữ dòng với null hay bỏ dòng | DR "reject cả block" chỉ thực thi được nếu AI phân biệt được ngày thiếu với ngày không tồn tại | CHƯA (`null`) | P0 |
| IN-DATA-06 | Lịch phiên giao dịch chuẩn | Danh sách trading date của giai đoạn, hoặc cột cờ `is_trading_day` | Phân biệt "date gap" thật với nghỉ lễ. Không có nó thì luật loại block theo gap sẽ loại nhầm hàng loạt | CHƯA | P0 |
| IN-DATA-07 | `features.parquet` đúng Feature Contract v0.1 | 5 cột raw + `date`; **giữ nguyên dòng ngày warm-up với giá trị null**, không backfill | Input duy nhất của HMM | STUB | P0 |
| IN-DATA-08 | `data_manifest.json` (hash + `data_version`) | `data/metadata/data_manifest.json` | Ghi provenance trong `regime_summary.json` và scenario manifest | STUB | P1 |
| IN-DATA-09 | Quality report của giai đoạn dùng để fit | Số ngày thiếu, mã bị loại, outlier được gắn cờ | Báo cáo trung thực cùng kết quả regime; không tự lọc outlier (quy tắc 5) | STUB | P1 |

**Đặc tả cột `features.parquet` mà AI đề nghị Data emit** (đây là bản diễn giải field-level của
Feature Contract v0.1 — nếu Data thấy công thức nào không khả thi, phản hồi trước khi code):

| Cột | Kiểu | Cửa sổ | Định nghĩa AI đang giả định | Null khi nào |
|---|---|---|---|---|
| `date` | date, non-null, unique | — | Ngày giao dịch | Không bao giờ |
| `market_return_1d` | float64 | 1 | Trung bình **cross-sectional, equal-weight** log return của 8 mã tại `t` | Khi bất kỳ mã nào trong 8 mã không có return hợp lệ tại `t` (fail closed) |
| `market_volatility_20d` | float64 | 20 | Độ lệch chuẩn trượt 20 phiên của `market_return_1d`, dữ liệu tới `t` | Warm-up hoặc có null trong cửa sổ |
| `market_max_drawdown_60d` | float64, `<= 0` | 60 | Max drawdown trượt 60 phiên của market wealth index | Warm-up hoặc có null trong cửa sổ |
| `mean_pairwise_corr_60d` | float64 | 60 | Trung bình tương quan cặp sau biến đổi Fisher-z, 28 cặp, cửa sổ 60 phiên | Warm-up hoặc có null trong cửa sổ |
| `market_illiquidity_relative_20d` | float64 | 20 (baseline 250) | Trung bình 20 phiên của Amihud tương đối so với median trượt 250 phiên | Warm-up, hoặc theo chính sách zero-volume ở IN-DATA-10 |

| ID | Quyết định cần Data chốt cùng AI | Đề xuất mặc định |
|---|---|---|
| IN-DATA-10 | Ngày volume = 0 xử lý sao trong Amihud | Không chia cho 0, không thay bằng epsilon tùy tiện: đánh dấu ngày đó null và ghi log. Nếu Data có quy ước sẵn thì dùng quy ước của Data |
| IN-DATA-11 | `market_return_1d` equal-weight hay theo tỷ trọng danh mục mẫu | Equal-weight — feature mô tả **thị trường**, không nên phụ thuộc danh mục người dùng nhập |
| IN-DATA-12 | Data hay AI tính 5 feature | Theo Feature Contract v0.1: **Data tính raw field**, AI chỉ transform + scale. Nếu Data không kịp, AI nhận tính tạm và ghi rõ trong provenance là lệch hợp đồng |

### 3.2. Đỗ Ngọc Tân — Contracts / Pipeline / Backend

Không có nhánh này thì AI **không được phép** ghi bất kỳ artifact nào đúng quy tắc: quy tắc 8 cấm nối
path, quy tắc 13 cấm module tính toán tự ghi metadata.

| ID | AI cần | Dạng cụ thể | Vì sao AI không tự làm được | Trạng thái | Mức |
|---|---|---|---|---|---|
| IN-CTR-01 | `schemas/regime.py` hiện thực | Chốt tập field theo DR: `date`, `method`, `inference_status`, `filtered_raw_state_id`, `filtered_label`, `p_*_filtered`; field chẩn đoán tách tên riêng | Schema là ranh giới giữa AI và Risk/Quantum; đổi sau là breaking change | STUB | P0 |
| IN-CTR-02 | `schemas/scenarios.py` hiện thực | Key trong `.npz`, dtype, shape `(S,20,8)`, **mảng ticker order đi kèm cube**, field manifest bắt buộc (SCN-OD-08/09), và cột của `scenario_validation.csv` (artifact bàn giao thứ 4 theo `docs/Structure.md`) | Risk map theo ticker, không map theo vị trí; AI cần biết đặt tên key gì | STUB | P0 |
| IN-CTR-03 | Review + nhận ownership `schemas/features.py` | Xác nhận v0.1, xử lý DR-R-03 (window 20 vs 250), quyết định version bump | File nằm trong package của Tân | Đã có nội dung, **chưa review** | P0 |
| IN-CTR-04 | `ArtifactPaths` hiện thực | Property cho `regime_daily.parquet`, `regime_summary.json`, `stress_scenarios.npz`, `scenario_manifest.json` | AI không được nối chuỗi path | STUB | P0 |
| IN-CTR-05 | `Config` hiện thực + gộp `includes` | Kèm quyết định DR-R-02: config chỉ ghi `feature_contract_version` | AI không được tự mở YAML | STUB | P0 |
| IN-CTR-06 | `RunContext` hiện thực + API ghi summary | Ai ghi `regime_summary.json` và scenario manifest: RunContext ghi, AI **trả về dict** | Quy tắc 13 | STUB | P0 |
| IN-CTR-07 | `validate_or_raise()` hiện thực | Dùng ở cả input lẫn output của mỗi stage AI | Quy tắc 12 | STUB | P0 |
| IN-CTR-08 | `mocks/returns.py`, `mocks/features.py` | Sinh dữ liệu giả đúng schema, nhận `seed` | Không có mock thì "song song từ ngày 1" chỉ là giả định. AI đang dùng fixture nội bộ thay thế tạm | STUB | P0 |
| IN-CTR-09 | Đăng ký seed vào config | `base.yaml: seed`, `regime.yaml: seeds.values`, `scenarios.yaml: seed` | Cấm hard-code seed (quy tắc 8); AI chỉ **đề xuất** danh sách, không tự đăng ký | CHƯA (`null`) | P1 |
| IN-CTR-10 | Xác nhận stage boundary trong pipeline | `regime` chạy trước `scenarios`; scenarios đọc regime qua artifact hay qua object in-memory | Ảnh hưởng chữ ký hàm public của `qshield_ai` | STUB | P1 |

**Đề xuất seed để Tân đăng ký (AI không tự chốt):** `[101, 202, 303, 404, 505, 606, 707, 808, 909, 1001]`.
Mọi seed đã đăng ký đều phải báo cáo, không chọn seed đẹp nhất (DR §5, §6).

### 3.3. Liêu Hoài Phúc — Risk

AI sản xuất cube và evidence; Phúc sở hữu tiêu chí chấp nhận. Không có §3.3 thì AI có cube nhưng
không có quyền nói nó "đạt".

| ID | AI cần | Vì sao | Trạng thái | Mức |
|---|---|---|---|---|
| IN-RISK-01 | **Đơn vị return của tensor** (DR-R-06): log hay simple; cách cộng dồn 20 ngày | Sai quy ước ở đây làm sai dấu và sai độ lớn CVaR mà không báo lỗi | CHƯA | P0 |
| IN-RISK-02 | **Ngày đánh giá `t`** (DR-R-05) | `target_regime = filtered_label(t)`; không có `t` thì không sinh được cube cuối | CHƯA | P0 |
| IN-RISK-03 | Spec Scenario Validation Gate | Danh sách metric, ngưỡng, luật pass/fail, ai ký. AI nộp mean/std/quantile/skew/kurtosis/corr/tail coverage như evidence thô | CHƯA | P0 |
| IN-RISK-04 | Chốt SCN-OD-03: hard label vs probability mixture | Quyết định cách điều kiện hóa bootstrap | DR đề xuất hard label | P0 |
| IN-RISK-05 | Chốt SCN-OD-04: reference distribution để so | Không có mẫu tham chiếu thì validation chỉ là mô tả, không phải kiểm định | DR đề xuất realized future returns theo regime | P1 |
| IN-RISK-06 | Cần 1 bộ cube (theo regime tại `t`) hay 3 bộ (mỗi regime một bộ) | Ảnh hưởng số lần chạy, thời gian, và cấu trúc artifact | CHƯA | P1 |
| IN-RISK-07 | Chốt SCN-OD-02: pool scarcity / reuse có phải metric gate không | AI đã dự định ghi `eligible_block_count` và tỷ lệ tái sử dụng vào manifest dù có gate hay không | DR đề xuất có | P2 |

### 3.4. Nguyễn Thị Ánh Ngọc — PO / duyệt config

| ID | Cần quyết | Vì sao cần cấp PO | Mức |
|---|---|---|---|
| IN-PO-01 | `S = 500` (scope đã khóa) hay `2.000 / 5.000` (DR §1, DR-R-01) | Đây là Change Request theo `limitations.md §1` + `mvp_scope.md §22`, không phải lựa chọn kỹ thuật của AI. Ghi chú chi phí: code generic `(S,H,N)`, tăng `S` chỉ tốn thời gian chạy và dung lượng, không tốn công code | P0 |
| IN-PO-02 | SCN-OD-01: run dùng fallback rule-based có được coi là evidence hợp lệ không | Quyết định tư cách bằng chứng của kết quả, ảnh hưởng slide/demo | P0 |
| IN-PO-03 | MD-00: nguyên tắc PR/AC áp dụng tới đâu trong scope đã khóa | AI đang phải tự phán đoán khi PRS và scope khóa lệch nhau (chính là gốc của DR-R-01) | P1 |
| IN-PO-04 | Duyệt `configs/regime.yaml` + `configs/scenarios.yaml` sau khi điền | Theo bản đồ repo, `configs/` do Ngọc duyệt | P1 |

---

## 4. AI tự làm được, không chờ ai (đang/sẽ làm)

Những mục này chỉ cần mảng NumPy và tham số truyền vào, nên chạy được trên fixture tự sinh.

| ID | Việc | Phụ thuộc bên ngoài |
|---|---|---|
| SELF-01 | Feature Contract v0.1 + test | Đã xong; còn sửa DR-R-03 |
| SELF-02 | Fixture synthetic returns/features trong `packages/ai/tests/` | Không — sẽ bỏ khi IN-CTR-08 về |
| SELF-03 | `regime/train.py`: GaussianHMM 3 state, `covariance_type=diag`, `n_iter=500`, đa seed | Không |
| SELF-04 | `regime/labeling.py`: xếp hạng state theo thống kê rồi mới gán Normal/Volatile/Stress (quy tắc 7) | Không |
| SELF-05 | `regime/selection.py`: stability medoid + tie-break tất định | Ngưỡng cuối cần calibrate trên validation (cần IN-DATA-02) |
| SELF-06 | Tách filtered (causal) vs Viterbi/smoothed (chẩn đoán) | Không |
| SELF-07 | `regime/evaluate.py`: duration, transition matrix, ổn định qua seed | Không |
| SELF-08 | `scenarios/bootstrap.py`: moving-block generic `(S,H,N)`, lấy nguyên vector N tài sản mỗi ngày | Không |
| SELF-09 | Luật eligibility của block (reject nguyên block khi thiếu/gap/vắng mã) | Cần IN-DATA-05/06 mới thực thi đúng trên dữ liệu thật |
| SELF-10 | `scenarios/validate.py`: tính metric phân phối | Ngưỡng do Phúc (IN-RISK-03) |
| SELF-11 | `baseline/rule_based_regime.py` | Tư cách evidence do Ngọc (IN-PO-02) |
| SELF-12 | Nội dung `regime_summary.json` (dict provenance) | AI **trả về** dict; RunContext ghi (IN-CTR-06) |

AI **không** làm: CVaR/drawdown/chi phí, chọn action, QUBO/QAOA, ngưỡng gate, đặt giá trị config,
sửa schema của package khác.

---

## 5. Đường găng

```
IN-DATA-01 (8 mã)  ─┐
IN-DATA-02 (split)  ├─→ features.parquet (IN-DATA-07) ─→ HMM fit ─→ filtered labels ─┐
IN-DATA-03/04 (returns + volume) ─┘                                                   │
                                                                                      ├─→ cube (S,20,8)
IN-RISK-02 (ngày t) ──────────────────────────────────────────────────────────────────┤
IN-PO-01  (S) ────────────────────────────────────────────────────────────────────────┘
                                                                                      │
IN-CTR-04/05/06/07 (paths/config/runcontext/validate) ────────────────────────────────┴─→ artifact ghi được
IN-RISK-01 (đơn vị return) ─→ cube dùng được cho Risk
IN-RISK-03 (gate) ─────────→ cube được tuyên bố "đạt"
```

Thứ tự đề nghị:

1. **Sớm nhất có thể:** IN-DATA-01, IN-DATA-02, IN-PO-01, IN-RISK-01, IN-RISK-02 — đây là 5 quyết
   định một dòng, không cần code, nhưng chặn mọi thứ phía sau.
2. **Kế tiếp:** IN-CTR-01…08 (Tân), IN-DATA-03/04/05/06 (Minh Anh).
3. **Trước cổng nghiệm thu ngày 4:** IN-RISK-03, IN-DATA-07, IN-CTR-09.
4. Còn lại là P1/P2, ảnh hưởng chất lượng báo cáo chứ không chặn đường chạy.

---

## 6. Nếu input chưa về thì AI làm gì

Theo governance rule của DR v0.1:

- AI dùng default đã ghi trong tài liệu này, đánh dấu run là `DRAFT / NON_BASELINE_RUN`.
- Run đó ghi rõ quyết định nào chưa được trả lời và default nào đã áp dụng.
- Không dùng làm evidence cuối, evidence UAT, hay số lên slide/demo.
- Khi owner chốt khác default, phải sinh **run ID mới** cho scenario, risk và optimization — không
  sửa số của run cũ.

Cụ thể trong lúc chờ: chạy `S=500` (giá trị đang khóa), tensor **log return**, `t` = ngày cuối của
chuỗi fixture, seed theo danh sách đề xuất ở §3.2, feature do AI tính tạm nếu `features.parquet`
chưa có — và tất cả những điều này đều được ghi vào provenance.

---

## 7. Definition of Ready — khi nào AI coi là đã đủ input

**Regime stage sẵn sàng khi:** IN-DATA-01, 02, 03, 07 có thật · IN-CTR-01, 04, 05, 06, 07 chạy được ·
IN-CTR-03 đã review · IN-DATA-04 có hoặc feature #5 được chính thức miễn.

**Scenario stage sẵn sàng khi:** Regime stage xong · IN-RISK-01, 02 đã chốt · IN-PO-01 đã chốt ·
IN-CTR-02 chạy được · IN-DATA-05, 06 có thật.

**Được tuyên bố "đạt" khi:** IN-RISK-03 tồn tại và Phúc ký.
