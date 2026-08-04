# Nguyễn Anh Tú - regime-conditioned moving-block bootstrap, block 5 → 20 ngày; lấy nguyên vector 8 tài sản mỗi ngày, không bootstrap độc lập từng mã.
"""Moving-block bootstrap điều kiện hóa theo regime, generic `(S, H, N)`.

Luật bất di bất dịch: MỘT NGÀY KỊCH BẢN LÀ NGUYÊN VECTOR N TÀI SẢN của một phiên lịch sử. Bootstrap
từng mã độc lập sẽ phá tương quan chéo và làm CVaR sai mà không schema nào bắt được
(`docs/runbook/troubleshooting.md` §4).

Vị trí block là CHỈ SỐ TRÊN LỊCH PHIÊN (AD-11), nên tính liền mạch là cấu trúc: một block không thể
nối qua khoảng trống vì khoảng trống không phải một vị trí trên lịch. Ngày thiếu mã bị loại như
"absent asset" — loại CẢ block, không rút ngắn, không bỏ mã.

Neo (DR §Anchor semantics): nhãn filtered tại `d`, block là `[d+1 .. d+block_length]`, và
`d+block_length <= t`. Block bắt đầu từ `d+1` để không điều kiện hóa lên chính quan sát đã tạo ra
suy luận trạng thái tại `d`. KHÔNG đòi các ngày trong block cũng cùng regime — làm vậy là điều kiện
hóa lên tính dai dẳng của regime và đổi luôn phân phối mục tiêu.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ReturnPanel:
    """Bảng log return `(T, N)` khớp lịch phiên. `complete[t]` = ngày `t` có đủ N mã."""

    dates: tuple[pd.Timestamp, ...]
    log_returns: np.ndarray
    complete: np.ndarray
    tickers: tuple[str, ...]


@dataclass(frozen=True)
class BlockPool:
    """Tập block hợp lệ cho một regime mục tiêu, kèm lý do loại để ghi vào manifest."""

    target_regime: str
    block_starts: np.ndarray
    anchor_dates: tuple[pd.Timestamp, ...]
    eligible_block_count: int
    rejected: dict[str, int]
    anchor_split_counts: dict[str, int]


def build_return_panel(
    returns: pd.DataFrame, calendar: Sequence[pd.Timestamp], *, tickers: Sequence[str]
) -> ReturnPanel:
    """Dựng panel theo ĐÚNG thứ tự `tickers` trong config — Risk map theo ticker, không theo vị
    trí."""
    wide = returns.pivot(index="date", columns="ticker", values="log_return")
    missing = [ticker for ticker in tickers if ticker not in wide.columns]
    if missing:
        raise ValueError(f"returns thiếu ticker {missing} — không dựng được panel.")

    index = pd.DatetimeIndex(pd.to_datetime(list(calendar)))
    aligned = wide[list(tickers)].reindex(index)
    values = aligned.to_numpy(dtype=float)
    return ReturnPanel(
        dates=tuple(index),
        log_returns=values,
        complete=np.isfinite(values).all(axis=1),
        tickers=tuple(tickers),
    )


def resolve_evaluation_date(
    regime_daily: pd.DataFrame, panel: ReturnPanel, *, configured: Any | None
) -> pd.Timestamp:
    """AD-09: `null` ⇒ ngày cuối vừa có nhãn regime vừa có đủ N mã. Ngày ghim phải thỏa cả hai."""
    labelled = set(pd.to_datetime(regime_daily["date"]))
    usable = [
        date
        for position, date in enumerate(panel.dates)
        if panel.complete[position] and date in labelled
    ]
    if not usable:
        raise ValueError(
            "Không có ngày nào vừa có nhãn regime vừa đủ N mã — không chọn được ngày đánh giá t."
        )
    if configured is None:
        return usable[-1]

    chosen = pd.Timestamp(configured)
    if chosen not in set(usable):
        raise ValueError(
            f"evaluation_date={chosen.date()} không có nhãn regime hoặc không đủ N mã "
            f"(khoảng dùng được: {usable[0].date()} → {usable[-1].date()})."
        )
    return chosen


def build_block_pool(
    panel: ReturnPanel,
    regime_daily: pd.DataFrame,
    *,
    target_regime: str,
    block_length: int,
    evaluation_date: pd.Timestamp,
) -> BlockPool:
    """Danh sách block hợp lệ + đếm lý do loại (SCN-OD-02: pool scarcity phải ghi lại)."""
    if block_length < 1:
        raise ValueError(f"block_length phải >= 1, nhận {block_length}.")
    position_of = {date: index for index, date in enumerate(panel.dates)}
    last_allowed = position_of.get(pd.Timestamp(evaluation_date))
    if last_allowed is None:
        raise ValueError(
            f"evaluation_date={pd.Timestamp(evaluation_date).date()} không nằm trên lịch phiên."
        )

    anchors = regime_daily.loc[regime_daily["regime"] == target_regime]
    has_split = "split" in anchors.columns
    starts: list[int] = []
    anchor_dates: list[pd.Timestamp] = []
    split_counts: dict[str, int] = {}
    rejected = {
        "anchor_off_calendar": 0,
        "beyond_evaluation_date": 0,
        "incomplete_panel": 0,
    }

    for row in anchors.itertuples(index=False):
        anchor_position = position_of.get(pd.Timestamp(row.date))
        if anchor_position is None:
            rejected["anchor_off_calendar"] += 1
            continue
        start = anchor_position + 1
        end = start + block_length - 1
        if end > last_allowed:
            rejected["beyond_evaluation_date"] += 1
            continue
        if not panel.complete[start : end + 1].all():
            rejected["incomplete_panel"] += 1
            continue
        starts.append(start)
        anchor_dates.append(pd.Timestamp(row.date))
        if has_split:
            key = str(row.split)
            split_counts[key] = split_counts.get(key, 0) + 1

    return BlockPool(
        target_regime=target_regime,
        block_starts=np.asarray(starts, dtype=int),
        anchor_dates=tuple(anchor_dates),
        eligible_block_count=len(starts),
        rejected=rejected,
        anchor_split_counts=split_counts,
    )


def generate_cube(
    panel: ReturnPanel,
    pool: BlockPool,
    *,
    num_scenarios: int,
    horizon_days: int,
    block_length: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """`(cube_simple, cube_log, metadata)` — mỗi kịch bản là `horizon/block` block nối lại."""
    if horizon_days % block_length != 0:
        raise ValueError(
            f"horizon_days={horizon_days} phải chia hết cho block_length={block_length}."
        )
    if pool.eligible_block_count == 0:
        raise ValueError(
            f"Pool block cho regime {pool.target_regime!r} rỗng — không sinh được kịch bản. "
            f"Lý do loại: {pool.rejected}."
        )
    if num_scenarios < 1:
        raise ValueError(f"num_scenarios phải >= 1, nhận {num_scenarios}.")

    blocks_per_path = horizon_days // block_length
    rng = np.random.default_rng(seed)
    drawn = rng.integers(
        0, pool.eligible_block_count, size=(num_scenarios, blocks_per_path)
    )
    starts = pool.block_starts[drawn]  # (S, blocks_per_path)

    offsets = np.arange(block_length)
    positions = (starts[:, :, None] + offsets[None, None, :]).reshape(
        num_scenarios, horizon_days
    )
    cube_log = panel.log_returns[positions]  # (S, H, N)
    cube_simple = np.expm1(cube_log)

    if not np.isfinite(cube_log).all():
        raise ValueError(
            "Cube chứa NaN/Inf dù mọi block đã qua kiểm tra đủ N mã — kiểm tra lại panel."
        )

    total_draws = int(drawn.size)
    unique_blocks = len(np.unique(drawn))
    metadata = {
        "target_regime": pool.target_regime,
        "seed": int(seed),
        "block_length": int(block_length),
        "blocks_per_path": int(blocks_per_path),
        "num_scenarios": int(num_scenarios),
        "horizon_days": int(horizon_days),
        "n_assets": int(panel.log_returns.shape[1]),
        "ticker_order": list(panel.tickers),
        "eligible_block_count": int(pool.eligible_block_count),
        "blocks_drawn": total_draws,
        "unique_blocks_used": unique_blocks,
        "reuse_rate": float(1.0 - unique_blocks / total_draws),
        "rejected_blocks": dict(pool.rejected),
        "anchor_split_counts": dict(pool.anchor_split_counts),
        "anchor_first": str(pool.anchor_dates[0].date()) if pool.anchor_dates else None,
        "anchor_last": str(pool.anchor_dates[-1].date()) if pool.anchor_dates else None,
        "return_type": "simple",
    }
    return cube_simple, cube_log, metadata
