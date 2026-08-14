"""Q-SHIELD Risk Engine public API."""

from qshield_risk.candidate_gate import CandidateGateResult, evaluate_candidate_gate
from qshield_risk.candidates import candidate_order, select_four_level_candidates
from qshield_risk.evaluate import RiskEvaluation, evaluate
from qshield_risk.metrics import TailUncertainty
from qshield_risk.objective import FinancialObjective, financial_objective
from qshield_risk.policy import ConstraintViolation, RiskPolicy
from qshield_risk.rerank import (
    PolishingResult,
    build_financial_baselines,
    polish_reductions,
    rerank_candidates,
)
from qshield_risk.sampling import (
    ObjectiveSampleDataset,
    decode_four_level_bits,
    sample_objective,
    sample_objective_dataset,
    structured_bit_vectors,
)

__all__ = [
    "CandidateGateResult",
    "ConstraintViolation",
    "FinancialObjective",
    "ObjectiveSampleDataset",
    "PolishingResult",
    "RiskEvaluation",
    "RiskPolicy",
    "TailUncertainty",
    "build_financial_baselines",
    "candidate_order",
    "decode_four_level_bits",
    "evaluate",
    "evaluate_candidate_gate",
    "financial_objective",
    "polish_reductions",
    "rerank_candidates",
    "sample_objective",
    "sample_objective_dataset",
    "select_four_level_candidates",
    "structured_bit_vectors",
]
