# Câu hỏi cần Ngọc và Phúc quyết định

**Soạn:** rà soát kỹ thuật 2026-09-04 · **Nhánh:** `staging-tan-dev` · **Trạng thái:** chờ trả lời
**Bằng chứng đầy đủ:** `reponse.md` — đọc **Phụ lục J** trước (sổ tổng hợp), chi tiết ở D–I
**Báo cáo trực quan:** https://claude.ai/code/artifact/3ac4ae67-5004-4f9b-bc71-65a013cd58e6

---

## Trước khi đọc: ba điều về tài liệu này

**1. Mọi con số dưới đây đo được trên code và artifact thật**, có lệnh tái tạo ở `reponse.md`
Phụ lục C. Không có số nào là ước lượng hay ngoại suy trừ khi ghi rõ.

**2. Không mục nào đã bị tự ý thay đổi.** Theo `plan.md` A5 — *"Gói nháp không kích hoạt
runtime"* — toàn bộ tham số tài chính (`target_cash_increment`, trọng số hàm mục tiêu, chi phí
giao dịch, ngưỡng cổng) giữ nguyên. Đợt sửa chỉ chạm code và ba khoá cấu hình kỹ thuật.

**3. Bảy kết luận trong bản rà soát đầu đã phải đính chính** bằng số đo mới — bảng đầy đủ ở
`reponse.md` J.5. Tài liệu này dùng con số **sau đính chính**.

**Trạng thái chốt:** 476 test pass + 8 chậm, 0 fail · `ruff` sạch · 0 commit, 0 push.

---

## Đường tới hạn

```
A1 (danh mục mẫu) ──> A2 (ngưỡng cổng chặn) ──> A3 (mô hình xấp xỉ có đủ không)
                                                          │
B1 (ký plan) ──> B2 (governance) ──> B5 (chạy lại bench) ──┼──> E4: quantum có đóng góp gì
                                                          │
B4 (ngân sách QAOA) ──────────────────────────────────────┘
```

**A1 → A3 là đường tới hạn.** Chưa chốt hai mục này thì mọi thí nghiệm quantum đều đo trên nền
không vững — nên thí nghiệm E4 đã được **hoãn có chủ đích**, không phải chưa kịp làm.

---

# Phần A — Câu hỏi cho Phúc (Risk)

## A1. Danh mục mẫu `sample_portfolio_weights` có được đổi không?

> **Ưu tiên cao nhất.** Đây là nguyên nhân gốc của cả hai lỗi P0 mà bản rà soát đầu quy nhầm
> cho tham số tài chính.

### Hiện trạng

`configs/base.yaml:337-368` khai danh mục mẫu là **equal-weight 1/30 cho cả 30 mã VN30**, cash 0.

### Cơ chế đã xác minh

```
10 candidate × 3,3333% × 30% = 0,10000  ←  đúng bằng target_cash_increment: 0.1
```

Vì trần tiền mặt đúng bằng mục tiêu, **chỉ tồn tại một** nghiệm đưa `cash_budget_deviation` về 0:
bán hết mức mọi mã. Đồng thời 30 mã trọng số giống hệt làm lợi ích biên dàn đều, khiến top-10
chỉ giữ được 59,9% tổng lợi ích.

### Bằng chứng — giữ nguyên toàn bộ tham số, chỉ đổi hình dạng danh mục

| Danh mục | Trần cash | corr(objective, tổng bán) | Nghiệm tối ưu | coverage@10 |
|---|---|---|---|---|
| **equal-weight (hiện tại)** | 0,1000 | **−0,9817** | bán hết mức mọi mã | **0,599** ❌ |
| zipf 1/rank | 0,2152 | −0,4526 | nội tại | 0,846 ✅ |
| concentrated top5=60% | 0,2040 | −0,4582 | nội tại | 0,839 ✅ |
| realistic 12 holdings | 0,2700 | −0,7253 | `[30,30,30,10,0…]%` | 0,971 ✅ |

