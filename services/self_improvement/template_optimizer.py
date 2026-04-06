from __future__ import annotations

import re
from typing import Dict, List

from services.self_improvement.models import ImprovementProposal


class TemplateOptimizer:
    def build_proposals(self, analysis: Dict[str, object]) -> List[ImprovementProposal]:
        proposals: List[ImprovementProposal] = []
        for item in analysis.get("weakest_targets", [])[:3]:
            failure_rate = float(item.get("failure_rate", 0.0))
            target = str(item.get("target", "general"))
            if failure_rate <= 0.05:
                continue
            proposals.append(
                ImprovementProposal(
                    type="template_update",
                    target=target,
                    problem=f"{target} yo'nalishida failure rate yuqori",
                    root_cause="Template constraintlari va distractor qoidalari yetarlicha qattiq emas",
                    solution="Versioned template chiqarib, range constraint, topic lock va distractor quality filter qo'shilsin",
                    confidence=min(0.99, 0.65 + failure_rate),
                    version=self._next_version(target),
                    metadata={"failure_rate": failure_rate, "failures": item.get("failures", 0)},
                )
            )
        return proposals

    def _next_version(self, target: str) -> str:
        match = re.search(r"_v(\d+)$", target)
        if not match:
            return f"{target}_v2"
        current = int(match.group(1))
        return re.sub(r"_v\d+$", f"_v{current + 1}", target)


template_optimizer = TemplateOptimizer()
