# Nguyễn Đỗ Minh Anh - loader dữ liệu giá/khối lượng từ DNSE/Entrade — nguồn multi-exchange.
"""DNSE/Entrade OHLC API loader — port từ `CLEAN.ipynb` (hàm `download_ticker_dnse`).

Public API, không cần auth, có full history HNX/UPCOM (Yahoo chỉ có HOSE). Endpoint:
`https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from={epoch}&to={epoch}&symbol={ticker}&resolution=1D`

Giá trả về theo NGHÌN VNĐ → nhân 1000 để có VNĐ đầy đủ (tương thích Yahoo). API không cung cấp
field adjusted riêng; bản demo giữ proxy ``Adj Close = Close`` nhưng gắn metadata/warning
``ADJ_UNVERIFIED``. Không được dùng proxy này làm bằng chứng baseline (TL-002).

`verify=False`: máy phát triển gốc (Windows) thiếu root CA cho `entrade.com.vn`, khiến request luôn
báo `SSLError` và fallback nhầm về Yahoo — mất hết history trước ngày chuyển sang HOSE. Xác định
bằng cell diagnostic trong `CLEAN.ipynb` (test trực tiếp với `verify=False` thành công).
"""

from __future__ import annotations

import logging
import time
import warnings

import pandas as pd
import requests
import urllib3

logger = logging.getLogger(__name__)

_URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def download_ticker(
    ticker: str, start: str, end: str, max_retries: int = 3
) -> tuple[pd.DataFrame | None, str | None]:
    """Tải giá 1 mã từ DNSE/Entrade, có retry + backoff.

    Trả về `(df, "dnse_entrade")` nếu thành công, `(None, None)` nếu fail sau `max_retries` lần.
    """
    start_epoch = int(pd.Timestamp(start).timestamp())
    end_epoch = int(pd.Timestamp(end).timestamp())
    url = f"{_URL}?from={start_epoch}&to={end_epoch}&symbol={ticker}&resolution=1D"

    for attempt in range(max_retries):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "ignore", urllib3.exceptions.InsecureRequestWarning
                )
                r = requests.get(url, headers=_HEADERS, timeout=30, verify=False)
            r.raise_for_status()
            data = r.json()
            # DNSE API v2 không trả field "s" — chỉ check "t" đủ rồi (request fail thì
            # raise_for_status() ở trên đã raise Exception).
            if not data.get("t"):
                return None, None

            df = pd.DataFrame(
                {
                    "date": pd.to_datetime(data["t"], unit="s")
                    .tz_localize(None)
                    .normalize(),
                    "Open": [x * 1000 for x in data["o"]],
                    "High": [x * 1000 for x in data["h"]],
                    "Low": [x * 1000 for x in data["l"]],
                    "Close": [x * 1000 for x in data["c"]],
                    "Volume": data["v"],
                }
            )
            df = df.set_index("date").sort_index()
            logger.warning(
                "DNSE %s không có field adjusted riêng: dùng Close làm proxy Adj Close với "
                "flag ADJ_UNVERIFIED; không hợp lệ cho baseline TL-002.",
                ticker,
            )
            df["Adj Close"] = df["Close"]
            df.attrs["adjusted_close_method"] = "CLOSE_PROXY_UNVERIFIED"
            df.attrs["adjusted_close_evidence"] = "ADJ_UNVERIFIED"
            df = df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
            return df, "dnse_entrade"

        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            if attempt == max_retries - 1:
                logger.warning(
                    "DNSE %s failed after %d attempts: %s: %s",
                    ticker,
                    max_retries,
                    type(e).__name__,
                    str(e)[:100],
                )
                return None, None
            time.sleep(3 * (attempt + 1))
    return None, None
