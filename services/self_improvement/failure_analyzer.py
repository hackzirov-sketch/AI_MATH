from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:
    KMeans = None
    TfidfVectorizer = None


class FailureAnalyzer:
    def analyze(self, events: List[Dict[str, object]]) -> Dict[str, object]:
        targets = Counter()
        failures = Counter()
        prompts: List[str] = []
        coverage = Counter()
        for event in events:
            target = str(event.get("template_id") or event.get("generator_used") or event.get("subject") or "general")
            targets[target] += 1
            if not event.get("success", False):
                failures[target] += 1
            for topic in event.get("topics", []) or []:
                coverage[str(topic)] += 1
            if event.get("error_message"):
                prompts.append(str(event["error_message"]))
        weakest = []
        for target, total in targets.most_common():
            failure_rate = failures[target] / max(total, 1)
            weakest.append(
                {
                    "target": target,
                    "total": total,
                    "failures": failures[target],
                    "failure_rate": round(failure_rate, 4),
                }
            )
        weakest.sort(key=lambda item: (item["failure_rate"], item["failures"], item["total"]), reverse=True)
        return {
            "total_events": len(events),
            "weakest_targets": weakest[:5],
            "coverage_gaps": [topic for topic, count in coverage.items() if count <= 1][:5],
            "failure_clusters": self._cluster_failures(prompts),
        }

    def _cluster_failures(self, prompts: List[str]) -> List[Dict[str, object]]:
        unique_prompts: List[str] = []
        for prompt in prompts:
            if not prompt:
                continue
            if any(self._similar(existing, prompt) >= 90 for existing in unique_prompts):
                continue
            unique_prompts.append(prompt)
        if not unique_prompts:
            return []
        if KMeans is not None and TfidfVectorizer is not None and len(unique_prompts) >= 3:
            vectorizer = TfidfVectorizer(max_features=64)
            matrix = vectorizer.fit_transform(unique_prompts)
            cluster_count = min(3, len(unique_prompts))
            model = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
            labels = model.fit_predict(matrix)
            grouped = defaultdict(list)
            for label, prompt in zip(labels, unique_prompts):
                grouped[int(label)].append(prompt)
            return [
                {
                    "cluster_id": cluster_id,
                    "examples": values[:3],
                    "size": len(values),
                }
                for cluster_id, values in grouped.items()
            ]
        return [{"cluster_id": 0, "examples": unique_prompts[:3], "size": len(unique_prompts)}]

    def _similar(self, left: str, right: str) -> float:
        if fuzz is None:
            return 100.0 if left == right else 0.0
        return float(fuzz.token_set_ratio(left, right))


failure_analyzer = FailureAnalyzer()
