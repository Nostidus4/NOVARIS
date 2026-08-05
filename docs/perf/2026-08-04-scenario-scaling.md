# Độ nhạy thời gian chạy chặng scenarios theo (S, N) — 2026-08-04

Doc đồng hành với [`2026-08-04-pipeline-timing.md`](2026-08-04-pipeline-timing.md). Doc kia trả lời
"chạy end-to-end mất bao lâu" ở đúng một điểm cấu hình (`S=500, H=20, N=8, ×3 regime`). Doc này trả
lời câu tiếp theo: **con số đó đổi thế nào khi tăng số kịch bản S và số mã N.**

**Kết luận ngắn:** trên universe đã khóa (N=8), chạy đủ 5000 kịch bản theo mục tiêu CLAUDE.md tốn
**+1,6 giây** so với S=500. Thời gian chạy không phải lý do để giữ S=500. Ràng buộc thật khi lên
S=5000 là **kích thước artifact**, không phải wall-clock. Còn N=30 thì chặng scenarios gần như không
hề hấn — nhưng nó **phá vỡ chặng 5/6** (xem §6).

## 1. Môi trường và cách đo

Cùng máy, cùng dữ liệu với doc gốc (Windows 11, Python 3.14, uv workspace; returns 21.088 dòng ×
2.641 phiên; regime artifact thật, `input_source: real`, 2.571 dòng).

| Hạng mục | Cách làm |
|---|---|
| Wall-clock CLI | `subprocess.run` quanh `uv run qshield-ai scenarios`, chạy 2 lần, lấy **min** |
| Cấu hình probe | file `configs/_probe_*.yaml` tạm (base.yaml + override `num_scenarios`), **đã xóa sau khi đo** |
| Cờ | `--force` bắt buộc — xem §2 |
| Benchmark trong tiến trình | gọi thẳng hàm thư viện, tách từng bước, bỏ chi phí import |

Ba trục đo tách nhau vì mỗi trục trả lời một câu khác nhau:

1. **CLI trên dữ liệu thật, N=8** — số dùng được ngay, so trực tiếp với doc gốc.
2. **CLI trên `--mock`, N=8 và N=30** — cách duy nhất chạy được N=30 qua CLI (xem §3).
3. **Benchmark trong tiến trình trên panel thật** — phép đo *có kiểm soát* cho trục N.

## 2. Phải dùng `--force`, và điều đó nói lên một chuyện

Cổng kiểm định kịch bản trên dữ liệu thật hiện **FAIL**. Không có `--force` thì cube không được ghi
(đúng theo thiết kế: `cli.py` dọn artifact cũ rồi thoát). Đo mà không có `--force` sẽ **bỏ sót**
`np.savez_compressed` — mà đó chính là phần đắt nhất và là phần scale theo cả S lẫn N. Mọi số CLI
dưới đây đều chạy với `--force`, nên bao gồm toàn bộ đường ghi.

Hệ quả cho người đọc số: các run này là `NON_BASELINE_RUN` có chủ ý, dùng để đo thời gian, **không**
phải bằng chứng kịch bản đạt kiểm định.

## 3. N=30 không chạy được trên dữ liệu thật

`data/processed/returns.parquet` chỉ có 8 mã. `build_return_panel`
(`packages/ai/src/qshield_ai/scenarios/bootstrap.py:61`) raise ngay khi thiếu ticker — đúng như
thiết kế. Muốn có số N=30 thật phải fetch thêm 22 mã và dựng lại toàn bộ chặng data; việc đó **không
làm trong lần đo này** vì nó ghi đè `data/processed/` và phụ thuộc mạng.

Thay vào đó, N=30 được đo hai cách, và **cả hai đều có nhược điểm phải nói rõ**:

- **CLI `--mock` với universe 30 mã** — chạy hết đường thật (IO, validate, ghi npz) nhưng trên dữ
  liệu fixture 840 dòng, và nhãn regime khác (xem §5).
- **Benchmark trong tiến trình trên panel thật nới rộng** — 8 cột thật + 22 cột sinh từ chính chúng
  (có jitter), **giữ nguyên lịch phiên và mask `complete`**, nên block pool và số cửa sổ tham chiếu
  giống hệt trường hợp N=8 (1.068 cửa sổ mỗi regime). Chỉ bề rộng N đổi. Đây là phép đo sạch nhất
  cho trục N, nhưng **không phải dữ liệu thật 30 mã** — nó trả lời "rộng thêm 22 cột tốn bao nhiêu",
  không trả lời "30 mã VN30 thật hành xử ra sao".

## 4. Kết quả

### 4.1 Wall-clock CLI (min của 2 lần)

| S | N=8, dữ liệu thật | N=8, `--mock` | N=30, `--mock` |
|---|---|---|---|
| 500 | **3,57 s** | 3,64 s | 4,86 s |
| 2000 | **4,04 s** | 3,78 s | 6,74 s |
| 5000 | **5,21 s** | 4,67 s | 14,35 s |

