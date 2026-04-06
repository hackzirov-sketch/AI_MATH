from __future__ import annotations

from typing import Dict, List

from services.self_improvement.models import ImprovementProposal
from services.self_improvement.pool_optimizer import pool_optimizer
from services.self_improvement.prompt_optimizer import prompt_optimizer
from services.self_improvement.template_optimizer import template_optimizer


class ProposalGenerator:
    def generate(self, analysis: Dict[str, object], events: List[Dict[str, object]]) -> List[ImprovementProposal]:
        proposals: List[ImprovementProposal] = []
        proposals.extend(template_optimizer.build_proposals(analysis))
        proposals.extend(pool_optimizer.build_proposals(analysis))
        proposals.extend(prompt_optimizer.build_proposals(events))
        proposals.sort(key=lambda item: item.confidence, reverse=True)
        return proposals[:5]


proposal_generator = ProposalGenerator()
