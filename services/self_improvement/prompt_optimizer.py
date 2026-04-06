from __future__ import annotations

from typing import Dict, List

from services.self_improvement.models import ImprovementProposal

try:
    import spacy
except Exception:
    spacy = None


class PromptOptimizer:
    def __init__(self):
        self._nlp = None

    def build_proposals(self, events: List[Dict[str, object]]) -> List[ImprovementProposal]:
        question_texts = [str(event.get("sample_question", "")) for event in events if event.get("sample_question")]
        if not question_texts:
            return []
        avg_length = sum(len(text.split()) for text in question_texts) / max(len(question_texts), 1)
        sentence_ratio = self._sentence_ratio(question_texts[:20])
        if avg_length <= 24 and sentence_ratio >= 0.85:
            return []
        return [
            ImprovementProposal(
                type="prompt_update",
                target="question_prompt",
                problem="Savollar matni ba'zi oqimlarda cho'zilib ketmoqda yoki grammatik ajralishi sust",
                root_cause="Prompt structure savolni qisqa va bir gapli shaklga majburlamayapti",
                solution="Promptga max token budget, single-sentence rule va Uzbek clarity examples qo'shilsin",
                confidence=0.74,
                version="question_prompt_v2",
                metadata={"average_word_count": round(avg_length, 2), "sentence_ratio": round(sentence_ratio, 4)},
            )
        ]

    def _sentence_ratio(self, texts: List[str]) -> float:
        if not texts:
            return 1.0
        if spacy is not None:
            try:
                if self._nlp is None:
                    self._nlp = spacy.blank("xx")
                    if "sentencizer" not in self._nlp.pipe_names:
                        self._nlp.add_pipe("sentencizer")
                counts = []
                for text in texts:
                    doc = self._nlp(text)
                    counts.append(sum(1 for _ in doc.sents) or 1)
                single = sum(1 for count in counts if count == 1)
                return single / max(len(counts), 1)
            except Exception:
                pass
        single = sum(1 for text in texts if text.count(".") <= 1 and text.count("?") <= 1)
        return single / max(len(texts), 1)


prompt_optimizer = PromptOptimizer()
