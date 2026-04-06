from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

from services.serialization import dumps, loads


class TelemetryCollector:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir or Path(__file__).resolve().parent.parent.parent / "data" / "telemetry")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root_dir / "generation_events.jsonl"

    def record(self, event_type: str, payload: Dict[str, object]) -> None:
        record = {
            "event_type": event_type,
            "created_at": time.time(),
            **payload,
        }
        with open(self.events_path, "ab") as handle:
            handle.write(dumps(record))
            handle.write(b"\n")

    def record_generation(self, payload: Dict[str, object]) -> None:
        self.record("generation_outcome", payload)

    def load_recent(self, event_type: Optional[str] = None, limit: int = 200) -> List[Dict[str, object]]:
        if not self.events_path.exists():
            return []
        records: List[Dict[str, object]] = []
        with open(self.events_path, "rb") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = loads(line)
                except Exception:
                    continue
                if event_type and record.get("event_type") != event_type:
                    continue
                records.append(record)
        return records[-limit:]


telemetry_collector = TelemetryCollector()