Tương quan −0,98 nghĩa là hàm mục tiêu gần như **tuyến tính đơn điệu** theo tổng lượng bán —
không có cấu trúc tổ hợp để giải. Degeneracy biến mất ở **cả ba** dạng lệch, và coverage@10
vượt ngưỡng 0,70 ở cả ba.

### Bổ sung từ phép duyệt đủ

Duyệt đủ 1.048.576 tổ hợp trên danh mục thực tế cho thấy **"bán 30% mọi mã" là phương án TỆ
NHẤT tuyệt đối** (hạng 1.048.576/1.048.576). Việc equal-weight biến nó thành nghiệm tối ưu vì
thế nghiêm trọng hơn bản rà soát đầu mô tả.

### Câu hỏi

1. Có đồng ý rằng equal-weight 1/30 **không đại diện** cho persona ở `plan.md` A1
   (*"nhà đầu tư cá nhân có danh mục cổ phiếu hiện hữu"*)?
2. Evidence run nên dùng danh mục nào trong lúc chờ danh mục thật có consent (`plan.md` G2)?
3. Có đồng ý **giữ equal-weight làm fixture hồi quy** không? Nó bộc lộ đúng trường hợp biên và
   nên được test — chỉ là không nên làm evidence.

### Lưu ý về giới hạn

Ba dạng danh mục lệch ở bảng trên là **do reviewer dựng**, không phải danh mục nhà đầu tư thật.
`plan.md` §7 ghi rõ *"chưa có investor portfolio thật"*. Kết luận ở đây là **định hướng về cơ
chế**, chưa phải con số cuối. Nên lặp trên ≥5 dạng trước khi chốt.

---

## A2. Ngưỡng cổng chặn mô hình xấp xỉ — giữ hay nới?

### Hiện trạng

`configs/workflow_update.yaml:618-629` khai `surrogate_validation.thresholds` với trạng thái
`PROVISIONAL_PENDING_OWNER`:

```yaml
mae_max: 0.02
rmse_max: 0.03
spearman_min: 0.7
top_k: 20
top_k_recall_min: 0.6
```

Cổng chặn **nay đã được triển khai** — trước đây khoá config này không có dòng code nào đọc, dù
`gates.surrogate_validation_required_before_solver: true`.

### Kết quả chạy thật

| Danh mục | MAE holdout | Spearman | top-20 recall | Verdict |
|---|---|---|---|---|
| equal-weight | 0,00017 | 1,0000 | 1,000 | **PASS** |
| realistic 12 holdings | 0,03086 | 0,8887 | **0,250** | **FAIL** (6 vi phạm) |

### Phát hiện mới: ước lượng từ holdout đang LẠC QUAN

Phép duyệt đủ 1.048.576 tổ hợp cho phép đo **chính xác** thay vì ước lượng từ 1.000 mẫu:

| Chỉ số | **Toàn không gian** | Holdout 1.000 (cổng chặn dùng) | Holdout lệch |
|---|---|---|---|
| **top-20 recall** | **0,000** | 0,250 | **lạc quan** |
| **top-100 recall** | **0,000** | — | — |
| top-1000 recall | 0,011 | — | — |
| Spearman ρ | 0,8334 | 0,8887 | lạc quan |
| MAE | 0,03400 | 0,03086 | lạc quan |
| RMSE | 0,04235 | 0,03900 | lạc quan |

**Mọi chỉ số đều tốt hơn sự thật.** Cổng chặn vẫn bắt được FAIL — nhưng nó đang bảo vệ **yếu
hơn** con số trên phiếu kiểm định gợi ý.

### Khuyến nghị của reviewer

