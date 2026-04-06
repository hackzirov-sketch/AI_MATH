from __future__ import annotations

from pathlib import Path
from time import time
from typing import Dict, List, Optional

from services.self_improvement.approval_manager import approval_manager
from services.self_improvement.failure_analyzer import failure_analyzer
from services.self_improvement.models import ImprovementReport
from services.self_improvement.proposal_generator import proposal_generator
from services.self_improvement.quality_gate import quality_gate
from services.self_improvement.rollback_manager import rollback_manager
from services.self_improvement.telemetry_collector import telemetry_collector
from services.serialization import dumps


class SelfImprovementEngine:
    def __init__(self):
        self.root_dir = Path(__file__).resolve().parent.parent.parent / "data" / "self_improvement"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_report_path = self.root_dir / "latest_runtime_report.json"

    def record_generation_outcome(
        self,
        request_payload: Dict[str, object],
        response_payload: Dict[str, object],
        trace_metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        questions = response_payload.get("questions", []) or []
        template_ids = [question.get("template_id") or question.get("type") or "general" for question in questions]
        generator_used = response_payload.get("generator_used") or (template_ids[0] if template_ids else "general")
        payload = {
            "success": bool(response_payload.get("success")),
            "subject": request_payload.get("subject"),
            "grade": request_payload.get("grade"),
            "difficulty": request_payload.get("difficulty"),
            "topic": request_payload.get("topic"),
            "topics": list({question.get("topic") or request_payload.get("topic") or "" for question in questions if question.get("topic") or request_payload.get("topic")}),
            "template_id": template_ids[0] if template_ids else "general",
            "generator_used": generator_used,
            "question_count": len(questions),
            "error_message": response_payload.get("error_message", ""),
            "sample_question": (questions[0].get("question") or questions[0].get("question_text") or "") if questions else "",
            "trace_metrics": dict(trace_metrics or {}),
        }
        telemetry_collector.record_generation(payload)

    def analyze_recent_generations(self, limit: int = 200) -> List[Dict[str, object]]:
        events = telemetry_collector.load_recent("generation_outcome", limit=limit)
        analysis = failure_analyzer.analyze(events)
        proposals = proposal_generator.generate(analysis, events)
        reports: List[Dict[str, object]] = []
        for proposal in proposals:
            scores, test_results, risk_level, recommended_action = quality_gate.evaluate(proposal, analysis)
            weakest = next((item for item in analysis.get("weakest_targets", []) if item.get("target") == proposal.target), {})
            report = ImprovementReport(
                analysis=f"So'nggi {analysis.get('total_events', 0)} generatsiya telemetrysi tahlil qilindi",
                problem_detected=proposal.problem,
                root_cause=proposal.root_cause,
                proposal=proposal,
                test_results=test_results,
                quality_scores=scores,
                risk_level=risk_level,
                recommended_action=recommended_action,
            )
            payload = report.to_dict()
            payload["analysis_details"] = {"weak_target": weakest, "coverage_gaps": analysis.get("coverage_gaps", [])}
            reports.append(payload)
            approval_manager.submit(payload)
            rollback_manager.record(payload, status=recommended_action)
        return reports

    def refresh_runtime_report(self, limit: int = 200) -> Dict[str, object]:
        events = telemetry_collector.load_recent("generation_outcome", limit=limit)
        analysis = failure_analyzer.analyze(events)
        proposals = proposal_generator.generate(analysis, events)
        top_proposal = proposals[0].to_dict() if proposals else None
        weakest_target = ""
        weakest_items = analysis.get("weakest_targets", []) or []
        if weakest_items:
            weakest_target = str(weakest_items[0].get("target", ""))
        summary = {
            "generated_at": time(),
            "event_count": len(events),
            "weakest_target": weakest_target,
            "weakest_targets": weakest_items[:5],
            "coverage_gaps": analysis.get("coverage_gaps", []),
            "failure_clusters": analysis.get("failure_clusters", []),
            "top_proposal": top_proposal,
        }
        self.runtime_report_path.write_bytes(dumps(summary))
        return summary


self_improvement_engine = SelfImprovementEngine()
