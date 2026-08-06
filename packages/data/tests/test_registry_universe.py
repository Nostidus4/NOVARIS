# Nguyễn Anh Tú - universe loader phải mang được exchange_periods sang tầng quality.
import pytest
from qshield_data.sources.registry import load_universe

_BASE_TICKER = {
    "ticker": "AAA",
    "yahoo_symbol": "AAA.VN",
    "company_name": "Test Co",
    "first_trading_date": "2020-01-01",
    "exchange_current": "HOSE",
    "exchange_history": "-",
    "exchange_periods": [{"exchange": "HOSE"}],
    "data_source": "yahoo",
    "notes": "",
}


def test_load_universe_carries_exchange_periods() -> None:
    df = load_universe({"tickers": [dict(_BASE_TICKER)]})
    assert df.loc[0, "exchange_periods"] == [{"exchange": "HOSE"}]


def test_load_universe_rejects_missing_exchange_periods() -> None:
    incomplete = dict(_BASE_TICKER)
    del incomplete["exchange_periods"]
    with pytest.raises(ValueError, match="exchange_periods"):
        load_universe({"tickers": [incomplete]})
