# Hợp đồng dữ liệu (Data Contracts)

**Định nghĩa hình thức nằm trong code, không trong tài liệu này:**
`packages/contracts/src/qshield_contracts/schemas/`. Tài liệu này chỉ tổng hợp để tra cứu nhanh —
khi cần biết chính xác một artifact có cột gì, đọc schema, đừng suy đoán từ tên file hay từ bảng bên
dưới.

`packages/contracts/` là package quan trọng nhất repo: nó là lý do 5 người làm song song trên các
chặng khác nhau của pipeline mà vẫn ráp được với nhau. Một bảng mô tả cột trong tài liệu không chặn
được ai gõ sai tên cột; một schema chạy được (`validate_or_raise()`) thì có.

---

## 1. Nơi mở config và sinh đường dẫn — chỉ một nơi duy nhất

| Việc | Module duy nhất được làm việc này |
|---|---|
| Đọc/gộp `configs/*.yaml` | `qshield_contracts.config.Config` (`config.py`) |
| Sinh đường dẫn artifact | `qshield_contracts.paths.ArtifactPaths` (`paths.py`) |
| Ghi `config.json`, `data_version.json`, `metrics.json`, `logs.txt` | `qshield_contracts.runs.RunContext` (`runs.py`) |
| Validate input/output ở ranh giới module | `qshield_contracts.validate.validate_or_raise()` |

Không hard-code đường dẫn, ticker, seed, ngày hay ngưỡng ở nơi khác — tất cả đọc qua `Config` và
`ArtifactPaths`. Không nối chuỗi path thủ công trong `packages/data`, `packages/ai`, `packages/risk`
hay `packages/quantum`.

## 2. Bảng tham số (`configs/*.yaml`)

| File | Nội dung |
|---|---|
| `base.yaml` | seed, chế độ artifact (`dev`/`runs`), log; gộp các file còn lại qua `includes` |
| `universe.yaml` | 8 mã, tỷ trọng danh mục mẫu |
| `data.yaml` | nguồn dữ liệu, khoảng thời gian, train/val/test split |
| `regime.yaml` | HMM: 3 trạng thái, 10 seed, danh sách feature |
| `scenarios.yaml` | S=500 kịch bản, H=20 ngày, block=5 |
| `risk.yaml` | α=0,95 (CVaR confidence), phí giao dịch, spread, liquidity penalty |
| `quantum.yaml` | K=3 (số hành động được chọn), λ₁, λ₂, penalty P, p=1 (QAOA depth), shots=1024 |

Đổi `artifacts.mode` trong `base.yaml`:

- `dev` → ghi vào `artifacts/dev/`, đường dẫn cố định, dùng khi lặp nhanh.
- `runs` → ghi vào `artifacts/runs/run_YYYYMMDD_HHMM/`, có version — bắt buộc dùng từ ngày 4 của
  sprint vì mọi số lên slide phải truy được về một `run_id`.

## 3. Bảng artifact chính

| Artifact | Schema (nơi định nghĩa) | Hình dạng |
|---|---|---|
| `data/processed/returns.parquet` | `schemas/returns.py` | Long format: một dòng / (`date`, `ticker`) |
| `data/processed/features.parquet` | `schemas/features.py` | Một dòng / ngày |
| `artifacts/.../regime/regime_daily.parquet` | `schemas/regime.py` | Một dòng / ngày + 3 xác suất trạng thái |
| `artifacts/.../scenarios/stress_scenarios.npz` | `schemas/scenarios.py` | **Tensor `(500, 20, 8)`** = (scenario, horizon, asset) |
| `artifacts/.../risk/action_effects.csv` | `schemas/risk.py` | Một dòng / action (vector `g`, ma trận `C`, vector chi phí `c`) |
| `artifacts/.../optimization/qaoa_result.json` | `schemas/optimization.py` | Bitstring thắng + metrics benchmark |

**Đổi schema là breaking change.** Quy trình bắt buộc: sửa `contracts` trước, rồi sửa cả bên ghi
lẫn bên đọc artifact đó trong **cùng một pull request** — không tách PR, vì hai bên sẽ không tương
thích ở giai đoạn trung gian.

---

## 4. Chi tiết từng artifact

### 4.1. `returns.parquet` (Data)

- Long format, khóa chính `(date, ticker)`.
- Có cả simple return và log return.
- **Không forward-fill.** Giá thiếu được xử lý theo quy tắc trong `data.yaml` và phải ghi log; không
  bao giờ `.ffill()` trên cột return.
- Corporate actions (chia tách, cổ tức) đã được điều chỉnh trước khi tính return
  (`clean/corporate_actions.py`).

### 4.2. `features.parquet` (Data)

- Một dòng mỗi ngày giao dịch, ở mức thị trường/tài sản dùng làm input cho HMM.
- Mọi rolling feature **chỉ dùng dữ liệu đến ngày `t`** — không có centered window, không backfill
  từ tương lai.
