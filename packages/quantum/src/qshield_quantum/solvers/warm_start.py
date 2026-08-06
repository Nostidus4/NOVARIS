# Đỗ Ngọc Tân - optional warm-start QAOA for the generic workflow branch.
"""Construct Qiskit's continuous-relaxation warm-start wrapper when available."""

from __future__ import annotations

from typing import Any

from qiskit_algorithms import QAOA


def make_warm_start_optimizer(qaoa: QAOA) -> Any | None:
    """Return a p=1-compatible warm-start optimizer, or ``None`` on unsupported installs."""
    try:
        from qiskit_optimization.algorithms import (
            SlsqpOptimizer,
            WarmStartQAOAOptimizer,
        )
    except ImportError:
        return None
    return WarmStartQAOAOptimizer(
        pre_solver=SlsqpOptimizer(),
        relax_for_pre_solver=True,
        qaoa=qaoa,
        epsilon=0.25,
        num_initial_solutions=1,
    )
