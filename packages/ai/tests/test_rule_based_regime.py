# Nguyễn Anh Tú - test fallback: ngưỡng lấy từ TRAIN, không có cột xác suất nào được sinh ra.
import pandas as pd
import pytest
from qshield_ai.baseline.rule_based_regime import rule_based_labels


def _frame() -> pd.DataFrame:
    """Train có volatility [1,2,3,4,5] ⇒ phân vị 0.8 (nội suy tuyến tính) = 4.2."""
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=8),
            "split": ["train"] * 5 + ["test"] * 3,
            "realized_vol_20d": [1.0, 2.0, 3.0, 4.0, 5.0, 5.0, 5.0, 3.0],
            "drawdown": [-0.01] * 5 + [-0.20, -0.05, -0.30],
        }
    )


def _labels() -> pd.DataFrame:
    return rule_based_labels(
        _frame(),
        volatility_column="realized_vol_20d",
        drawdown_column="drawdown",
        vol_quantile=0.8,
        drawdown_threshold=-0.10,
    )


def test_high_volatility_and_deep_drawdown_is_stress() -> None:
    """vol 5.0 >= 4.2 và drawdown -0.20 <= -0.10 ⇒ stress."""
    assert _labels().iloc[5]["regime"] == "stress"


def test_high_volatility_with_shallow_drawdown_is_volatile() -> None:
    """vol 5.0 >= 4.2 nhưng drawdown -0.05 > -0.10 ⇒ chỉ volatile."""
    assert _labels().iloc[6]["regime"] == "volatile"


def test_low_volatility_is_normal_even_with_deep_drawdown() -> None:
    """vol 3.0 < 4.2 ⇒ normal, dù drawdown -0.30 rất sâu — luật lấy volatility làm cổng đầu."""
    assert _labels().iloc[7]["regime"] == "normal"


def test_threshold_comes_from_train_rows_only() -> None:
    """Thêm ngày TEST volatility cực lớn không được làm đổi ngưỡng (quy tắc 4).

    Phải thêm BA outlier, không phải một. Với một outlier, phân vị 0.8 trên toàn khung là
    đúng 5.0, mà `5.0 >= 5.0` vẫn True — nhãn không đổi kể cả khi bỏ lọc train, nên test
    không phân biệt được đúng/sai. Với ba outlier, ngưỡng toàn khung nhảy lên 1000.0 và hai
    dòng vol=5.0 sẽ tụt từ stress/volatile xuống normal. Chỉ khi đó test mới thật sự chứng
    minh được ngưỡng học từ train:
        train  [1,2,3,4,5]                      → phân vị 0.8 = 4.2   (vol 5.0 là cao)
        toàn   [1,2,3,4,5,5,5,3,1000,1000,1000] → phân vị 0.8 = 1000  (vol 5.0 KHÔNG cao)
    """
    frame = _frame()
    baseline = _labels()["regime"].tolist()

    for day in ("2024-01-15", "2024-01-16", "2024-01-17"):
        frame.loc[len(frame)] = {
            "date": pd.Timestamp(day),
            "split": "test",
            "realized_vol_20d": 1000.0,
            "drawdown": -0.5,
        }
    shifted = rule_based_labels(
        frame,
        volatility_column="realized_vol_20d",
        drawdown_column="drawdown",
        vol_quantile=0.8,
        drawdown_threshold=-0.10,
    )
    assert shifted["regime"].tolist()[:8] == baseline


def test_output_has_no_probability_columns() -> None:
    """AD-07: fallback KHÔNG được sinh ra bất kỳ cột xác suất nào."""
    columns = set(_labels().columns)
    assert columns == {"date", "regime", "rule_fired", "method"}
    assert not any(column.startswith("prob") for column in columns)


def test_method_column_is_constant() -> None:
    assert set(_labels()["method"]) == {"rule_based"}


def test_rule_fired_explains_each_row() -> None:
    labels = _labels()
    assert labels.iloc[5]["rule_fired"] == "vol>=q AND drawdown<=threshold"
    assert labels.iloc[6]["rule_fired"] == "vol>=q"
    assert labels.iloc[7]["rule_fired"] == "default"


def test_missing_train_rows_raise() -> None:
    frame = _frame()
    frame["split"] = "test"
    with pytest.raises(ValueError, match="train"):
        rule_based_labels(
            frame,
            volatility_column="realized_vol_20d",
            drawdown_column="drawdown",
            vol_quantile=0.8,
            drawdown_threshold=-0.10,
        )
