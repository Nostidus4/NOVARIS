# Plan refactor `CLEAN.ipynb` → `packages/data/qshield_data`

**Mục tiêu:** biến notebook 60 cell (8 bước data pipeline) thành package `qshield_data` theo cấu trúc trong `Structure.md` §3, chạy được bằng CLI, đọc/ghi vào `~/Doc/QSHIELD/data/{raw,interim,processed,metadata}`.

**Ràng buộc bao trùm:**
- Bám nguyên tên file trong Structure.md, không đổi.
- Config (paths, thresholds, dates, universe) **KHÔNG** hard-code trong `qshield_data` — đọc từ `configs/*.yaml` qua `packages/contracts/config.py` (Structure §3 quy định `contracts/config.py` là nơi *duy nhất* mở file yaml).
- Logic bên trong hàm giữ nguyên như notebook, không refactor thuật toán, không đổi library.
- Point-in-time và raw-immutable là bất biến (Cell 0 quy định).

---

## 1. Bảng mapping cell → file

| Cell | Nội dung | Đi vào | Thành hàm/class |
|:---:|---|---|---|
| 0 | Markdown intro | — | (bỏ, giữ trong `docs/` nếu cần) |
| 1 | Markdown header "Setup" | — | bỏ |
| 2 | `!pip install ...` | — | bỏ (đã có `pyproject.toml`) |
| 3 | Imports | rải khắp các file | (chuẩn Python, không thành hàm) |
| 4 | Markdown "Config" | — | bỏ |
| **5** | **VERSION, TIME SPLITS, ELIGIBILITY THRESHOLDS, PATHS** | ⚠️ **KHÔNG vào `qshield_data`** — chuyển sang `configs/data.yaml` + `configs/universe.yaml`; đọc qua `contracts.config` | (là YAML, không phải code) |
| 6 | `sha256_of_file`, `to_utc_date` | `manifest.py` (private helpers) | `_sha256_of_file`, `_to_utc_date` |
| 7 | Markdown | — | bỏ |
| **8** | **UNIVERSE_ROWS (30 mã VN30)** | ⚠️ `configs/universe.yaml` (30 rows). `sources/registry.py` chỉ có hàm `load_universe()` đọc yaml đó. | `load_universe() -> pd.DataFrame` |
| **9** | **SOURCE_ROWS** | `sources/registry.py` | `build_source_register(access_date: str) -> pd.DataFrame` |
| 10 | Markdown | — | bỏ |
| **11** | `download_ticker` (Yahoo) | `sources/loaders/yahoo.py` ⚠️ **file mới, Structure chưa có** | `download_ticker(symbol, start, end, max_retries=3)` |
| **12** | `download_vnindex_vnstock`, `download_ticker_vnstock` | `sources/loaders/vnstock.py` | `download_vnindex(start, end, max_retries=3)`, `download_ticker(ticker, start, end, max_retries=3)` |
| 13 | Markdown "Diagnostic DNSE" | — | bỏ (chuyển sang `notebooks/exploration/dnse_diagnostic.ipynb` nếu cần) |
| 14 | Diagnostic DNSE code | — | bỏ (như trên) |
| **11-cont** | `download_ticker_dnse` (nằm trong Cell 12, tui thấy có DNSE loader) | `sources/loaders/dnse.py` ⚠️ **file mới, Structure chưa có** | `download_ticker(ticker, start, end, max_retries=3)` |
| **15** | `_download_one` + orchestration multi-source | `sources/loaders/__init__.py` HOẶC file mới `sources/fetch.py` | `fetch_all_prices(universe: pd.DataFrame, start, end, raw_dir: Path) -> pd.DataFrame` (trả manifest) |
| **16** | Tải VN-Index (ưu tiên vnstock, fallback Yahoo) | `sources/fetch.py` (cùng file với Cell 15) | `fetch_vn_index(start, end, raw_dir: Path) -> tuple[pd.DataFrame, str, str]` |
| 17 | Markdown | — | bỏ |
| **18** | Đọc raw → concat → chuẩn hoá schema (rename cột, ép kiểu) | `clean/normalize.py` | `load_and_normalize(raw_manifest: pd.DataFrame, data_version: str) -> pd.DataFrame` |
| **19** | Dedup + loại phantom Yahoo + flag quality | `clean/validate_prices.py` | `dedup_prices(df) -> tuple[pd.DataFrame, int]`, `remove_yahoo_phantom_days(df, vn_index) -> tuple[pd.DataFrame, int]`, `flag_price_quality(df) -> pd.DataFrame` |
| **20** | Loại pre-listing + sort + save `prices_adjusted.parquet` | `clean/corporate_actions.py` (dù chưa có logic split thực sự — Yahoo/DNSE `Adj Close` đã điều chỉnh — nhưng đây là file gần nhất về mặt "handle sự kiện doanh nghiệp") | `remove_pre_listing(df, universe) -> pd.DataFrame` |
| 21 | Markdown | — | bỏ |
| **22** | `compute_asset_returns` (simple + log return) | `returns.py` | `compute_asset_returns(df: pd.DataFrame) -> pd.DataFrame` |
| **23** | Market features (rolling vol, drawdown, liquidity) | `features.py` | `build_market_features(index_df: pd.DataFrame \| None, returns: pd.DataFrame, ...) -> pd.DataFrame` |
| 24 | Point-in-time check (assert) | `features.py` | `_assert_point_in_time(market: pd.DataFrame) -> None` |
| 25-45 | Toàn bộ EDA blocks 1-6 | ⚠️ **Chuyển sang `notebooks/exploration/eda_vn30_baseline.ipynb`**, KHÔNG vào package | (là notebook riêng) |
| 46 | Markdown | — | bỏ |
| **47** | `build_eligibility` | ⚠️ **file mới `eligibility.py`** hoặc gộp vào `features.py` — xem §6 câu hỏi | `build_eligibility(prices, universe, thresholds: dict) -> pd.DataFrame` |
| **48** | Save `eligibility_daily.parquet` | thuộc CLI orchestrator, không phải file riêng | (gọi trong `cli.py`) |
| 49 | Markdown | — | bỏ |
| **50** | `assign_split` + apply cho returns & market | `split.py` | `assign_split(dt, level, splits_config: dict) -> str`, `apply_splits(df, level, splits_config) -> pd.DataFrame` |
| 51 | Markdown | — | bỏ |
| **52** | 6 checks DQ (dup, non-positive, negative volume, pre-listing, universe=30, split overlap) | `quality/checks.py` | mỗi check 1 hàm: `check_no_duplicates(prices)`, `check_positive_prices(prices)`, `check_no_negative_volume(prices)`, `check_no_pre_listing(prices, universe)`, `check_universe_count(universe)`, `check_split_no_overlap(returns)`; + `run_all_checks(...)` |
| 53 | Markdown | — | bỏ |
| **54** | Data Dictionary Excel | `quality/report.py` (hoặc file riêng — xem §6) | `build_data_dictionary(out_path: Path) -> Path` |
| **55** | Data Manifest JSON | `manifest.py` | `build_manifest(run_id, data_version, files, ...) -> dict`, `write_manifest(manifest, out_path) -> Path` |
| **56** | Sample loader script | ⚠️ **KHÔNG vào package** — đây là code cho consumer (Tú/Phúc). Structure không có chỗ. Đề xuất `packages/data/src/qshield_data/loader.py` hoặc expose qua `__init__.py` — xem §6 | `load_data(table, split=None, date=None, tickers=None)`, `get_manifest()` |
| 57 | Markdown | — | bỏ |
| 58 | DoD checklist | — | bỏ (đưa vào `docs/` nếu cần) |
| 59 | Markdown ghi chú | — | bỏ |

