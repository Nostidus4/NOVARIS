# packages/data/

**Owner:** Nguyễn Đỗ Minh Anh
**Vai trò:** Thu thập → làm sạch → return/feature → eligibility → quality gate.
**Workflow-v2:** §7 (PIT/source), §8 (eligibility/liquidity).

## Nhiệm vụ

- Fetch OHLCV từ vendor (Yahoo / DNSE / vnstock / CSV local).
- Clean: normalize, corporate actions đã đăng ký, validate prices.
- Tính returns (từ adjusted close đã verified) — **cấm** `.ffill()` trên return.
- Features thị trường cho HMM (đúng contract feature).
- Eligibility / coverage / liquidity theo config.
- Data quality report + evidence adjusted price.

## Cây chính

```text
qshield_data/
  sources/fetch.py, loaders/{yahoo,dnse,vnstock,csv_local}.py
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
- Corporate action chỉ từ registry đã duyệt (ví dụ VCB trong `configs/base.yaml`).
- Gate: Data Gate fail → downstream chỉ `EXPERIMENTAL_NON_BASELINE` (workflow-v2 §7).

## Test

```bash
uv run pytest packages/data -q
```