S=500 (3,57 s) khớp với doc gốc (3,5 s) — hai lần đo độc lập cho cùng một con số.

### 4.2 Benchmark trong tiến trình, panel thật (giây)

Bỏ chi phí import. 3 regime, 1.068 cửa sổ tham chiếu mỗi regime ở **mọi** dòng — pool không đổi.

| N | S | pool | generate | reference | validate | ghi npz | **tổng compute** | npz | cube RAM |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 500 | 0,018 | 0,003 | 0,008 | 0,063 | 0,062 | **0,15** | 1,8 MB | 3,7 MB |
| 8 | 1000 | 0,018 | 0,005 | 0,008 | 0,080 | 0,126 | **0,24** | 3,5 MB | 7,3 MB |
| 8 | 2000 | 0,018 | 0,010 | 0,008 | 0,127 | 0,242 | **0,40** | 7,0 MB | 14,6 MB |
| 8 | 5000 | 0,021 | 0,025 | 0,008 | 0,309 | 0,597 | **0,96** | 17,5 MB | 36,6 MB |
| 30 | 500 | 0,018 | 0,007 | 0,010 | 0,287 | 0,355 | **0,68** | 11,7 MB | 13,7 MB |
| 30 | 1000 | 0,019 | 0,013 | 0,009 | 0,404 | 0,734 | **1,18** | 23,5 MB | 27,5 MB |
| 30 | 2000 | 0,019 | 0,026 | 0,010 | 0,694 | 1,453 | **2,20** | 47,0 MB | 54,9 MB |
| 30 | 5000 | 0,019 | 0,069 | 0,010 | 2,060 | 3,545 | **5,71** | 117,5 MB | 137,3 MB |

Ba điều đọc được ngay:

1. **Bootstrap gần như miễn phí.** `generate_cube` — tức toàn bộ phần thuật toán của chặng này —
   tốn **69 ms** ở cấu hình nặng nhất đo được. Tối ưu bootstrap là tối ưu nhầm chỗ.
2. **Chi phí nằm ở ghi npz (62%) và validate (36%).** `np.savez_compressed` là khoản lớn nhất;
   `build_validation_report` đứng thứ hai (pandas `skew`/`kurt` trên mảng phẳng 3 triệu phần tử,
   cộng `np.corrcoef` O(N²)).
3. **Chi phí cố định lấn át ở cấu hình nhỏ.** 3,57 s CLI − 0,15 s compute ⇒ **~3,4 s là khởi động
   interpreter + import**. Ở S=500/N=8, **96% thời gian chặng này không phải là tính toán.**

Kiểm chứng chéo: dự đoán S=2000/N=8 = 3,4 + 0,40 = 3,8 s, đo được 4,04 s. Dự đoán S=5000/N=8 =
3,4 + 0,96 = 4,4 s, đo được 5,21 s. Phần dư giải thích ở §5.

## 5. Vì sao mock N=30 mất 14,4 s chứ không phải ~9 s

Chênh lệch giữa benchmark và CLI đã được truy, không suy đoán. Hai nguyên nhân, **không** cái nào là
scale theo số kịch bản:

1. **CLI ghi HAI file npz, benchmark chỉ đo một.** Ở S=5000/N=30 nó sinh
   `stress_scenarios.npz` (37,7 MB) **và** `scenarios_by_regime.npz` (54,0 MB) — 91,7 MB nén mỗi
   run. Vì nén đã là khoản chi lớn nhất, nhân đôi số byte ghi là nhân đôi số hạng lớn nhất.
2. **Hình học của mock khác.** Regime `--mock` với 30 mã **FAIL cổng** (đồng thuận nhãn 0,5411 <
   ngưỡng 0,6), nên scenarios chạy trên nhãn fallback rule-based: 704 block hợp lệ, tỷ lệ tái sử
   dụng 96,5%, giữ cả 3 regime — khác hẳn phân bố của panel thật.

Sinh dữ liệu fixture **không** phải nguyên nhân: `synthetic_dataset` cho 30 mã × 900 ngày mất 0,06 s.

Vì vậy ước lượng trung thực cho 30 mã **thật** là **~10–11 giây**, không phải 14,4. Và nó vẫn chỉ là
ước lượng cho tới khi có người fetch đủ 22 mã.

## 6. Ràng buộc thật không phải wall-clock

### 6.1 S=5000 — vấn đề là kích thước artifact

| Cấu hình | `stress_scenarios.npz` | `scenarios_by_regime.npz` | Tổng mỗi run |
|---|---|---|---|
| S=500, N=8 (thật) | 2,4 MB | 7,0 MB | **9,4 MB** |
| S=5000, N=8 (thật) | 6,0 MB | 17,5 MB | **23,5 MB** |
| S=5000, N=30 (mock) | 37,7 MB | 54,0 MB | **91,7 MB** |

