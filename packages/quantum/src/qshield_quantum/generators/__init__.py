# Đỗ Ngọc Tân - bộ sinh ứng viên theo nguồn cho thí nghiệm QAOA-assisted (docs/hybrid/2026-09-13-plan-qaoa-assisted.md).
"""Candidate generators — mỗi nguồn sinh pool RIÊNG, không bao giờ trộn nghiệm exact.

Mọi generator chỉ thấy QUBO surrogate + predicate feasibility (cùng thông tin với QAOA), trừ
`classical_true` nằm ở `qshield_risk.hybrid` vì nó cần true objective.
"""
