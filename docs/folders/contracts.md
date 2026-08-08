# packages/contracts/

**Owner:** Đỗ Ngọc Tân
**Vai trò:** Hợp đồng dữ liệu + hạ tầng chạy chung. Mọi package khác phụ thuộc đây.

## Nhiệm vụ

- Schema Pandera / Pydantic cho mọi artifact (`schemas/`).
- `ArtifactPaths` — đường dẫn artifact duy nhất được phép dùng.
- `Config` — load `configs/*.yaml` (+ profile/override).
- `RunContext` — **duy nhất** được ghi `config.json`, `data_version.json`, `metrics.json`, `logs.txt`.
- `mocks/` — dữ liệu giả đúng schema để dev song song.
- `validate_or_raise()` — validate ở biên module.

## Cây chính

```text
qshield_contracts/
  schemas/     # returns, features, regime, scenarios, risk, optimization, downstream...
  mocks/
  config.py
  paths.py
  runs.py
  validate.py
  enums.py
```

## Được làm

- Thêm/sửa schema khi thay đổi hình dạng artifact.
- Thêm mock khớp schema mới.
- Mở rộng `ArtifactPaths` khi có artifact mới.

## Không được làm

- Hard-code path/ticker/seed/ngày/ngưỡng.
- Ghi metadata run ngoài `RunContext`.
- Import `qshield_data` / `risk` / `quantum` (contracts ở đáy dependency).

## Context cho Claude

- Đổi schema = breaking change: sửa contracts → sửa bên ghi → sửa bên đọc → test.
- So sánh `StrEnum`: ép kiểu rồi `==`, không dùng `is` với string.
- Profile duy nhất: `workflow_update` (30→10, 20-bit) — xem
  [`../workflow-v2.md`](../workflow-v2.md) và `configs/`.

## Test

```bash
uv run pytest packages/contracts -q
```
