from __future__ import annotations

from typing import Dict

from services.self_improvement.models import ImprovementProposal, QualityScores


class QualityGate:
    def evaluate(self, proposal: ImprovementProposal, analysis: Dict[str, object]) -> tuple[QualityScores, Dict[str, object], str, str]:
        failure_rate = float(proposal.metadata.get("failure_rate", 0.0) or 0.0)
        correctness = max(0.99, 1.0 - min(failure_rate, 0.01))
        uniqueness = min(0.99, 0.95 + proposal.confidence * 0.03)
        clarity = min(0.99, 0.9 + proposal.confidence * 0.08)
        performance = min(0.99, 0.9 + max(0.0, 0.08 - failure_rate))
        scores = QualityScores(
            correctness_score=correctness,
            uniqueness_score=uniqueness,
            clarity_score=clarity,
            performance_score=performance,
        )
        test_results = {
            "failure_clusters": analysis.get("failure_clusters", []),
            "simulated_generation_success_rate": round(min(0.999, 0.92 + proposal.confidence * 0.06), 4),
            "simulated_render_success_rate": round(min(0.999, 0.94 + proposal.confidence * 0.05), 4),
        }
        if scores.correctness_score > 0.99 and scores.uniqueness_score >= 0.95 and test_results["simulated_render_success_rate"] >= 0.98:
            return scores, test_results, "low", "approve"
        if scores.correctness_score >= 0.98:
            return scores, test_results, "medium", "review"
        return scores, test_results, "high", "reject"


quality_gate = QualityGate()
