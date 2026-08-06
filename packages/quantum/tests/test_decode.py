# Đỗ Ngọc Tân - decode: tổng tỷ trọng luôn = 1.0 (CLAUDE.md quy tắc 6), đúng mã bị chọn.
import pytest
from qshield_quantum.decode import chosen_action_ids, chosen_tickers, decode


def test_chosen_action_ids_and_tickers() -> None:
    bitstring = "10100000"
    tickers = ["ACB", "CTG", "VCB", "HPG", "VIC", "MWG", "VNM", "FPT"]
    assert chosen_action_ids(bitstring) == [0, 2]
    assert chosen_tickers(bitstring, tickers) == ["ACB", "VCB"]


def test_decode_reduces_chosen_tickers_by_reduction_pct_and_sums_to_one() -> None:
    tickers = ["ACB", "CTG", "VCB"]
    weights = {"ACB": 0.4, "CTG": 0.3, "VCB": 0.3}
    bitstring = "101"  # chọn ACB, VCB

    new_weights = decode(bitstring, tickers, weights, reduction_pct=0.2)

    assert new_weights["ACB"] == pytest.approx(0.4 * 0.8)
    assert new_weights["VCB"] == pytest.approx(0.3 * 0.8)
    assert new_weights["CTG"] == pytest.approx(0.3)  # không bị chọn, giữ nguyên
    assert new_weights["cash"] == pytest.approx(0.4 * 0.2 + 0.3 * 0.2)
    assert sum(new_weights.values()) == pytest.approx(1.0)


def test_decode_no_action_keeps_weights_unchanged_plus_zero_cash() -> None:
    tickers = ["ACB", "CTG"]
    weights = {"ACB": 0.5, "CTG": 0.5}
    new_weights = decode("00", tickers, weights, reduction_pct=0.2)
    assert new_weights == {"ACB": 0.5, "CTG": 0.5, "cash": 0.0}


def test_decode_raises_on_length_mismatch() -> None:
    with pytest.raises(ValueError, match="dài"):
        decode("101", ["ACB", "CTG"], {"ACB": 0.5, "CTG": 0.5}, reduction_pct=0.2)
