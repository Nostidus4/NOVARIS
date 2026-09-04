# Nguyễn Anh Tú - test mọi key config mà packages/ai đọc đều tồn tại và đúng kiểu.
from pathlib import Path

import pytest
import yaml
from qshield_contracts.config import Config

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "base.yaml"


@pytest.fixture(scope="module")
def config() -> Config:
    return Config.load(CONFIG_PATH)


def test_global_seed_is_registered(config: Config) -> None:
    assert isinstance(config["seed"], int)


def test_regime_feature_keys(config: Config) -> None:
    features = config["features"]
    assert features["market_columns"] == [
        "market_log_return",
        "realized_vol_20d",
        "drawdown",
        "liquidity_20d",
    ]
    assert features["corr_window"] == 60
    assert config["feature_contract_version"] == "v0.2"


def test_regime_seeds_match_declared_count(config: Config) -> None:
    seeds = config["seeds"]
    assert len(seeds["values"]) == seeds["count"] == 10
    assert len(set(seeds["values"])) == 10, "seed trùng nhau là lỗi đăng ký"


def test_champion_is_inside_candidate_grid(config: Config) -> None:
    """Champion ghim ở 3/diag nhưng vẫn phải là một điểm trong lưới được báo cáo."""
    champion, candidates = config["champion"], config["candidates"]
    assert champion["n_states"] in candidates["n_states"]
    assert champion["covariance_type"] in candidates["covariance_type"]
    assert champion["n_states"] == 3, "RegimeDailySchema chặn state_id ở {0,1,2}"


def test_gate_min_mean_label_agreement_is_above_chance_level(config: Config) -> None:
    """Với 3 nhãn, đồng thuận ngẫu nhiên ~0.33 — ngưỡng cổng phải cao hơn hẳn mức đó, nếu không
    cổng không lọc được gì (xem selection.py AD-04)."""
    threshold = config["gate"]["min_mean_label_agreement"]
    assert isinstance(threshold, float)
    assert threshold > 1 / 3


def test_transforms_reference_real_features(config: Config) -> None:
    known = {*config["features"]["market_columns"], "mean_pairwise_corr_60d"}
    assert set(config["transforms"]) <= known


def test_scenario_seed_is_not_shadowed_by_base(config: Config) -> None:
    """`configs/scenarios.yaml` đã bị gộp thẳng vào `configs/base.yaml` (không còn `includes:`
    riêng cho scenario) — nguồn đọc thô đổi theo, nhưng mục đích test giữ nguyên: `scenario_seed`
    phải là một khóa TÁCH BIỆT khỏi `seed` toàn cục, và giá trị `Config` trả về phải đúng bằng
    giá trị khai báo thô trong yaml — không bị `seed` toàn cục ghi đè một cách âm thầm.

    Trước đây rủi ro nằm ở thứ tự merge include (key của `base.yaml` đè mọi include). Bây giờ
    toàn bộ nằm trong một file phẳng nên rủi ro đó không còn ở dạng cũ, nhưng vẫn đáng giữ làm
    regression guard: nếu ai đó gộp `scenario_seed` và `seed` thành một khóa, hay lỡ xóa
    `scenario_seed` và để code rơi về `seed` toàn cục, test này phải đỏ.

    NGOẠI LỆ CÓ CHỦ Ý với quy tắc "`Config` là nơi DUY NHẤT được `yaml.safe_load` trên
    `configs/*.yaml`" (`qshield_contracts.config`): bản đọc thô này chỉ dùng để đối chiếu với
    giá trị `Config` trả về, không giá trị nào từ đây được đưa vào code. Không nhân bản pattern
    này ra ngoài test: mọi nơi khác vẫn phải đi qua `Config`.
    """
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert "scenario_seed" in raw, (
        "khóa `scenario_seed` phải tồn tại độc lập trong base.yaml"
    )
    assert "seed" in raw, (
        "khóa `seed` toàn cục phải vẫn tồn tại tách biệt với `scenario_seed`"
    )
    assert config["scenario_seed"] == raw["scenario_seed"], (
        "Config trả về scenario_seed khác giá trị khai báo thô trong base.yaml — nghi ngờ bị "
        "`seed` toàn cục ghi đè trong lúc merge"
    )
    assert isinstance(config["scenario_seed"], int)


def test_scenario_keys(config: Config) -> None:
    assert config["num_scenarios"] == 5000
    assert config["horizon_days"] == 20
    assert config["block_length"] == 5
    assert "evaluation_date" in config
    thresholds = config["validation"]["thresholds"]
    assert thresholds["std_ratio_min"] < thresholds["std_ratio_max"]
    assert thresholds["tail_coverage_ratio_min"] < thresholds["tail_coverage_ratio_max"]
    min_reference_windows = config["validation"]["min_reference_windows"]
    assert isinstance(min_reference_windows, int)
    assert min_reference_windows > 0
