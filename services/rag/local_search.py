from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

try:
    from whoosh import fields, index
    from whoosh.qparser import QueryParser
except Exception:
    fields = None
    index = None
    QueryParser = None


class LocalSearchIndex:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def index_documents(self, documents: Sequence[Dict[str, str]]) -> None:
        if not documents or fields is None or index is None:
            return
        schema = fields.Schema(url=fields.ID(stored=True, unique=True), title=fields.TEXT(stored=True), content=fields.TEXT(stored=True))
        if not index.exists_in(str(self.index_dir)):
            ix = index.create_in(str(self.index_dir), schema)
        else:
            ix = index.open_dir(str(self.index_dir))
        writer = ix.writer()
        for document in documents:
            writer.update_document(
                url=str(document.get("url", "")),
                title=str(document.get("title", "")),
                content=str(document.get("content", "")),
            )
        writer.commit()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, object]]:
        if fields is None or index is None or QueryParser is None or not index.exists_in(str(self.index_dir)):
            return []
        ix = index.open_dir(str(self.index_dir))
        with ix.searcher() as searcher:
            parsed = QueryParser("content", ix.schema).parse(query)
            results = searcher.search(parsed, limit=limit)
            return [
                {
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "score": float(item.score),
                }
                for item in results
            ]
