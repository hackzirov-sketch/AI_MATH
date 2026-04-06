from __future__ import annotations

import sys

from services.bootstrap import bootstrap_runtime, bootstrap_state


def main() -> int:
    bootstrap_runtime()
    command = (sys.argv[1] if len(sys.argv) > 1 else "init-db").strip().lower()

    if command == "init-db":
        bootstrap_state()
        return 0

    if command == "cleanup-cache":
        bootstrap_state()
        from services.cache_manager import cache_manager

        reports = cache_manager.cleanup_all()
        for name, report in reports.items():
            print(name, report.to_dict())
        return 0

    if command == "analyze-quality":
        bootstrap_state()
        from services.self_improvement.engine import self_improvement_engine

        reports = self_improvement_engine.analyze_recent_generations(limit=100)
        print({"reports": len(reports)})
        return 0

    print(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
