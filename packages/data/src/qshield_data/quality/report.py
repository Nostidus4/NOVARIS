# Nguyễn Đỗ Minh Anh - xuất reports/data_quality_report.html.
"""Xuất Data Quality Report và Data Dictionary — port từ `CLEAN.ipynb`.

Format DQ report: `docs/Structure.md` §3 ghi `.html`, nhưng notebook gốc và plan.md §6 câu 6 chốt
dùng CSV cho MVP (đơn giản hơn, đủ dùng cho `manifest.py`/`loader.py` đọc lại) — HTML có thể thêm
sau nếu cần hiển thị đẹp hơn cho báo cáo cuối. Ghi rõ ở đây để không ai ngỡ ngàng khi thấy
`.csv` thay vì `.html`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook

_DATA_DICTIONARY: dict[str, list[tuple[str, str, str, str, str]]] = {
    "universe_register": [
        ("ticker", "string", "-", "Mã cổ phiếu, upper-case", "HPG"),
        ("yahoo_symbol", "string", "-", "Symbol trên Yahoo Finance", "HPG.VN"),
        ("company_name", "string", "-", "Tên doanh nghiệp", "Hoà Phát"),
        (
            "first_trading_date",
            "date",
            "YYYY-MM-DD",
            "Ngày giao dịch đầu tiên (best-effort)",
            "2007-11-15",
        ),
        ("exchange_current", "string", "-", "Sàn hiện tại", "HOSE"),
        ("exchange_history", "string", "-", "Lịch sử chuyển sàn", "HNX→HOSE 2020"),
        ("data_source", "string", "enum", "Nguồn tải giá chính: yahoo | dnse", "dnse"),
    ],
    "prices_adjusted": [
        ("date", "date", "YYYY-MM-DD", "Ngày giao dịch", "2024-06-28"),
        ("ticker", "string", "-", "Mã cổ phiếu", "HPG"),
        ("open, high, low, close", "float", "VND", "Giá không điều chỉnh", ""),
        (
            "adjusted_close",
            "float",
            "VND",
            "Giá đã điều chỉnh cổ tức/chia tách",
            "27500.0",
        ),
        ("volume", "int", "shares", "Khối lượng khớp lệnh", "5230000"),
        ("turnover_value", "float", "VND", "close × volume", "1.4e11"),
        (
            "quality_flag",
            "string",
            "-",
            (
                "OK hoặc bitmask lỗi (pipe-separated: NONPOS_PRICE|NONPOS_CLOSE|NEG_VOLUME|"
                "ZERO_VOLUME). Yahoo Finance đôi khi forward-fill giá cho ngày HOSE nghỉ (phantom "
                "days, close = close ngày trước, volume = 0). Pipeline cross-check với lịch giao "
                "dịch VN-Index (vnstock/VCI — feed thật từ broker VN) và loại các ngày phantom này "
                "khỏi prices_adjusted trước khi lưu, nên không còn xuất hiện trong dữ liệu cuối."
            ),
            "OK",
        ),
        ("source_id", "string", "-", "Nguồn dữ liệu", "YF_PRICES"),
        ("data_version", "string", "semver", "Phiên bản data run", "v1.0.0"),
    ],
    "returns": [
        ("date", "date", "YYYY-MM-DD", "Ngày giao dịch", ""),
        ("ticker", "string", "-", "Mã cổ phiếu", ""),
        ("simple_return", "float", "decimal", "P_t/P_{t-1} - 1", "0.0123"),
        ("log_return", "float", "decimal", "ln(P_t/P_{t-1})", "0.0122"),
        ("adjusted_close", "float", "VND", "Giá đã điều chỉnh", ""),
        ("volume", "int", "shares", "Khối lượng", ""),
        ("turnover_value", "float", "VND", "close × volume", ""),
        ("quality_flag", "string", "-", "Cờ chất lượng", ""),
        (
            "split",
            "string",
            "-",
            "train | validation | test | out_of_scope (asset-level clock)",
            "train",
        ),
    ],
    "market_features": [
        ("date", "date", "YYYY-MM-DD", "Ngày giao dịch", ""),
        (
            "close",
            "float",
            "index points",
            "VN-Index đóng cửa hoặc composite",
            "1450.32",
        ),
        ("volume", "float", "shares", "Volume của index", ""),
        ("market_log_return", "float", "decimal", "ln(close_t/close_{t-1})", ""),
        ("market_simple_return", "float", "decimal", "close_t/close_{t-1}-1", ""),
        (
            "realized_vol_20d",
            "float",
            "decimal",
            "Std của log return trên rolling 20 phiên (point-in-time)",
            "0.012",
        ),
        (
            "drawdown",
            "float",
            "decimal",
            "close/rolling_max_252 - 1 (âm hoặc 0)",
            "-0.08",
        ),
        (
            "liquidity_20d",
            "float",
            "log(shares)",
            "Rolling 20-day mean của log(volume)",
            "",
        ),
        (
            "split",
            "string",
            "-",
            "train | validation | test (market-level clock)",
            "train",
        ),
        (
            "source",
            "string",
            "-",
            "Nguồn (vnstock_VCI_VNINDEX / yahoo_^VNINDEX / custom_composite_ew)",
            "",
        ),
    ],
    "eligibility_daily": [
        ("date", "date", "YYYY-MM-DD", "Ngày đánh giá", ""),
        ("ticker", "string", "-", "Mã cổ phiếu", ""),
        ("eligible_flag", "bool", "-", "True nếu đủ điều kiện tại ngày này", "True"),
        (
            "reason_code",
            "string",
            "enum",
            (
                "OK | NOT_LISTED_AT_DATE | INSUFFICIENT_HISTORY | LOW_COVERAGE | "
                "SUSPENDED_OR_NO_DATA | LOW_LIQUIDITY"
            ),
            "OK",
        ),
        (
            "sessions_available",
            "int",
            "count",
            "Số phiên có dữ liệu tính đến ngày đánh giá",
            "1250",
        ),
        (
            "coverage_pct",
            "float",
            "[0,1]",
            "sessions_available / expected_sessions_since_listing",
            "0.99",
        ),
        (
            "avg_turnover_20d",
            "float",
            "VND",
            "Rolling 20-day mean turnover, point-in-time",
            "1.2e11",
        ),
    ],
}


def write_quality_report(checks_df: pd.DataFrame, out_path: Path) -> Path:
    """Ghi Data Quality Report ra CSV (xem docstring module về lựa chọn CSV thay vì HTML)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    checks_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def write_violations(violations: pd.DataFrame, out_path: Path) -> Path:
    """Ghi danh sách vi phạm biên độ giá (DQ-007) ra CSV.

    Ghi cả khi khung rỗng — file vắng mặt phải mang nghĩa "gate chưa chạy", khác hẳn với "chạy rồi
    và không tìm thấy gì". Hai tình huống đó không được nhìn giống nhau.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    violations.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def build_data_dictionary(out_path: Path) -> Path:
    """Sinh `data_dictionary.xlsx` — 5 sheet: universe_register, prices_adjusted, returns,
    market_features, eligibility_daily. Mỗi sheet: cột `column, type, unit, description, example`.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in _DATA_DICTIONARY.items():
        ws = wb.create_sheet(sheet_name[:31])  # Excel limit 31 chars
        ws.append(["column", "type", "unit", "description", "example"])
        for row in rows:
            ws.append(list(row))
    wb.save(out_path)
    return out_path