**`spearman_min` là tiêu chí SAI cho mục đích này.** ρ = 0,8334 nghe "khá tốt" và **vượt ngưỡng
0,70 hiện tại** — nhưng tối ưu hoá chỉ quan tâm phần **đuôi trên**, và ở đó tỷ lệ giữ được bằng
**0,000**. Một mô hình xấp xỉ có thể đạt Spearman cao trên toàn không gian trong khi hoàn toàn
vô dụng để tìm nghiệm tốt.

Đề xuất: chuyển `spearman_min` xuống vai trò báo cáo, lấy **`top_k_recall` làm tiêu chí quyết
định chính**, và tính nó trên tập mẫu lớn hơn nhiều — hoặc trên toàn không gian khi khả thi
(ở N=10 mất 33 phút với 8 tiến trình).

### Câu hỏi

1. Ngưỡng hiện tại có đúng ý Phúc không, hay là số tạm cần chốt lại?
2. `top-100 recall = 0,000` — mô hình xấp xỉ **không giữ được một nghiệm nào** trong 100 nghiệm
   tốt nhất. Vì bước rerank chỉ chọn trong pool solver trả về, đây có phải mức không chấp nhận
   được không?
3. Có đồng ý đổi tiêu chí quyết định từ Spearman sang `top_k_recall` không?
4. Nếu nới ngưỡng để PASS, xin xác nhận rõ ràng rằng chấp nhận khoảng cách ở A3.

---

## A3. Mô hình xấp xỉ bậc 2 có đủ không?

> **Ảnh hưởng trực tiếp tới số phận nhánh quantum.** Câu này nay có câu trả lời định lượng.

### Bằng chứng — duyệt đủ 1.048.576 tổ hợp trên hàm mục tiêu tài chính thật

2.004 giây, 8 tiến trình, dùng chính hàm `financial_objective_from_growth` canonical — không viết
lại công thức. Danh mục `realistic 12 holdings`.

| Phương án | true objective | lệch optimum | hạng /1.048.576 | lợi ích thu được |
|---|---|---|---|---|
| **Optimum thật** `[30,0,30,30,0,20,20,0,0,0]%` | **0,821059** | — | **1** | 100% |
| coordinate descent trực tiếp (7,3s) | 0,835184 | **1,72%** | **525** | **97,0%** |
| **exact 2²⁰ trên mô hình xấp xỉ — toàn bộ pipeline QUBO** (≈21s) | **0,938997** | **14,36%** | **307.751** | **75,0%** |
| no-action | 1,293691 | 57,56% | 1.048.359 | 0% |
| all-ones | 1,357435 | 65,33% | 1.048.576 (tệ nhất) | — |

**Phương án mà toàn bộ chuỗi QUBO chọn ra xếp hạng 307.751 — tệ hơn 70% số phương án có thể có.**

### Điểm mấu chốt

Trần chất lượng bị đặt bởi **mô hình xấp xỉ**, không phải solver. Exact đã tìm **đúng** cực tiểu
của mô hình đó — đó là điều tốt nhất bất kỳ solver nào có thể làm trên mô hình ấy. Vì vậy:

> **Cải thiện solver — kể cả thay exact bằng QAOA hoàn hảo — KHÔNG THỂ vá được khoảng cách này.**

QAOA đang cạnh tranh để giải tối ưu một mô hình vốn đã lệch 14,36%.

### Tiền đề của mô hình xấp xỉ không còn đứng vững

Lý do tồn tại của nó là *"hàm mục tiêu thật quá đắt để tối ưu trực tiếp"*.
Đo thật: **7,2 mili-giây một lần đánh giá**. Ở quy mô N=10, tiền đề đó sai.

### Ba hướng, nay đánh giá được

