from pathlib import Path

import pandas as pd
from qshield_data.loader import load_data


def test_universe_loader_prefers_workflow_update_snapshot(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    pd.DataFrame({"ticker": ["LEGACY"]}).to_csv(
        metadata / "universe_asof_20260803.csv", index=False
    )
    pd.DataFrame({"ticker": ["VN30"]}).to_csv(
        metadata / "universe_30_asof_20260803.csv", index=False
    )

    result = load_data("universe", data_root=tmp_path)

    assert result["ticker"].tolist() == ["VN30"]
