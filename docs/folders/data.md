# packages/data/

**Owner:** Nguyễn Đỗ Minh Anh
**Vai trò:** Thu thập → làm sạch → return/feature → eligibility → quality gate.
**Workflow-v2:** §7 (PIT/source), §8 (eligibility/liquidity).

## Nhiệm vụ

- Nạp giá 30 mã từ export FiinPro `data/raw/Full_Prices.xlsx` (`data.fiinpro_xlsx`); VN-Index tải
  qua vnstock (VCI) theo từng năm.
- Clean: normalize, lọc theo lịch VN-Index, gắn cờ giá (kể cả `INVALID_OHLC`), bỏ giá trước
  `first_trading_date`.
- Tính returns (từ adjusted close đã verified) — **cấm** `.ffill()` trên return.
- Features thị trường cho HMM (đúng contract feature).
- Eligibility / coverage / liquidity theo config.
- Data quality report + evidence adjusted price.

## Cây chính

```text
qshield_data/
  sources/fetch.py, loaders/{fiinpro,vnstock}.py
  clean/{normalize,corporate_actions,validate_prices}.py
  returns.py, features.py, split.py, eligibility.py, loader.py
  quality/{checks,report,evidence,price_limits}.py
  cli.py
```

## Được làm

- Gắn cờ outlier / DQ fail — báo cáo, không tự xóa im lặng.
- Point-in-time membership / source registry theo workflow-v2 (khi implement V2).
- Ghi artifact qua `ArtifactPaths` + validate schema.

## Không được làm

- Forward-fill lợi suất.
- `adjusted_close = close` không evidence.
- Dùng snapshot tương lai cho backtest (survivorship / look-ahead).
- Hard-code ticker list — lấy từ `configs/base.yaml` / profile.

## Artifact điển hình

- `data/processed/returns.parquet`, `features.parquet`
- eligibility / quality / source registry (theo profile)

## Context cho Claude

- Quy ước: giá thiếu xử lý theo `configs/base.yaml`, log rõ.
- FiinPro `adjusted_close` đã điều chỉnh sẵn mọi corporate action — **không** áp thêm registry
  back-adjust (sẽ điều chỉnh hai lần). Lỗi nằm trong file Excel thì vá qua
  `data.raw_price_patches`, có evidence.
- `adjusted_close` neo theo ngày export ⇒ không dùng làm giá hiện tại (dùng `close`). FiinPro là dữ
  liệu thương mại, gitignored. Chi tiết: `docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md`.
- Gate: Data Gate fail → downstream chỉ `EXPERIMENTAL_NON_BASELINE` (workflow-v2 §7).

## Test

```bash
uv run pytest packages/data -q
```