---

## 2. Interface từng file

### `qshield_data/__init__.py`
```python
"""Q-SHIELD data package: fetch, clean, feature, quality-check VN30 market data."""
__version__ = "1.0.0"
```

### `qshield_data/cli.py`
```python
import typer
app = typer.Typer(help="Q-SHIELD data pipeline CLI")

@app.command()
def fetch(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 1-2: đọc universe, tải giá từ Yahoo/DNSE/vnstock vào data/raw/."""

@app.command()
def clean(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 3: normalize + dedup + phantom-day + pre-listing → data/processed/prices_adjusted.parquet."""

@app.command()
def features(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 4: tính returns + market features → data/processed/{returns,market_features}.parquet."""

@app.command()
def eligibility(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 5: build eligibility_daily.parquet."""

@app.command()
def split(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 6: gán cột split (train/validation/test) cho returns & market_features."""

@app.command()
def quality(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 7: chạy Data Quality Gate → reports/data_quality_report.csv."""

@app.command()
def manifest(config: Path = Path("configs/data.yaml")) -> None:
    """Bước 8: build data_dictionary.xlsx + data_manifest.json."""

@app.command()
def all(config: Path = Path("configs/data.yaml")) -> None:
    """Chạy tuần tự fetch → clean → features → eligibility → split → quality → manifest."""

if __name__ == "__main__":
    app()
```

