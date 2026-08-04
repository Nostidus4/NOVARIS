# Nguyễn Anh Tú - ĐÚNG 5 feature cho HMM, không nhồi thêm.
"""5 feature đầu vào HMM: 4 cột lấy thẳng từ `market_features.parquet` (Minh Anh) + 1 cột
`mean_pairwise_corr_60d` do AI tính từ `returns.parquet`.

Quyết định AD-01 (`docs/architecture/ai-decisions-v0.2.md`): Feature Contract v0.1 bị rút — dùng
cột Data đã emit thật thay vì bắt Data tính lại 5 feature cross-sectional chưa ai sản xuất.

CLAUDE.md quy tắc 4: mọi rolling chỉ nhìn về quá khứ; `StandardScaler` fit CHỈ trên `split=="train"`.
Ngày warm-up bị loại HẲN khỏi frame — `RegimeDailySchema` không cho phép null nên không có cách nào
biểu diễn chúng thành dòng (AD-06).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

FEATURE_CONTRACT_VERSION = "v0.2"
CORR_FEATURE = "mean_pairwise_corr_60d"


def mean_pairwise_corr(
    returns: pd.DataFrame, *, tickers: Sequence[str], window: int
) -> pd.Series:
    """Trung bình tương quan cặp giữa N tài sản trên cửa sổ trượt `window` phiên.

    Chỉ dùng ngày có ĐỦ N tài sản (AD-16). Một ngày thiếu mã sẽ khiến `rolling().corr()` trả NaN
    suốt `window` ngày sau đó — trên dữ liệu thật mất 170 ngày mà không đổi lại được gì. Tương quan
    là thống kê tổng hợp point-in-time, khác luật block bootstrap (nơi TUYỆT ĐỐI không được nối hai
    phiên không liền nhau, xem `scenarios/bootstrap.py`).
    """
    wide = returns.pivot(index="date", columns="ticker", values="log_return")
    missing = [ticker for ticker in tickers if ticker not in wide.columns]
    if missing:
        raise ValueError(
            f"returns thiếu ticker {missing} — không tính được {CORR_FEATURE}."
        )
    wide = wide[list(tickers)].dropna()
    n_assets = wide.shape[1]
    if n_assets < 2:
        raise ValueError(f"Cần >= 2 tài sản để tính tương quan cặp, nhận {n_assets}.")

    rolled = wide.rolling(window, min_periods=window).corr()
    values = rolled.to_numpy().reshape(len(wide), n_assets, n_assets)
    off_diagonal = np.where(~np.eye(n_assets, dtype=bool), values, np.nan)
    counts = np.isfinite(off_diagonal).sum(axis=(1, 2))
    totals = np.nansum(off_diagonal, axis=(1, 2))
    means = np.where(counts > 0, totals / np.maximum(counts, 1), np.nan)
    return pd.Series(means, index=wide.index, name=CORR_FEATURE)


def build_feature_frame(
    market_features: pd.DataFrame,
    returns: pd.DataFrame,
    *,
    tickers: Sequence[str],
    market_columns: Sequence[str],
    corr_window: int,
) -> pd.DataFrame:
    """Ghép 4 cột market + tương quan → 1 dòng/ngày, chỉ giữ dòng đủ cả 5 feature.

    Loại `split == "out_of_scope"` (ngoài cửa sổ nghiên cứu đã khóa ở `configs/data.yaml`).
    """
    missing = [column for column in market_columns if column not in market_features]
    if missing:
        raise ValueError(
            f"market_features thiếu cột {missing} — kiểm tra configs/regime.yaml."
        )

    corr = mean_pairwise_corr(returns, tickers=tickers, window=corr_window)
    in_scope = market_features.loc[market_features["split"] != "out_of_scope"]
    joined = in_scope.set_index("date").join(corr, how="inner")

    feature_names = [*market_columns, CORR_FEATURE]
    joined = joined.dropna(subset=feature_names)
    if joined.empty:
        raise ValueError(
            "Không còn dòng nào sau khi loại warm-up — kiểm tra corr_window và độ dài dữ liệu."
        )
    return (
        joined.reset_index()[["date", "split", *feature_names]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def apply_transforms(
    frame: pd.DataFrame, transforms: Mapping[str, str]
) -> pd.DataFrame:
    """`log` cho volatility, `fisher_z` cho correlation (AD-02); cột không khai báo giữ nguyên."""
    out = frame.copy()
    for column, kind in transforms.items():
        if column not in out.columns:
            raise ValueError(f"Không có cột {column!r} để transform {kind!r}.")
        values = out[column].to_numpy(dtype=float)
        if kind == "log":
            if (values <= 0).any():
                raise ValueError(
                    f"Cột {column!r} có giá trị <= 0, không log được (min={values.min()})."
                )
            out[column] = np.log(values)
        elif kind == "fisher_z":
            if (np.abs(values) >= 1).any():
                raise ValueError(
                    f"Cột {column!r} có |giá trị| >= 1, Fisher-z phân kỳ "
                    f"(max abs={np.abs(values).max()})."
                )
            out[column] = np.arctanh(values)
        else:
            raise ValueError(f"Transform {kind!r} chưa được hỗ trợ (cột {column!r}).")
    return out


def fit_scaler(frame: pd.DataFrame, feature_names: Sequence[str]) -> StandardScaler:
    """Fit `StandardScaler` CHỈ trên dòng `split == "train"` (CLAUDE.md quy tắc 4)."""
    train = frame.loc[frame["split"] == "train", list(feature_names)]
    if train.empty:
        raise ValueError(
            "Không có dòng split=='train' để fit scaler — kiểm tra date_range trong configs/data.yaml."
        )
    return StandardScaler().fit(train.to_numpy(dtype=float))


def to_matrix(
    frame: pd.DataFrame, feature_names: Sequence[str], scaler: StandardScaler
) -> np.ndarray:
    """Ma trận `(n_rows, n_features)` đã scale — đầu vào trực tiếp của `regime/train.py`."""
    return scaler.transform(frame[list(feature_names)].to_numpy(dtype=float))