- Scaler (nếu có) `fit` chỉ trên tập train, `transform` cho validation/test — không fit lại trên
  toàn bộ dữ liệu.

### 4.3. `regime_daily.parquet` (Regime)

- Một dòng mỗi ngày, gồm 3 cột xác suất trạng thái (tổng = 1) và nhãn trạng thái.
- **Nhãn được gán theo đặc trưng thống kê** (return/volatility/drawdown của từng state sau khi fit),
  **không theo state id**. HMM trả state 0/1/2 theo thứ tự ngẫu nhiên tùy seed — giả định "state 0 =
  Normal" là bug im lặng, không phải quy ước có thể dùng.
- Kèm model version và seed dùng để train, để truy xuất được.

### 4.4. `stress_scenarios.npz` (Scenarios)

- Tensor `(500, 20, 8)` = 500 kịch bản × 20 ngày horizon × 8 tài sản trong universe.
- Sinh bằng regime-conditioned moving-block bootstrap, block length 5 — lấy nguyên **vector 8 tài
  sản mỗi ngày** từ cùng một block lịch sử, không bootstrap độc lập từng tài sản (làm vậy sẽ phá vỡ
  tương quan chéo).
- Kèm seed, regime dùng để điều kiện hóa, và validation metrics (mean, std, quantile, skew, kurtosis,
  correlation, tail coverage).

### 4.5. `action_effects.csv` (Risk)

Đầu vào trực tiếp cho QUBO. Với quy ước dấu `L_s = -R^(H)_{p,s}` (loss dương = lỗ, tính trên phân
phối loss chứ không phải return):

- **`g_i`** — mức giảm CVaR khi thực hiện hành động `i` một mình: `g_i = CVaR_0 − CVaR_i`.
- **`C_ij`** — ma trận tương tác cặp hành động: `C_ij = g_i + g_j − R_ij` (`R_ij` là hiệu ứng thật
  khi làm đồng thời cả hai).
- **`c_i`** — vector chi phí giao dịch: `TC_i = |Δw_i| × (fee + spread + liquidity_penalty)`.
- CVaR dùng công thức Rockafellar–Uryasev: `VaR_α = Q_α(L)`, `CVaR_α = E[L | L ≥ VaR_α]`, α = 0,95.
  Đây là **trung bình phần đuôi**, không phải giá trị tại phân vị.
- Tổng tỷ trọng (cổ phiếu + tiền mặt) phải luôn bằng 1,0 sau mọi hành động — invariant kiểm tra ở
  ranh giới `packages/risk`.

### 4.6. `qaoa_result.json` (Optimization)

- Bitstring thắng (K=3 hành động được chọn trong 8 mã), cùng object trace của cả ba cách tính
  objective dùng để đối chiếu ở `verify/consistency.py`.
- Benchmark: exact energy, QAOA energy theo từng seed (không chỉ seed tốt nhất), optimality gap,
  feasibility rate, shots, backend, runtime.
- Nghiệm QAOA **phải được chấm lại bằng true CVaR** qua `qshield_risk.evaluate`, không chỉ bằng giá
  trị objective — objective thấp mà CVaR thực tế không giảm thì nghiệm đó vô nghĩa và phải được báo
  cáo như vậy.

---

## 5. Invariant xuyên suốt mọi artifact

| Invariant | Vi phạm là gì |
|---|---|
| `loss = -return`, CVaR tính trên loss | Lẫn dấu loss/return làm mọi so sánh trước–sau sai |
| Không forward-fill return | `.ffill()` trên cột return |
| Không dùng dữ liệu tương lai | Rolling feature dùng dữ liệu sau ngày `t`; scaler fit trên toàn bộ thay vì chỉ train |
| Không tự xóa outlier | Phải gắn cờ và báo cáo, không âm thầm loại bỏ |
| Tổng tỷ trọng luôn = 1,0 | Kể cả phần tiền mặt, sau mọi hành động |
| Regime label theo thống kê | Không gán cứng theo state id |
| Chỉ `RunContext` ghi metadata | Module tính toán trả về dữ liệu thuần, không tự ghi `config.json`/`logs.txt` |

## 6. Mock data cho phát triển song song

`packages/contracts/src/qshield_contracts/mocks/` sinh dữ liệu giả **đúng schema thật** cho mọi
artifact ở bảng §3. Dùng khi module phía trên trong pipeline chưa xong — cả 5 người có thể phát
triển song song từ ngày 1 mà không ai chờ ai:

```bash
uv run qshield-pipeline all --config configs/base.yaml --mock
```

Khi dữ liệu thật của một chặng sẵn sàng, chỉ đổi nguồn đầu vào của chặng đó — các chặng phía sau
không đổi code vì chúng chỉ phụ thuộc vào schema trong `contracts`, không phụ thuộc cách chặng trước
tạo ra dữ liệu.

Xem thêm `docs/architecture/pipeline.md` cho luồng chạy tổng thể.
