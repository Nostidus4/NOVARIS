# Đỗ Ngọc Tân - test validate_or_raise: pass-case trả DataFrame, fail-case raise ValueError kèm context.
import pandas as pd
import pandera.pandas as pandera
import pytest
from qshield_contracts.validate import validate_or_raise

_SCHEMA = pandera.DataFrameSchema({"x": pandera.Column(int, pandera.Check.ge(0))})


def test_validate_or_raise_pass_case() -> None:
    df = pd.DataFrame({"x": [1, 2, 3]})

    out = validate_or_raise(df, _SCHEMA, context="test")

    assert out["x"].tolist() == [1, 2, 3]


def test_validate_or_raise_fail_case_includes_context() -> None:
    df = pd.DataFrame({"x": [-1, 2]})

    with pytest.raises(ValueError, match="\\[my_module\\]"):
        validate_or_raise(df, _SCHEMA, context="my_module")