| | Hướng | Đánh giá sau khi có số |
|---|---|---|
| **(a)** | Tăng số mẫu (`plan.md` D8: *"sample count scale theo số hệ số"*) | **Không giải quyết được.** Vấn đề là lớp mô hình, không phải số mẫu: bậc 2 không biểu diễn nổi hàm CVaR ở vùng nhiều hành động |
| **(b)** | Đổi lớp mô hình (bậc cao hơn / số hạng ba biến) | Có thể, **nhưng phá dạng QUBO thuần** ⇒ ảnh hưởng trực tiếp khả năng chạy quantum |
| **(c)** | Ở N=10 dùng classical trực tiếp trên true objective; giữ QUBO/QAOA làm nhánh nghiên cứu có nhãn rõ cho quy mô lớn hơn | Thu được **97,0%** lợi ích trong **7,3s**, so với **75,0%** trong 21s của đường QUBO |

### Câu hỏi

1. Chọn hướng nào — (a), (b), hay (c)?
2. Nếu chọn (b): chấp nhận rằng dạng bài toán không còn là QUBO thuần, và nhánh quantum phải
   được định vị lại?
3. Nếu chọn (c): giữ nhánh QUBO/QAOA ở vai trò nào, và với nhãn gì?

### Giới hạn của bằng chứng này

- **Một danh mục tổng hợp**, do reviewer dựng. Cần lặp trên ≥5 danh mục, gồm danh mục thật có
  consent, trước khi coi là kết luận chung.
- Coordinate descent trên true objective (hạng 525) cũng **không tối ưu** — lệch 1,72%. Nếu chọn
  hướng (c) thì vẫn cần thuật toán tốt hơn, hoặc chấp nhận 1,72%.
- Kết quả này **không** nói QAOA tệ. Nó nói mọi solver trên đường QUBO đều bị chặn trên bởi cùng
  một mô hình xấp xỉ.

---

## A4. Hàm mục tiêu: tổng có trọng số hay theo thứ tự ưu tiên?

### Hiện trạng — code đang làm KHÁC kế hoạch

`plan.md` D5 đề xuất hàm mục tiêu **lexicographic** (theo thứ tự ưu tiên). Code thực tế
(`packages/risk/src/qshield_risk/objective.py:240-251`) dùng **tổng có trọng số thuần**.

Khoá `financial_objective.priority: cvar_first` tồn tại trong cấu hình nhưng **không có dòng code
nào đọc nó** — bất kỳ ai đọc cấu hình đều tưởng tính năng đã có.

### Câu hỏi

1. Giữ tổng có trọng số, và **xoá khoá `priority`** để khỏi gây hiểu nhầm? Hay implement
   lexicographic thật?
2. Nếu giữ tổng có trọng số: `plan.md` D5 yêu cầu *"Weights/scales của QUBO phải fit trên
   validation"*. Hiện **chưa có bằng chứng fit nào**. Phúc cung cấp được không?

### Ghi chú kỹ thuật

Biên độ đóng góp đo trên 711 mẫu train (danh mục equal-weight):

| Thành phần | Biên độ |
|---|---|
| `cash_budget_deviation` | **0,30257** |
| `cvar` | 0,11157 |
| `turnover` | 0,02167 |
| `transaction_cost` | 0,00542 |
| `return_sacrifice` | 0,00297 |
| `liquidity_penalty` | 0,00108 |

Bốn thành phần cuối gộp lại vẫn nhỏ hơn 1/3 biên độ CVaR. Với trọng số/thang đo hiện tại, chúng
gần như không có tiếng nói trong nghiệm.

---

## A5. Khi nào có `risk_policy` thật?

### Hiện trạng

`configs/workflow_update.yaml:503` để `risk_policy_artifact: null`. Hệ quả dây chuyền:

| Ảnh hưởng | Chi tiết |
|---|---|
| `RiskPolicy.from_config` trả `None` | Không có dải tiền mặt, không hạn mức CVaR, không danh sách cấm bán, không hạn mức từng mã |
| Cổng rerank không kiểm được gì | Nay báo `NOT_EVALUATED` thay vì `PASS` giả (đã sửa) |
| `quantum_constraints` rỗng | **Bài toán tối ưu không có ràng buộc nào** |
| CR-WF2-002 không thực thi được | Kế hoạch bảo bỏ mục tiêu tiền mặt cứng 10%, nhưng thiếu chính sách nên hệ thống rơi về mục tiêu cứng — **đây chính là cơ chế tạo ra hiện tượng ở A1** |

