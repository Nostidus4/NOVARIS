# folders/ — context cho agent / Claude

Mỗi file mô tả **một thư mục**: nhiệm vụ, owner, được/không được làm gì, entry point,
artifact, test. Đọc file thư mục bạn sắp sửa **trước** khi code.

Policy sản phẩm / thứ tự workstream: [`../workflow-v2.md`](../workflow-v2.md).
Quy tắc bất biến (CVaR, path, quantum API): [`../../CLAUDE.md`](../../CLAUDE.md).

## Dependency (một chiều)

```text
contracts
   ↑
data, ai, risk, quantum
   ↑              ↑
risk ←── (duy nhất) ── quantum   # exact cần true CVaR
   ↑
pipeline
   ↑
backend  ──HTTP──►  frontend
```

`configs/` không import code; mọi package đọc config qua `qshield_contracts.config.Config`.

## Index

| File | Thư mục |
|---|---|
| [`contracts.md`](contracts.md) | `packages/contracts/` |
| [`data.md`](data.md) | `packages/data/` |
| [`ai.md`](ai.md) | `packages/ai/` |
| [`risk.md`](risk.md) | `packages/risk/` |
| [`quantum.md`](quantum.md) | `packages/quantum/` |
| [`pipeline.md`](pipeline.md) | `packages/pipeline/` |
| [`backend.md`](backend.md) | `backend/` |
| [`frontend.md`](frontend.md) | `frontend/` |
| [`configs.md`](configs.md) | `configs/` |
| [`artifacts-data.md`](artifacts-data.md) | `data/`, `artifacts/`, `reports/`, `notebooks/` |

## Khi implement bất kỳ thay đổi nào

1. Đúng profile `workflow_update` theo [`../workflow-v2.md`](../workflow-v2.md)?
2. Schema đổi? → sửa `contracts` trước, rồi ghi + đọc trong cùng PR.
3. Path artifact? → chỉ qua `ArtifactPaths`, không nối chuỗi.
4. Công thức tài chính? → không đặt trong `backend/` hay `frontend/`.
5. Claim / output? → khớp [`../disclaimer.md`](../disclaimer.md) và workflow-v2 §24.