### `qshield_data/sources/registry.py`
```python
def load_universe(universe_yaml: Path) -> pd.DataFrame:
    """Đọc configs/universe.yaml → DataFrame 30 rows với cột ticker, yahoo_symbol, company_name, first_trading_date, exchange_current, exchange_history, data_source, notes."""

def build_source_register(access_date: str, yfinance_version: str, vnstock_version: str) -> pd.DataFrame:
    """Sinh Source Register DataFrame với 4 rows: YF_PRICES, VNSTOCK_PRICES, DNSE_PRICES, VNSTOCK_INDEX."""

def save_universe_and_sources(universe: pd.DataFrame, sources: pd.DataFrame, metadata_dir: Path, universe_as_of: str) -> tuple[Path, Path]:
    """Ghi universe_asof_{YYYYMMDD}.csv và source_register.csv vào data/metadata/."""
```

### `qshield_data/sources/loaders/yahoo.py` ⚠️ file mới
```python
def download_ticker(symbol: str, start: str, end: str, max_retries: int = 3) -> pd.DataFrame | None:
    """Tải OHLCV 1 mã từ Yahoo Finance qua yfinance, retry + exponential backoff."""
```

### `qshield_data/sources/loaders/dnse.py` ⚠️ file mới
```python
def download_ticker(ticker: str, start: str, end: str, max_retries: int = 3) -> tuple[pd.DataFrame | None, str]:
    """Tải OHLCV 1 mã từ DNSE/Entrade chart-api. Trả (df, source_tag). Giá đã ×1000 để nhất quán VND."""
```

### `qshield_data/sources/loaders/vnstock.py`
```python
def download_vnindex(start: str, end: str, max_retries: int = 3) -> pd.DataFrame | None:
    """Tải VN-Index từ vnstock (source=VCI), interval=1D."""

def download_ticker(ticker: str, start: str, end: str, max_retries: int = 3) -> pd.DataFrame | None:
    """Tải OHLCV 1 mã VN từ vnstock (source=VCI) — dùng khi cần alternative cho DNSE."""
```

### `qshield_data/sources/loaders/csv_local.py`
```python
def load_from_csv(csv_path: Path) -> pd.DataFrame:
    """Đọc raw CSV đã tải sẵn (offline mode / demo). Schema khớp output của các loader trên."""
```

### `qshield_data/sources/fetch.py` ⚠️ file mới (Structure không có, nhưng cần chỗ chứa orchestration Cell 15-16)
```python
def fetch_all_prices(universe: pd.DataFrame, start: str, end: str, raw_dir: Path) -> pd.DataFrame:
    """Route theo universe['data_source']: dnse → DNSE, else → Yahoo; fallback Yahoo nếu DNSE fail. Ghi CSV vào raw_dir/prices/, trả raw_manifest DataFrame."""

def fetch_vn_index(start: str, end: str, raw_dir: Path) -> tuple[pd.DataFrame | None, str | None, str | None]:
    """Ưu tiên vnstock, fallback Yahoo. Ghi CSV vào raw_dir/vn_index/, trả (df, symbol_used, source_used)."""
```

### `qshield_data/clean/normalize.py`
```python
def load_and_normalize(raw_manifest: pd.DataFrame, data_version: str) -> pd.DataFrame:
    """Đọc từng file raw CSV OK trong manifest → concat → rename cột (Open→open, Adj Close→adjusted_close, ...) → ép kiểu numeric → gắn ticker, source_id, data_version. Trả DataFrame long-format."""
```

