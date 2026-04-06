from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from services.serialization import dumps, loads


class RollbackManager:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir or Path(__file__).resolve().parent.parent.parent / "data" / "self_improvement")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.root_dir / "proposal_history.json"

    def record(self, report: Dict[str, object], status: str) -> None:
        history = self.load_history()
        history.append({"status": status, **report})
        self.history_path.write_bytes(dumps(history))

    def load_history(self) -> List[Dict[str, object]]:
        if not self.history_path.exists():
            return []
        try:
            return list(loads(self.history_path.read_bytes()) or [])
        except Exception:
            return []


rollback_manager = RollbackManager()
