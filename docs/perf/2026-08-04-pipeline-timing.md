# Đo thời gian chạy pipeline — 2026-08-04

Đo trên nhánh `chore/pipeline-timing` (tách từ `feat/ai-regime-scenarios`, sau commit `0660ab7`).
Mục tiêu: trả lời "chạy full pipeline end-to-end mất bao lâu" bằng số đo thật, không ước lượng.

**Kết luận ngắn:** chưa chạy được end-to-end. 3 trong 6 chặng chưa hiện thực. Phần chạy được
(chặng 1–3) mất **~2 phút 50 giây** trên dữ liệu thật; trong đó **~75 giây là lãng phí thuần túy**
ở `qshield-data split` (xem §4).

## 1. Môi trường

| Hạng mục | Giá trị |
|---|---|
| Máy | Windows 11, shell Git Bash / PowerShell |
| Python | 3.14 (uv workspace, 1 venv chung) |
| Dữ liệu | 8 mã, returns 21.088 dòng × 2.641 phiên (2016-01-04 → 2026-07-30), market_features 2.762 dòng |
| Config | `configs/base.yaml` (config hoàn chỉnh DUY NHẤT — `configs/uat/*.yaml` còn là stub toàn `null`) |
| Cách đo | wall-clock quanh `subprocess.run`, chạy lại 2 lần mỗi lệnh, lấy **min** |

Mọi số dưới đây **đã bao gồm** chi phí khởi động: `uv run python -c pass` = **0,25 s**, còn
`uv run qshield-ai <cmd>` mất thêm ~2–3 s chỉ để import cây module. Với các chặng ngắn (scenarios),
phần khởi động chiếm phần lớn thời gian.

## 2. Kết quả

### Chặng chạy được

| Chặng | Lệnh | Thời gian | Ghi chú |
|---|---|---|---|
| 1. data | `qshield-data fetch` | **40,0 s** | mạng — biến động theo đường truyền, không tái lập được |
| 1. data | `qshield-data clean` | 5,7 s | |
| 1. data | `qshield-data features` | 4,9 s | |
| 1. data | `qshield-data eligibility` | 6,1 s | |
| 1. data | `qshield-data split` | **62,1 s** | ~99% là parse ngày thừa — xem §4 |
| 1. data | `qshield-data quality` | 3,9 s | |
| 1. data | `qshield-data manifest` | 5,4 s | |
| 1. data | `qshield-data build` (cả 7 bước trong 1 tiến trình) | **104,9 s** | gồm cả fetch |
| 2. regime | `qshield-ai regime` | **60,1 s** | 10 seed × lưới 8 ứng viên (n_states 2–5 × diag/full), n_iter=500 |
| 3. scenarios | `qshield-ai scenarios` | **3,5 s** | S=500, H=20, N=8, ×3 regime |

**Tổng chặng 1–3 trên dữ liệu thật: ~168 giây (2 phút 50 giây).**

### Trên dữ liệu giả (`--mock`)

| Lệnh | Thời gian |
|---|---|
| `qshield-ai regime --mock` | 26,7 s |
| `qshield-ai scenarios --mock` | 4,3 s |

### Chặng chưa hiện thực

| Chặng | Package | Trạng thái |
|---|---|---|
| 4. risk | `qshield_risk` | `raise NotImplementedError` (toàn package 34 dòng) |
| 5. qubo / 6. solve | `qshield_quantum` | `raise NotImplementedError` (toàn package 41 dòng) |
| orchestrator | `qshield_pipeline` | `raise NotImplementedError`; `stages.py` chỉ có 1 dòng comment |

Chưa đo được chi phí QAOA/exact solver. Đây là ẩn số lớn nhất còn lại: exact solver duyệt 256
bitstring (rẻ), nhưng `StatevectorSampler` + COBYLA 200 vòng lặp trên 8 qubit là phần chưa ai chạy.

## 3. Độ nhạy theo config

| Trục | Đo được |
|---|---|
| `num_scenarios` 500 → 5000 (mục tiêu CLAUDE.md) | 3,5 s → **4,5 s** — chỉ +1 giây |
| `artifacts.mode` dev → runs | 60,1 s → 66,2 s cho regime, **nhưng chặng scenarios sau đó FAIL** (§6) |
| dữ liệu thật → `--mock` | regime nhanh hơn 2,3× (840 dòng vs 2.571 dòng) |