### Câu hỏi

Khi nào có `risk_policy` thật? Đây là chặn cứng cho việc nói *"hệ thống tôn trọng ràng buộc danh
mục"* — hiện tại câu đó **không đúng**.

---

# Phần B — Câu hỏi cho Ngọc (Product / Governance)

## B1. `plan.md` có được ký không?

Toàn bộ `plan.md` mang `DRAFT_PENDING_NGOC_REVIEW` — dòng 5 ghi *"không phải biên bản đã ký"*,
dòng 35 ghi mọi mục là *"đề xuất chốt"* cần bằng chứng trước khi phê duyệt hiệu lực.

**Hệ quả thực tế:** code và tài liệu đang tham chiếu tới "quyết định D5 / E3 / CR-002" như thể
chúng đã hiệu lực. Nếu Ngọc sửa hoặc bác một mục, phần code tham chiếu tới nó phải sửa theo.

**Câu hỏi:** Ngọc ký, sửa, hay bác?

---

## B2. Ba tệp quản trị chưa tồn tại

`plan.md` yêu cầu tạo, hiện **không có tệp nào**:

| Quyết định | Tệp | Nội dung |
|---|---|---|
| A3 | `configs/policies/risk_appetite.yaml` | Khẩu vị rủi ro và biên chính sách |
| A4 | `configs/policies/claim_policy.yaml` | Claim nào được phép, claim nào cấm |
| A5 | `decision_registry.yaml` | ID / phiên bản / chủ sở hữu / bằng chứng / người duyệt / ngày hiệu lực |

**A4 là gấp nhất.** Hiện không có gì ngăn một người soạn slide dùng câu đã bị cấm. Mục "Claim
được phép / không được phép" trong artifact có thể dùng làm nội dung khởi đầu.

**Câu hỏi:** Ngọc soạn, hay muốn Tân dựng khung rồi Ngọc điền?

---

## B3. Hai cách diễn đạt trên giao diện cần Ngọc duyệt lại

Đã sửa trong đợt này, nhưng là quyết định sản phẩm:

| Chỗ | Trước | Sau |
|---|---|---|
| `frontend/components/landing/Hero.tsx` | "Phòng vệ bằng lượng tử." | "Phòng vệ danh mục — mô hình hoá bằng QUBO." |
| `frontend/app/landing/page.tsx` metadata | "…bằng lượng tử" | "…bằng QUBO" |

**Lý do sửa:** QAOA **không chạy trên đường sản phẩm** — 100% artifact 20-bit mang
`actual_solver: "exact"`, `qaoa_seed_count: 0`.

**Câu hỏi:** Ngọc đồng ý cách diễn đạt mới, hay muốn câu khác?

---

## B4. Cấu hình QAOA baseline vượt ngân sách 6 lần

### Số đo (đây chính là dry-run mà `plan.md` E3 yêu cầu)

| maxiter | runtime |
|---|---|
| 10 | 175,0 s |
| 30 | 533,9 s |

Quan hệ tuyến tính sạch: **17,9 giây mỗi vòng lặp COBYLA** ở 20 qubit, chi phí cố định ≈ 0.

Ngoại suy sang cấu hình baseline đang khai (`optimizer_maxiter: 200`, `min_seeds: 10`):

| Hạng mục | Cần | Ngân sách config | Vượt |
|---|---|---|---|
| 1 seed | ~3.590 s (60 phút) | `qaoa_seed_timeout_seconds: 600` | **6,0×** |
| 10 seed | ~35.890 s (10,0 giờ) | `qaoa_total_timeout_seconds: 7200` | **5,0×** |
| maxiter vừa ngân sách 600s | **33** | khai 200 | — |

