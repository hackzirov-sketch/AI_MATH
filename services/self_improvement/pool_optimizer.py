from __future__ import annotations

from typing import Dict, List

from services.self_improvement.models import ImprovementProposal


class PoolOptimizer:
    def build_proposals(self, analysis: Dict[str, object]) -> List[ImprovementProposal]:
        proposals: List[ImprovementProposal] = []
        for topic in analysis.get("coverage_gaps", [])[:2]:
            proposals.append(
                ImprovementProposal(
                    type="pool_extension",
                    target=str(topic),
                    problem=f"{topic} mavzusida coverage past",
                    root_cause="Question pool va variation oralig'i kam ishlatilgan",
                    solution="Shu mavzu uchun yangi template family va qo'shimcha example-driven variantlar tayyorlansin",
                    confidence=0.78,
                    version=f"{topic}_pool_v2",
                    metadata={"topic": topic},
                )
            )
        return proposals


pool_optimizer = PoolOptimizer()