### `qshield_data/clean/validate_prices.py`
```python
def dedup_prices(prices: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Sort theo (date, ticker, volume) → drop_duplicates keep='last' để ưu tiên row volume cao nhất. Trả (df, n_removed)."""

def remove_yahoo_phantom_days(prices: pd.DataFrame, vn_index: pd.DataFrame | None) -> tuple[pd.DataFrame, int]:
    """Loại các ngày Yahoo forward-fill mà VN-Index không có (chỉ áp dụng cho source YF_PRICES/YF_PRICES_FALLBACK)."""

def flag_price_quality(prices: pd.DataFrame) -> pd.DataFrame:
    """Thêm cột quality_flag: 'OK' hoặc bitmask pipe-separated (NONPOS_PRICE|NONPOS_CLOSE|NEG_VOLUME|ZERO_VOLUME)."""
```

### `qshield_data/clean/corporate_actions.py`
```python
def remove_pre_listing(prices: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Loại các row có date < first_trading_date của ticker (theo PR-DAT-017)."""

# Note: split/dividend adjustment đã có sẵn trong adjusted_close từ Yahoo/DNSE — không cần re-implement.
# File này giữ nguyên cho khả năng mở rộng sau (nếu chuyển sang raw price + tự tính adjustment factor).
```

### `qshield_data/returns.py`
```python
def compute_asset_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Tính simple_return và log_return per ticker, KHÔNG forward-fill (ngày đầu mỗi ticker = NaN, đúng ý)."""
```

### `qshield_data/features.py`
```python
def build_market_features(
    index_df: pd.DataFrame | None,
    returns: pd.DataFrame,
    index_source_tag: str | None,
) -> pd.DataFrame:
    """Nếu index_df có → dùng VN-Index thật; nếu None → fallback custom composite EW từ returns.
    Tính market_log_return, market_simple_return, realized_vol_20d, drawdown (vs rolling_max_252), liquidity_20d.
    Tất cả rolling đều min_periods đủ lớn, KHÔNG center."""

def _assert_point_in_time(market: pd.DataFrame) -> None:
    """Assert rolling ở ngày t không nhìn thấy dữ liệu > t (shift-and-recompute check)."""
```

### `qshield_data/eligibility.py` ⚠️ đề xuất file mới — xem §6
```python
def build_eligibility(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    min_history_sessions: int,
    min_coverage_pct: float,
    min_turnover_20d_vnd: float,
) -> pd.DataFrame:
    """Trả DataFrame [date, ticker, eligible_flag, reason_code, sessions_available, coverage_pct, avg_turnover_20d].
    Point-in-time cumulative, dùng first_data_date thực tế làm mốc coverage."""
```

### `qshield_data/split.py`
```python
def assign_split(dt: pd.Timestamp, level: str, splits_config: dict) -> str:
    """level: 'market' | 'asset'. Trả 'train' | 'validation' | 'test' | 'out_of_scope'."""

def apply_splits(df: pd.DataFrame, level: str, splits_config: dict) -> pd.DataFrame:
    """Thêm cột 'split' cho df dựa trên assign_split. Đảm bảo train/val/test không overlap."""
```

### `qshield_data/quality/checks.py`
```python
def check_no_duplicates(prices: pd.DataFrame) -> dict:
    """DQ-001, AC-DAT-004."""

def check_positive_prices(prices: pd.DataFrame) -> dict:
    """DQ-002, AC-DAT-005."""

def check_no_negative_volume(prices: pd.DataFrame) -> dict:
    """DQ-003."""

def check_no_pre_listing(prices: pd.DataFrame, universe: pd.DataFrame) -> dict:
    """DQ-004, AC-DAT-011."""

def check_universe_count(universe: pd.DataFrame, expected: int = 30) -> dict:
    """DQ-005, AC-DAT-001."""

def check_split_no_overlap(returns: pd.DataFrame) -> dict:
    """DQ-006, AC-DAT-009."""

def run_all_checks(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    returns: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """Chạy 6 check, trả (report_df, all_pass). Mỗi dict có: check_id, check_name, type, status, count, trace."""
```