`plan.md` E3 ghi rõ các số ngân sách này là *"Draft… cần dry-run, không cam kết SLA"*.

### Ba phương án

| | Phương án | Đánh đổi |
|---|---|---|
| **(a)** | Giữ chế độ dev (1 seed / 128 shots / maxiter 10) | Chạy 183 s, nhưng 1 seed **vi phạm** quy tắc "tối thiểu 10 seed, không cherry-pick" (CLAUDE.md 18) |
| **(b)** | Hạ `optimizer_maxiter` 200 → ~30 | 10 seed ≈ 89 phút, vừa ngân sách. **Chưa đo** maxiter=30 có đủ để COBYLA hội tụ ở 20 tham số |
| **(c)** | Nâng ngân sách lên ~10 giờ mỗi lần chạy baseline | Mỗi evidence run mất một ngày làm việc |

**Đề xuất: (b), nhưng phải chạy thí nghiệm hội tụ trước khi chốt.** Thí nghiệm đó chưa chạy —
reviewer làm được trong 1–2 giờ nếu Ngọc muốn.

---

## B5. Chữ ký trên run hash trước đây không có ý nghĩa

`plan.md` G3: *"Ngọc ký final trên run/config hash cụ thể."*

### Vấn đề đã phát hiện và sửa

Trước đợt này, **kết quả QAOA không tái lập được dù cùng seed**. Ba lần chạy cùng `seed=101`,
cùng bài toán, cùng tiến trình:

```
lần 1: 00111011  energy = −0.15286668
lần 2: 00111111  energy = −0.18319979
lần 3: 00111111  energy = −0.18319979
```

Nguyên nhân: `seed` chỉ được truyền cho bộ lấy mẫu, còn điểm khởi tạo tham số bốc từ một bộ sinh
ngẫu nhiên **toàn cục** không liên quan tới seed.

Đã sửa — nay **3/3 giống hệt**, và seed khác vẫn cho kết quả khác.

### Hệ quả cần Ngọc biết

**Mọi artifact QAOA sinh trước bản sửa mang con số không tái tạo được**, gồm toàn bộ thư mục
`artifacts_bench/`. Chúng dùng được làm ghi chép lịch sử, nhưng **không được dùng làm bằng chứng
cho bất kỳ so sánh solver nào**, và không được dùng cho chữ ký duyệt.

Cảnh báo này đã được ghi vào `artifacts_bench/README.md`.

**Câu hỏi:** chạy lại ngay, hay chờ chốt A3? Nếu A3 dẫn tới đổi lớp mô hình xấp xỉ thì phải chạy
lại toàn bộ lần nữa.

---

# Phần C — Việc đã làm, không cần duyệt

Để Ngọc và Phúc khỏi mất thời gian: những mục dưới đây là **lỗi kỹ thuật đã sửa và có test**,
không phải quyết định.

## C.1 Mười sáu mục P0/P1

