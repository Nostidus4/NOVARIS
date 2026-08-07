**A. Quyết Định Chặn Baseline**

| ID | Quyết định |
| ----- | ----- |
| TL-001 | Chốt baseline dùng **30 mã VN30 snapshot 2026-08-03**. Minh Anh phải xuất `universe_30_asof_20260803.csv` có ticker nội bộ, ticker vendor, company name, source, checksum/version. Nếu chưa có file này thì mọi run vẫn là `NON_BASELINE_RUN`. |
| TL-002 | **Không chấp nhận tự gán `close = adjusted_close` cho baseline.** Demo có thể dùng với flag limitation, nhưng workflow update phải có evidence adjusted close/corporate action hoặc cross-check rõ ràng. |
| TL-003 | Chốt data range: `asset_train_start = 2016-01-01`, `test_end = 2026-07-31`. Khi đổi data phải tạo data version mới. |
| TL-004 | Giữ eligibility hiện tại: `min_history_sessions=252`, coverage `>=98%`, turnover 20 ngày `>=1 tỷ VND`. Mã bị loại phải có reason code. Exception cần Minh Anh đề xuất, Ngọc \+ Phúc duyệt. |
| TL-005 | TL-005 update: Development dùng 2,000 scenarios. Final baseline ưu tiên 5,000 scenarios. Trong trường hợp 5,000 không đáp ứng runtime/RAM/gate stability, được phép dùng 2,000-4,999 scenarios làm final accepted run, nhưng phải ghi rõ `num_scenarios`, lý do chọn, benchmark runtime/RAM, Scenario Gate PASS/WARN/FAIL và limitation trong report. Không được so sánh các run khác nhau nếu không ghi rõ S. |
| TL-006 | Scenario Gate hiện tại giữ làm chuẩn tạm, nhưng nếu fail metric quan trọng như kurtosis thì **không được gọi là baseline**. Có thể chạy tiếp bằng approved exception để phân tích impact, nhưng report phải ghi rõ gate fail. |
| TL-007 | Duyệt tạm transaction cost base: fee `0.0015`, spread `0.0010`, liquidity `0.0005`, `weight_sum_tolerance=1e-8`. Phúc phải chạy sensitivity low/base/high. |
| TL-008 | Liquidity penalty là **objective component riêng**, không cộng trùng hai lần vào transaction cost. Transaction cost \= fee \+ spread; liquidity penalty \= khoản phạt riêng trong scoring/objective. |
| TL-009 | Chốt stress-to-cash policy bản đầu: target tăng cash `10%`, maximum reduction mỗi mã `30%`. Phúc/Tú có thể đề xuất mapping `p_stress -> B_t`, nhưng trước mắt dùng base policy này để chạy pipeline. |
| TL-010 | Candidate ranking chốt theo net score: lợi ích giảm CVaR 10/20/30 \+ baseline CVaR contribution, trừ transaction cost và liquidity penalty. Ticker ineligible hoặc weight \= 0 bị loại trước ranking. Tie-break ưu tiên CVaR reduction cao hơn, sau đó cost thấp hơn. |
| TL-011 | Canonical financial objective ưu tiên **giảm CVaR trước**, sau đó mới bám cash target. Nếu giảm CVaR và cash target xung đột, chọn nghiệm có true CVaR tốt hơn, miễn không vi phạm constraint. |

**B. Quantum / Benchmark**

| ID | Quyết định |
| ----- | ----- |
| TL-012 | Final QAOA giữ `p=1`, `shots=1024`, COBYLA `maxiter=200`, warm-start, 10 seed `[101,202,303,404,505,606,707,808,909,1001]`. Dev nhanh được giảm seed/shots nhưng phải gắn `NON_FINAL_CONFIG`. |
| TL-013 | Performance budget: exact 20-bit phải chạy được trong giới hạn máy benchmark nhóm chọn; QAOA mỗi seed phải có timeout riêng và toàn run có timeout tổng. Tân phải báo runtime/RAM theo cùng một máy reference, không lấy số lẫn máy. |
| TL-014 | Surrogate Gate phải có MAE/RMSE, Spearman, top-k recall, feasible rate, seed stability. Nếu fail thì không dùng QUBO/QAOA làm baseline, chỉ được phân tích với exception. |
| TL-015 | Duyệt benchmark bắt buộc: exact \+ QAOA \+ classical trên cùng `qubo_hash`, đủ 10 seed, có success probability, feasible rate, optimality gap, runtime/memory và true-CVaR rerank. |

**C. Rerank / Polishing / Product**

| ID | Quyết định |
| ----- | ----- |
| TL-016 | Rerank top **20 distinct feasible bitstrings** nếu đủ; nếu ít hơn thì rerank toàn bộ feasible candidates. Tie-break bằng true objective, sau đó CVaR thấp hơn, sau đó cost thấp hơn. |
| TL-017 | Polishing được duyệt với: zero-action lock, biên `±5pp`, final reduction `[0,30%]`, không short, không weight âm. |
| TL-018 | Materiality: chỉ gọi là “có cải thiện” nếu true CVaR giảm tối thiểu **1% relative** sau cost. Nếu không đạt thì hiển thị cảnh báo hoặc no-action/fallback. |
| TL-019 | Product Gate do Ngọc ký cuối cùng. Baseline chỉ công bố khi đủ `data_gate`, `scenario_gate`, `product_gate`, dashboard reconciliation, limitations/disclaimer và UAT evidence. |

**D. Quyết Định Kỹ Thuật**

| ID | Quyết định |
| ----- | ----- |
| TL-020 | Duyệt dynamic underfill: nếu chưa đủ 10 mã eligible thì dùng `M=min(N_eligible,10)`, gắn `NON_BASELINE_RUN`, không padding ticker giả. |
| TL-021 | Giữ cả `candidate_top10.csv` và `candidate_order.json`. CSV để audit ranking, JSON để khóa bit order/hash. |
| TL-022 | Nếu QAOA timeout hoặc không có nghiệm feasible, dùng exact làm `actual_solver`, nhưng phải báo QAOA failure trung thực. |
| TL-023 | Không tuyên bố quantum advantage. Simulator không đại diện QPU. Exact chỉ chứng minh tối ưu ở tầng QUBO, không phải tối ưu tài chính thật. |