`artifacts.mode: runs` là **bắt buộc từ ngày 4 sprint** (CLAUDE.md, `docs/architecture/pipeline.md`
§4), tức mỗi run_id giữ một bản riêng. Ở N=8/S=5000 là 23,5 MB mỗi run và tích lũy — chấp nhận
được. Ở N=30/S=5000 là 91,7 MB mỗi run, và đó mới là thứ chạm trần trước wall-clock.

Nếu cần đánh đổi: `savez` không nén sẽ cắt phần lớn thời gian (3,5 s trong 5,7 s ở cấu hình nặng
nhất) nhưng đổi lấy file to hơn. Đây là **quyết định có chủ ý của người sở hữu ngân sách artifact**,
không phải chỗ để đổi mặc định trong im lặng.

### 6.2 N=30 — chặng 5/6 gãy, không phải chặng 3

Chi phí một lần chấm CVaR (đo thật; cận dưới, chưa gồm chi phí giao dịch và ma trận `C`) chiếu lên
hai solver:

| | N=8, S=5000 | N=30, S=500 | N=30, S=5000 |
|---|---|---|---|
| Một lần chấm CVaR | 3,38 ms | 0,85 ms | 9,45 ms |
| Exact solver, duyệt **toàn bộ** 2^N bitstring (quy tắc 16) | 256 → **0,9 s** | 1,07e9 → **~10,6 ngày** | 1,07e9 → **~117 ngày** |
| Chỉ duyệt tập khả thi C(N,3) | 56 → 0,2 s | 4.060 → 3,5 s | 4.060 → **38 s** |
| Bộ nhớ `StatevectorSampler`, 1 statevector | 4 KB | 16 GiB | **16 GiB** |

Hai hệ quả nếu N=30 từng được cân nhắc nghiêm túc:

1. **Quy tắc 16 phải đổi phát biểu**, từ "duyệt 256 bitstring" thành "duyệt tập con khả thi K phần
   tử". Bản khả thi rẻ (38 s) và vẫn là ground truth hợp lệ. Đây là đổi **cách phát biểu bài toán**,
   không phải đổi quy mô.
2. **QAOA qua `StatevectorSampler` là bất khả thi ở 30 qubit** trên máy này — 2^30 biên độ
   complex128 = 16 GiB cho một statevector, không phụ thuộc S. Đây là bức tường, và nó tới **rất
   lâu trước khi** bất cứ thứ gì trong `packages/ai` trở nên chậm.

Ở N=8 đã khóa, S=5000 miễn phí ở mọi chặng: exact solver duyệt hết 256 bitstring trong dưới 1 giây.

### 6.3 Regime cũng không trung tính với N

`--mock`, một mẫu: N=8 → 21,9 s, N=30 → 27,3 s. Feature `mean_pairwise_corr_60d` là O(N²) nên tăng
theo N, nhưng mức tăng vừa phải. Tín hiệu đáng chú ý hơn là **cổng HMM FAIL ở N=30** (đồng thuận
0,5411 < 0,6): đổi N là **đổi chính feature** mà HMM học, không chỉ đổi chi phí. Cảnh báo: mock, 840
dòng, một mẫu — đây là tín hiệu cần điều tra, không phải kết luận.

## 7. Tái lập

Benchmark dùng config probe tạm sinh từ `configs/base.yaml` (override `num_scenarios`, và với N=30
thì thêm một file include universe 30 mã). Cả hai đã xóa sau khi đo — repo không còn dấu vết.

```bash
# N=8, dữ liệu thật: đổi num_scenarios trong configs/scenarios.yaml rồi
PYTHONIOENCODING=utf-8 uv run qshield-ai scenarios --force --config configs/base.yaml
```

`PYTHONIOENCODING=utf-8` vẫn bắt buộc khi stdout là pipe (doc gốc §8 — chưa sửa).

`--force` sẽ đánh dấu run là NON_BASELINE. Dùng để đo thời gian thì được; **đừng** lấy artifact từ
những run này làm đầu vào cho Risk.

## 8. Việc cần làm cho ai

| Việc | Chủ sở hữu |
|---|---|
| Quyết định S cuối cùng — thời gian chạy **không còn là lý do** giữ S=500 | Nguyễn Thị Ánh Ngọc (duyệt config) |
| Ngân sách artifact khi bật `artifacts.mode: runs` ở S=5000 (23,5 MB/run) | Đỗ Ngọc Tân (`contracts`, `ArtifactPaths`) |
| Nén hay không nén npz — đánh đổi thời gian/dung lượng | Đỗ Ngọc Tân |
| Quy tắc 16: phát biểu lại theo tập khả thi nếu N từng vượt 8 | Đỗ Ngọc Tân (`quantum`) |
| Cổng HMM FAIL khi universe rộng ra — điều tra khi có dữ liệu thật >8 mã | Nguyễn Anh Tú (`ai`) |