### `qshield_data/quality/report.py`
```python
def write_quality_report(checks_df: pd.DataFrame, out_path: Path) -> Path:
    """Ghi reports/data_quality_report.csv (Structure §3 quy định format HTML — tui đề xuất csv trước, HTML sau; xem §6)."""

def build_data_dictionary(out_path: Path) -> Path:
    """Sinh data_dictionary.xlsx với các sheet: universe_register, prices_adjusted, returns, market_features, eligibility_daily."""
```

### `qshield_data/manifest.py`
```python
def _sha256_of_file(path: Path) -> str:
    """SHA-256 checksum, đọc theo chunk 1MB."""

def _to_utc_date(x) -> str:
    """Chuẩn hoá về 'YYYY-MM-DD'."""

def _file_info(path: Path, data_root: Path) -> dict | None:
    """Trả {path, sha256, size_bytes, modified_at} hoặc None nếu file không tồn tại."""

def build_manifest(
    run_id: str,
    data_version: str,
    universe_version: str,
    universe_as_of: str,
    files: dict[str, Path],
    row_counts: dict[str, int],
    splits_config: dict,
    eligibility_config: dict,
    quality_gate_pass: bool,
    index_symbol_used: str | None,
    index_source_used: str | None,
    data_root: Path,
) -> dict:
    """Xây manifest dict."""

def write_manifest(manifest: dict, out_path: Path) -> Path:
    """Ghi metadata/data_manifest.json, ensure_ascii=False."""
```

### `qshield_data/loader.py` ⚠️ đề xuất — xem §6
```python
def load_data(
    table: str,
    split: str | None = None,
    date: str | None = None,
    tickers: list[str] | None = None,
    data_root: Path | None = None,
) -> pd.DataFrame:
    """Consumer API cho Tú/Phúc. table ∈ {universe, prices, returns, market_features, eligibility}."""

def get_manifest(data_root: Path | None = None) -> dict:
    """Đọc metadata/data_manifest.json."""
```

---

## 3. Chỗ cần tách / gộp / bổ sung so với notebook

### 3.1 Loaders (Structure chỉ liệt kê `vnstock.py` + `csv_local.py`)
Notebook có **3 nguồn**: Yahoo Finance, DNSE/Entrade, vnstock. Đề xuất **thêm 2 file mới**:
- `sources/loaders/yahoo.py`
- `sources/loaders/dnse.py`

Cùng với `vnstock.py` và `csv_local.py` đã có trong Structure. Nếu không tách, `vnstock.py` sẽ chứa cả 3 loader → sai tên file.

### 3.2 Orchestration multi-source (Cell 15-16)
Cần **file mới** `sources/fetch.py` cho 2 hàm `fetch_all_prices` + `fetch_vn_index`. Đây là routing logic, không thuộc registry cũng không thuộc từng loader riêng.

### 3.3 Eligibility (Cell 47)
Structure §3 phần `packages/data/` không liệt kê `eligibility.py`. **2 phương án:**
- **A.** Thêm file mới `qshield_data/eligibility.py` (tui đề xuất — logic nặng, đủ chiếm 1 file).
- **B.** Gộp vào `features.py` (mismatched — eligibility không phải "feature", nó là gate).

### 3.4 Config — điểm QUAN TRỌNG NHẤT
Cell 5 hard-code toàn bộ constants. Theo Structure §1.1 và §3, đây phải là YAML:

| Constant notebook | File YAML đích |
|---|---|
| `DATA_VERSION`, `UNIVERSE_VERSION`, `UNIVERSE_AS_OF` | `configs/base.yaml` |
| `MARKET_TRAIN_START/END`, `ASSET_TRAIN_START/END`, `VAL_*`, `TEST_*` | `configs/data.yaml` |
| `MIN_HISTORY_SESSIONS`, `MIN_COVERAGE_PCT`, `MIN_TURNOVER_20D_VND` | `configs/data.yaml` (section `eligibility`) |
| `DATA_ROOT`, `RAW_DIR`, `PROCESSED`, `METADATA`, `REPORTS` | `configs/base.yaml` (section `paths`) hoặc `contracts/paths.py` |
| `UNIVERSE_ROWS` (30 mã) | `configs/universe.yaml` |

`qshield_data` **chỉ nhận `config: dict`** đã parse, không tự đọc yaml. Việc đọc yaml là của `packages/contracts/config.py`.

