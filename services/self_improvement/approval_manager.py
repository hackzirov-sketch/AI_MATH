from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from services.serialization import dumps, loads


class ApprovalManager:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir or Path(__file__).resolve().parent.parent.parent / "data" / "self_improvement")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.pending_path = self.root_dir / "pending_proposals.json"

    def submit(self, report: Dict[str, object]) -> None:
        proposals = self.load_pending()
        proposals.append(report)
        self.pending_path.write_bytes(dumps(proposals))

    def load_pending(self) -> List[Dict[str, object]]:
        if not self.pending_path.exists():
            return []
        try:
            return list(loads(self.pending_path.read_bytes()) or [])
        except Exception:
            return []


approval_manager = ApprovalManager()
