from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ImprovementProposal:
    type: str
    target: str
    problem: str
    root_cause: str
    solution: str
    confidence: float
    version: str
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type,
            "target": self.target,
            "problem": self.problem,
            "root_cause": self.root_cause,
            "solution": self.solution,
            "confidence": self.confidence,
            "version": self.version,
            "metadata": dict(self.metadata),
        }


@dataclass
class QualityScores:
    correctness_score: float
    uniqueness_score: float
    clarity_score: float
    performance_score: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "correctness_score": round(self.correctness_score, 4),
            "uniqueness_score": round(self.uniqueness_score, 4),
            "clarity_score": round(self.clarity_score, 4),
            "performance_score": round(self.performance_score, 4),
        }


@dataclass
class ImprovementReport:
    analysis: str
    problem_detected: str
    root_cause: str
    proposal: ImprovementProposal
    test_results: Dict[str, object]
    quality_scores: QualityScores
    risk_level: str
    recommended_action: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "analysis": self.analysis,
            "problem_detected": self.problem_detected,
            "root_cause": self.root_cause,
            "proposal": self.proposal.to_dict(),
            "test_results": dict(self.test_results),
            "quality_scores": self.quality_scores.to_dict(),
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
        }