### 3.5 EDA (Cell 25-45)
Toàn bộ 6 EDA blocks (VN-Index history, 30-ticker coverage, fat-tail, correlation, regime correlation, top-5 extreme days) **KHÔNG** vào package. Chuyển sang `notebooks/exploration/eda_vn30_baseline.ipynb`. Structure §1.1 quy định "notebook không được chứa core logic — chỉ gọi lại hàm trong `packages/`" → OK.

### 3.6 Sample loader (Cell 56)
Notebook sinh ra `sample_loader.py` như một file **standalone** đặt bên cạnh data. Structure không có chỗ này. **3 phương án** — xem §6.

### 3.7 Data dictionary (Cell 54)
Structure không có file riêng cho dictionary. Đề xuất: đặt hàm `build_data_dictionary()` trong `quality/report.py` (cùng nhóm với quality report).

---

## 4. Thứ tự implement (dependency order)

| # | File | Lý do phải xong trước |
|:-:|---|---|
| 1 | `configs/universe.yaml` + `configs/data.yaml` + `configs/base.yaml` | Toàn bộ code đọc từ đây |
| 2 | `sources/registry.py` | `load_universe()` là input của mọi bước sau |
| 3 | `sources/loaders/{yahoo,dnse,vnstock,csv_local}.py` | Độc lập nhau, làm song song được |
| 4 | `sources/fetch.py` | Depends #2 + #3 |
| 5 | `clean/normalize.py` | Depends #4 (raw manifest) |
| 6 | `clean/validate_prices.py` | Depends #5 |
| 7 | `clean/corporate_actions.py` | Depends #6 |
| 8 | `returns.py` | Depends #7 (prices sạch) |
| 9 | `features.py` | Depends #8 + VN-Index từ #4 |
| 10 | `eligibility.py` | Depends #7 + #2 |
| 11 | `split.py` | Depends #8 + #9 |
| 12 | `quality/checks.py` | Depends #7 + #11 |
| 13 | `quality/report.py` | Depends #12 |
| 14 | `manifest.py` | Depends toàn bộ output files |
| 15 | `loader.py` (nếu chọn phương án A/B ở §6) | Depends #14 |
| 16 | `cli.py` | Cuối cùng, wire tất cả |

**Song song hoá được:** #3 (4 loaders), #5-9 (một chuỗi tuyến tính) vs #10 (eligibility) — làm 2 nhánh song song sau khi #7 xong.

---

## 5. CLI (`cli.py`) subcommand

Dùng `typer`. 8 lệnh, mỗi lệnh làm đúng 1 bước notebook:

| Lệnh | Gọi hàm | Output |
|---|---|---|
| `qshield-data fetch` | `registry.load_universe` → `fetch.fetch_all_prices` + `fetch.fetch_vn_index` → `registry.save_universe_and_sources` | `data/raw/prices/*.csv`, `data/raw/vn_index/*.csv`, `data/metadata/{universe_asof_*,source_register}.csv` |
| `qshield-data clean` | `normalize.load_and_normalize` → `validate_prices.dedup_prices` → `validate_prices.remove_yahoo_phantom_days` → `validate_prices.flag_price_quality` → `corporate_actions.remove_pre_listing` | `data/processed/prices_adjusted.parquet` |
| `qshield-data features` | `returns.compute_asset_returns` → `features.build_market_features` | `data/processed/{returns,market_features}.parquet` |
| `qshield-data eligibility` | `eligibility.build_eligibility` | `data/processed/eligibility_daily.parquet` |
| `qshield-data split` | `split.apply_splits` (level=asset + market) | update `returns.parquet`, `market_features.parquet` (thêm cột `split`) |
| `qshield-data quality` | `quality.checks.run_all_checks` → `quality.report.write_quality_report` | `reports/data_quality_report.csv` |
| `qshield-data manifest` | `quality.report.build_data_dictionary` → `manifest.build_manifest` → `manifest.write_manifest` | `data/metadata/{data_dictionary.xlsx,data_manifest.json}` |
| `qshield-data all` | chạy tuần tự 7 lệnh trên | tất cả |

Mỗi lệnh nhận `--config configs/data.yaml` và log ra `RUN_ID` để trace.