Đáng chú ý: **S=500 bị khóa KHÔNG phải vì lý do thời gian chạy.** Chạy đủ 5000 kịch bản theo mục
tiêu trong CLAUDE.md chỉ đắt thêm ~1 giây. Nếu AD-14 đang chờ IN-PO-01 vì lo chi phí tính toán thì
lo đó không có cơ sở — đã đo, cube `(5000, 20, 8)` sinh và validate xong trong 4,5 giây.

## 4. `qshield-data split` — 62 giây, ~99% lãng phí

`split.apply_splits` gọi `.apply(assign_split)` theo từng dòng, và `assign_split`
(`packages/data/src/qshield_data/split.py:21`) parse lại **6 chuỗi ngày giống hệt nhau** bằng
`pd.to_datetime` ở **mỗi dòng**. Với 21.088 + 2.762 dòng ⇒ ~143.000 lần parse lặp lại cùng 6 giá trị.

Đo trực tiếp, so với bản hoisted (parse 6 mốc một lần rồi so sánh vector hóa):

| Khung | Số dòng | Hiện tại | Hoisted | Tăng tốc | Nhãn giống hệt? |
|---|---|---|---|---|---|
| returns (asset-level) | 21.088 | **68,21 s** | 0,0055 s | **12.487×** | có |
| market_features | 2.762 | 6,87 s | 0,0524 s | 131× | có |

Nhãn sinh ra **giống hệt nhau từng phần tử** — đây là tối ưu thuần túy, không đổi ngữ nghĩa.
Sửa xong, `qshield-data build` giảm từ ~105 s xuống **~30 s**, và tổng chặng 1–3 xuống
**~1 phút 35 giây**.

Chủ sở hữu: Nguyễn Đỗ Minh Anh (`packages/data`).

## 5. CLI stub sai tên lệnh so với tài liệu

CLAUDE.md hướng dẫn `uv run qshield-pipeline all --config configs/base.yaml`. Lệnh đó **không tồn tại**:

```
$ uv run qshield-pipeline all --config configs/base.yaml
Got unexpected extra argument(s) (all)          # exit 2
```

Nguyên nhân: typer khi app chỉ có **một** command sẽ đưa command đó lên thành root, nên `all` bị coi
là tham số thừa. Lệnh chạy được là `uv run qshield-pipeline` (không có subcommand) — và khi đó mới
tới được `NotImplementedError`. Cùng lỗi với `qshield-risk effects` và `qshield-quantum solve`.

Không phải lỗi nghiêm trọng (cả ba đều là stub), nhưng khi hiện thực xong mà vẫn giữ một command
thì mọi lệnh trong tài liệu và trong CLAUDE.md đều sai. Cách sửa: thêm `@app.callback()` rỗng để
typer giữ nguyên dạng subcommand.

## 6. `artifacts.mode: runs` không dùng được giữa các lệnh

CLAUDE.md/`docs/architecture/pipeline.md` §4 bắt buộc dùng `runs` từ ngày 4 sprint. Đo thật:

```
$ qshield-ai regime    --config <base với mode: runs>   → OK, ghi vào run_20260804_172933/
$ qshield-ai scenarios --config <base với mode: runs>   → exit 2: "Chưa có regime_daily.parquet"
```

`_resolve_run_id` (`packages/ai/src/qshield_ai/cli.py:117`) sinh
`run_{now:%Y%m%d_%H%M%S}` **mỗi lần gọi**. Hai lệnh chạy cách nhau vài giây ⇒ hai thư mục run khác
nhau ⇒ chặng sau không thấy artifact của chặng trước. Ở `dev` mode không lộ vì đường dẫn cố định.

Cần một `run_id` chung cho cả pipeline: hoặc orchestrator sinh rồi truyền xuống, hoặc thêm cờ
`--run-id`, hoặc "dùng lại run mới nhất nếu không chỉ định". Đây là quyết định của `contracts`
(Đỗ Ngọc Tân) vì `ArtifactPaths` sở hữu ngữ nghĩa `run_id`.

## 7. `--mock` ghi đè artifact thật, không có dấu vết — ĐÃ SỬA

Phát hiện trong lúc đo, **nghiêm trọng nhất trong báo cáo này**. Đã sửa trong commit tiếp theo
trên nhánh này; phần mô tả dưới đây giữ nguyên để ghi lại sự cố.

`--mock` và run thật ghi vào **cùng** `artifacts/dev/`, và **không** artifact nào ghi lại rằng đầu
vào là dữ liệu giả. Chuỗi thực tế đã xảy ra khi chạy battery đo:

1. `qshield-ai regime --mock` ghi đè `artifacts/dev/regime/regime_daily.parquet` bằng nhãn từ fixture.
2. `qshield-ai scenarios --config configs/base.yaml` (**không** `--mock`) đọc đúng file đó.
3. Kết quả: `gate_status: PASS`, cube `(5000, 20, 8)`, `t=2021-06-14`, `regime_source: hmm_champion`.
   **Không có exception nào.**

`regime_summary.json` lúc đó ghi `coverage.n_rows: 840`, `2018-03-27 → 2021-06-14` — dấu hiệu duy
nhất cho thấy đó là fixture, và phải biết trước con số thật (2.571 dòng, 2016-04-04 → 2026-07-30)
mới nhận ra. `run_mode` chỉ ghi `NON_BASELINE_RUN`, không phân biệt mock/thật.

Đây đúng loại lỗi "im lặng ra số sai" mà quy tắc 13 và cơ chế provenance sinh ra để chặn.

### Cách sửa đã áp dụng

1. `regime_summary.json` mang khóa mới `input_source: "mock" | "real"`. Tham số của
   `build_regime_summary` là **keyword bắt buộc, không có mặc định** — một mặc định `"real"` sẽ
   khiến đúng lỗi này quay lại ngay khi ai đó quên truyền.
2. `scenarios` đọc sidecar đó **trước** khi đọc bất kỳ dữ liệu nào và **từ chối** khi nguồn lệch
   với nguồn của chính nó, theo **cả hai chiều**. `--force` vẫn cho qua nhưng ghi cảnh báo.
3. Artifact không có khóa (do bản CLI cũ ghi) tính là `"unknown"` và **cũng bị từ chối** —
   fail-closed. Giả định lạc quan "không ghi gì nghĩa là dữ liệu thật" chính là thứ tạo ra sự cố.
4. `scenario_manifest.json` ghi **hai** trường tách nhau: `input_source` (của run scenarios) và
   `regime_input_source` (của nhãn regime đã tiêu thụ). Gộp một trường sẽ giấu mất đúng trường
   hợp `--force` cần điều tra.

5 test mới. Đã chứng minh test thật sự phân biệt được: tắt guard ⇒ 3/3 test guard đỏ.

**Ảnh hưởng tới cả nhóm:** mọi `artifacts/dev/regime/` sinh trước thay đổi này đều thiếu dấu vết
nên sẽ bị chặn ở lần chạy `scenarios` kế tiếp. Cách khắc phục nằm ngay trong thông báo lỗi: chạy
lại `qshield-ai regime`.

## 8. Toàn bộ `qshield-data` crash khi stdout không phải UTF-8

Mọi bước của `qshield-data` (trừ `split`) và `--help` của **cả hai** CLI đều thoát **exit 1** với
`UnicodeEncodeError: 'charmap' codec can't encode character '✓'` khi stdout là pipe/redirect
(cp1252) — tức mọi lần chạy trong CI, trong script, hoặc `| tee`. Công việc **đã làm xong**, chỉ
crash ở dòng `typer.echo("✓ ...")` cuối cùng, nên artifact vẫn đúng nhưng exit code báo lỗi — một
orchestrator kiểm tra exit code sẽ dừng pipeline dù không có gì sai.

`packages/ai` đã có sẵn cách xử lý (`_tolerate_legacy_console_encoding`,
`packages/ai/src/qshield_ai/cli.py:70`) nhưng đặt trong `@app.callback()`, mà Click in `--help` rồi
thoát **trước khi** callback chạy ⇒ `--help` vẫn crash. `packages/data` không có cách xử lý nào.

Cách chạy tạm: `PYTHONIOENCODING=utf-8 uv run qshield-data build --config configs/base.yaml`
(đã xác minh: toàn bộ 7 bước exit 0).

## 9. Tái lập

```bash
PYTHONIOENCODING=utf-8 uv run qshield-data build --config configs/base.yaml
PYTHONIOENCODING=utf-8 uv run qshield-ai regime --config configs/base.yaml
PYTHONIOENCODING=utf-8 uv run qshield-ai scenarios --config configs/base.yaml
```

Chạy đo lại không làm bẩn repo: đã khôi phục `data/` bằng `git checkout -- data/` sau khi đo, và
xóa hai config probe tạm (`configs/_timing_runs.yaml`, `configs/_timing_s5000.yaml`). `fetch` để lại
9 file `data/raw/**/20260804_*.csv` chưa track — dữ liệu tải mới hôm nay, chưa dùng vào đâu.
