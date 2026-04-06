from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QuestionItem:
    """Unified question schema for every generator and output layer."""

    id: str
    subject: str
    topic: str
    grade: int
    difficulty: str
    type: str
    question_text: str
    options: Optional[List[str]]
    correct_answer: Any
    explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    render_spec: Optional[Dict[str, Any]] = None
    source_info: Optional[Dict[str, Any]] = None

    @classmethod
    def from_legacy_dict(
        cls,
        payload: Dict[str, Any],
        subject: str,
        grade: int,
        difficulty: str,
    ) -> "QuestionItem":
        options_map = payload.get("options")
        options_list: Optional[List[str]] = None
        metadata: Dict[str, Any] = dict(payload.get("metadata") or {})

        if isinstance(options_map, dict):
            labels = sorted(options_map.keys())
            options_list = [str(options_map[label]) for label in labels]
            metadata["option_labels"] = labels
            metadata["correct_label"] = str(
                payload.get("correct", payload.get("correct_label", ""))
            ).upper()
        elif isinstance(options_map, list):
            options_list = [str(item) for item in options_map]

        correct_answer = payload.get("correct_value", payload.get("answer", payload.get("correct")))
        if correct_answer is None and options_list and isinstance(options_map, dict):
            correct_label = metadata.get("correct_label")
            labels = metadata.get("option_labels", [])
            if correct_label in labels:
                correct_answer = options_list[labels.index(correct_label)]

        source_info = dict(payload.get("source_info") or {}) or None
        if (payload.get("source") or payload.get("source_type")) and not source_info:
            source_info = {
                "name": payload.get("source"),
                "source_type": payload.get("source_type"),
                "source_id": payload.get("book_source_id"),
                "quality_score": payload.get("quality_score"),
            }

        render_spec = payload.get("render_spec")
        if render_spec is not None and hasattr(render_spec, "to_dict"):
            render_spec = render_spec.to_dict()

        return cls(
            id=str(payload.get("id") or payload.get("question_id") or uuid.uuid4()),
            subject=str(payload.get("subject") or subject),
            topic=str(payload.get("topic") or subject),
            grade=int(payload.get("grade", grade)),
            difficulty=str(payload.get("difficulty") or difficulty),
            type=str(payload.get("type") or "question"),
            question_text=str(payload.get("question") or payload.get("question_text") or "").strip(),
            options=options_list,
            correct_answer=correct_answer,
            explanation=str(payload.get("explanation") or ""),
            metadata=metadata,
            render_spec=render_spec,
            source_info=source_info,
        )

    def infer_correct_label(self) -> Optional[str]:
        option_labels = self.metadata.get("option_labels") or []
        if not self.options or not option_labels:
            return None

        if self.metadata.get("correct_label") in option_labels:
            return self.metadata["correct_label"]

        for index, value in enumerate(self.options):
            if str(value).strip() == str(self.correct_answer).strip():
                return option_labels[index]
        return None

    def to_legacy_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "question_id": self.id,
            "subject": self.subject,
            "topic": self.topic,
            "grade": self.grade,
            "difficulty": self.difficulty,
            "type": self.type,
            "question": self.question_text,
            "question_text": self.question_text,
            "correct_value": self.correct_answer,
            "answer": self.correct_answer,
            "explanation": self.explanation,
            "metadata": dict(self.metadata),
        }

        if self.options:
            labels = self.metadata.get("option_labels") or ["A", "B", "C", "D"][: len(self.options)]
            payload["options"] = {labels[idx]: self.options[idx] for idx in range(min(len(labels), len(self.options)))}
            correct_label = self.infer_correct_label()
            if correct_label:
                payload["correct"] = correct_label
                payload["correct_label"] = correct_label

        if self.source_info:
            payload["source"] = self.source_info.get("name")
            payload["source_type"] = self.source_info.get("source_type")
            if self.source_info.get("source_id"):
                payload["book_source_id"] = self.source_info["source_id"]
            payload["source_info"] = dict(self.source_info)

        if self.render_spec:
            payload["render_spec"] = self.render_spec
            payload["requires_image"] = True

        return payload