---

## 6. Câu hỏi cần bà quyết trước khi implement

1. **Loaders — thêm `yahoo.py` và `dnse.py`?** Structure §3 chỉ ghi `vnstock.py` + `csv_local.py`. Notebook có 3 nguồn. Đề xuất thêm 2 file mới. **Chốt hay giữ nguyên Structure?**

2. **Eligibility — file riêng hay gộp?**
   - A. `qshield_data/eligibility.py` (đề xuất)
   - B. Gộp vào `features.py`
   - C. Gộp vào `quality/checks.py` (không đề xuất — nó không phải check)

3. **`sources/fetch.py` — file mới có được không?** Cell 15-16 cần chỗ chứa orchestration. Không thuộc registry, không thuộc loader riêng. **Chốt tên file:** `fetch.py` hay `orchestrator.py`?

4. **Sample loader (Cell 56) — đặt đâu?**
   - A. `qshield_data/loader.py` (là một API của package, downstream `from qshield_data import load_data`) — tui đề xuất.
   - B. Sinh `sample_loader.py` cạnh `data/` (giữ nguyên notebook, đặt ngoài package).
   - C. `packages/contracts/paths.py` xử lý paths, không có helper riêng cho load — Tú/Phúc tự dùng `pd.read_parquet(paths.returns)`.

5. **Config — đọc từ đâu?**
   - Notebook hard-code trong Cell 5.
   - Structure §3 nói `contracts/config.py` là **duy nhất** mở yaml.
   - **Câu hỏi:** `packages/contracts/` đã có sẵn `config.py` chưa? Nếu chưa, ai viết trước — Tân (owner của contracts) hay Minh Anh phải chờ? Trong lúc chờ, `qshield_data` nhận `dict` từ đâu?
   - **Đề xuất tạm:** viết `qshield_data/_config_stub.py` đọc yaml trực tiếp, đánh dấu `# TODO: swap for contracts.config once available`.

6. **Data quality report — CSV hay HTML?** Structure §3 ghi `.html`. Notebook ghi `.csv`. Chốt bên nào? (Tui đề xuất giữ CSV cho MVP, HTML thêm sau.)

7. **`corporate_actions.py` — giữ file này dù chưa có logic split?** Adjusted price đã có sẵn từ Yahoo/DNSE. File chỉ chứa `remove_pre_listing`. Có nên đổi tên `pre_listing.py` hay giữ `corporate_actions.py` để mở rộng sau?

8. **DNSE URL và headers — có thay đổi gì so với notebook không?** Notebook đang gọi `https://services.entrade.com.vn/chart-api/v2/ohlcs/stock`. Public API, không auth. Nếu team đã có concern về ổn định → thêm plan cache/retry mạnh hơn?

9. **Universe.yaml format — flat list hay nested?** 30 rows với 8 cột. Đề xuất:
   ```yaml
   universe_version: v1.0
   universe_as_of: 2026-08-03
   tickers:
     - ticker: ACB
       yahoo_symbol: ACB.VN
       company_name: "Ngân hàng Á Châu"
       first_trading_date: 2006-11-21
       exchange_current: HOSE
       exchange_history: "HNX→HOSE 2020-12"
       data_source: dnse
       notes: ""
     - ...
   ```
   **Chốt schema?**

10. **Tests?** Structure §3 phần `packages/data/` không ghi `tests/`. Có viết test hay không, và nếu có thì cho hàm nào (đề xuất: `returns.compute_asset_returns`, `split.assign_split`, `quality.checks.*`)?

---

## Tóm tắt executive

- **20 file code** trong `qshield_data/` (bao gồm `__init__.py` các subfolder).
- **4 file mới** so với Structure gốc: `sources/loaders/yahoo.py`, `sources/loaders/dnse.py`, `sources/fetch.py`, `eligibility.py`, `loader.py` — cần bà duyệt.
- **3 file YAML mới** trong `configs/`: `base.yaml`, `data.yaml`, `universe.yaml`.
- **Toàn bộ EDA (21 cell)** ra khỏi package, chuyển sang notebook exploration.
- **10 câu hỏi phải chốt** trước khi code, quan trọng nhất là #1, #4, #5.