| ID | Việc | Trước → Sau |
|---|---|---|
| P0-1 | CLI chẩn đoán hàm mục tiêu | không có → ablation + sweep + landscape |
| P0-2 | Cổng chặn mô hình xấp xỉ | khoá config **không code nào đọc** → bắt được FAIL thật |
| P0-3 | Xuất ràng buộc thật từ chính sách | `{}` → `constraints_encoding` minh bạch |
| P0-4a | Cổng kịch bản thiếu regime | `PASS` → `INCOMPLETE` |
| P0-4b | `gate_status` hard-code | hằng số `"PASS"` → `FALLBACK` (đo thật) |
| P0-4c | Cổng rerank không có chính sách | `PASS` giả → `NOT_EVALUATED` |
| P0-4d | Đa dạng khối bootstrap | không có → `unique_blocks: 71`, `reuse_rate: 0,996` |
| P0-5 | Backend nhận danh mục nhưng không dùng | im lặng → cảnh báo + 2 mã băm |
| P0-6 | UI dán nhãn "quantum" lên kết quả exact | → banner + badge nguồn solver |
| P1-1 | QAOA 20-bit không chạy được | n=8: **600,2s → 1,4s** (429×); n=20: bất khả thi → **183,6s** |
| P1-3 | Classical khớp ngân sách | 0,5s vs 600s → khớp đúng wall-time QAOA |
| P1-4 | Verify chỉ 0,39% không gian | **4.098 → 1.048.576** trạng thái, 2,69s |
| P1-5 | Stability chưa từng đánh giá | mọi chỉ số `null` → trùng lặp 0,933, ρ 0,99 |
| P1-7 | Codec cài trùng 2 gói | không gì bắt → test 4³ = 64 tổ hợp |
| P1-8 | Bộ nhớ đỉnh + phần cứng | cả hai `null` → **291,5 MB**, `arm/8 lõi/32 GB` |
| P1-10 | 3 test AI fail | 3 fail → 0 fail |

## C.2 Bảy lỗi im lặng — sáu cái không có trong bản rà soát đầu

| Lỗi | Số đo |
|---|---|
| `gate_status` hard-code `"PASS"` | `PASS` → `FALLBACK` |
| **Ghi nhật ký mất `logs.txt`** khi hai run trùng mã | mất 1/4 tệp metadata bắt buộc |
| **Worker QAOA treo lúc thoát** | ghi kết quả sau **2,0s** rồi treo ⇒ thử lại ×3 = **600,2s** |
| **Fallback treo vô hạn ở n>8** | `expm(2²⁰)` — treo, không phải "chậm" |
| **QAOA không tái lập dù cùng seed** | 3 lần → 2 kết quả; sau sửa 3/3 giống hệt |
| **Số ứng viên động đẩy lên 30 bit không ai chặn** | 2³⁰ ≈ **78 phút** rồi hết RAM |
| **Biến đếm cũ sau khi đổi số ứng viên** | `has 15 selected rows, expected 10` |

Năm trong bảy lỗi này **im lặng**: hệ thống vẫn chạy, vẫn ghi artifact, vẫn báo thành công.

## C.3 Trạng thái chốt

```
476 test pass + 8 chậm · 0 fail
ruff sạch · mypy không còn lỗi thuộc phần thêm mới
0 commit · 0 push · toàn bộ ở cây làm việc
không tham số tài chính nào bị đổi
```

Config chỉ thêm **ba khoá kỹ thuật**: `candidate_gate.stability_seeds`,
`candidate_gate.stability_block_length`, `performance_budget.exact_states_per_second`.

Thay đổi trong `configs/base.yaml` (ngày IPO thật của VPL, cờ chất lượng SSB) là công việc có
sẵn của người dùng, **không thuộc đợt rà soát này**.

---

# Phần D — Việc reviewer làm được tiếp, chờ chỉ đạo

| Việc | Thời gian | Giá trị |
|---|---|---|
| Thí nghiệm hội tụ maxiter | 1–2 giờ | **Khép câu B4** — biến một lựa chọn mò thành quyết định có số |
| Lặp thí nghiệm danh mục ≥5 dạng | ~15 phút | Làm kết luận A1 vững hơn |
| Chạy lại `artifacts_bench/` | ~30 phút | Phục hồi tính tái lập cho bằng chứng cũ (B5) |
| Duyệt đủ true objective trên danh mục khác | 33 phút/danh mục | Kiểm chứng A3 không phải hiện tượng cá biệt |
| Thí nghiệm E4 (có/không QAOA) | ~1 giờ | **Chỉ có nghĩa sau khi chốt A3** |
| E3 "dừng cây tiến trình" | — | Đổi hành vi khi lỗi, cần Tân xem trước |
