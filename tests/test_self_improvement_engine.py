import tempfile
import unittest
from pathlib import Path

from services.self_improvement.approval_manager import approval_manager
from services.self_improvement.engine import self_improvement_engine
from services.self_improvement.rollback_manager import rollback_manager
from services.self_improvement.telemetry_collector import telemetry_collector


class SelfImprovementEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)

        self.original_events_path = telemetry_collector.events_path
        self.original_pending_path = approval_manager.pending_path
        self.original_history_path = rollback_manager.history_path
        self.original_runtime_report_path = self_improvement_engine.runtime_report_path

        telemetry_collector.root_dir = root / "telemetry"
        telemetry_collector.root_dir.mkdir(parents=True, exist_ok=True)
        telemetry_collector.events_path = telemetry_collector.root_dir / "generation_events.jsonl"

        approval_manager.root_dir = root / "self_improvement"
        approval_manager.root_dir.mkdir(parents=True, exist_ok=True)
        approval_manager.pending_path = approval_manager.root_dir / "pending_proposals.json"

        rollback_manager.root_dir = approval_manager.root_dir
        rollback_manager.history_path = rollback_manager.root_dir / "proposal_history.json"
        self_improvement_engine.root_dir = approval_manager.root_dir
        self_improvement_engine.runtime_report_path = self_improvement_engine.root_dir / "latest_runtime_report.json"

    def tearDown(self):
        telemetry_collector.events_path = self.original_events_path
        approval_manager.pending_path = self.original_pending_path
        rollback_manager.history_path = self.original_history_path
        self_improvement_engine.runtime_report_path = self.original_runtime_report_path
        self.temp_dir.cleanup()

    def test_analyze_recent_generations_creates_proposals(self):
        for _ in range(3):
            telemetry_collector.record_generation(
                {
                    "success": False,
                    "subject": "matematika",
                    "grade": 6,
                    "difficulty": "o'rta",
                    "topic": "Kasrlar",
                    "topics": ["Kasrlar"],
                    "template_id": "vertical_arithmetic_v1",
                    "generator_used": "topic",
                    "question_count": 0,
                    "error_message": "duplicate distractors detected",
                    "sample_question": "Kasrlarni taqqoslang.",
                }
            )

        reports = self_improvement_engine.analyze_recent_generations(limit=10)

        self.assertTrue(reports)
        self.assertIn("proposal", reports[0])
        self.assertTrue(approval_manager.pending_path.exists())
        self.assertTrue(rollback_manager.history_path.exists())

    def test_refresh_runtime_report_writes_latest_summary(self):
        telemetry_collector.record_generation(
            {
                "success": False,
                "subject": "matematika",
                "grade": 6,
                "difficulty": "qiyin",
                "topic": "Kvadrat ildiz",
                "topics": ["Kvadrat ildiz"],
                "template_id": "channel_quiz_generation",
                "generator_used": "channel_quiz_generation",
                "question_count": 0,
                "error_message": "duplicate_blocked:semantic_match:16 ning kvadrat ildizini toping",
                "sample_question": "",
            }
        )

        summary = self_improvement_engine.refresh_runtime_report(limit=10)

        self.assertIn("event_count", summary)
        self.assertTrue(self_improvement_engine.runtime_report_path.exists())


if __name__ == "__main__":
    unittest.main()
