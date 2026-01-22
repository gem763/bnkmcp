from __future__ import annotations

import os
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from .schemas import PolicyChunk

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError("openai package is required for embeddings") from exc


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv()


def _get_env(name: str, alt: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name) or (os.getenv(alt) if alt else None) or default


class QdrantRepo:
    def __init__(
        self,
        *,
        qdrant_url: str,
        qdrant_api_key: str,
        collection: str,
        openai_api_key: str,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._collection = collection
        self._openai = OpenAI(api_key=openai_api_key)
        self._embedding_model = embedding_model
        self._client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self._datetime_range_cls = getattr(qmodels, "DatetimeRange", None)
        self._vector_name = os.getenv("QDRANT_VECTOR_NAME")

    @classmethod
    def from_env(cls) -> "QdrantRepo":
        _load_env()
        qdrant_url = _get_env("QDRANT_URL")
        qdrant_api_key = _get_env("QDRANT_APIKEY", "QDRANT_API_KEY")
        collection = _get_env("QDRANT_COLLECTION")
        openai_api_key = _get_env("OPENAI_APIKEY", "OPENAI_API_KEY")
        embedding_model = _get_env("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")

        missing = [
            name
            for name, value in (
                ("QDRANT_URL", qdrant_url),
                ("QDRANT_APIKEY", qdrant_api_key),
                ("QDRANT_COLLECTION", collection),
                ("OPENAI_APIKEY", openai_api_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
            collection=collection,
            openai_api_key=openai_api_key,
            embedding_model=embedding_model,
        )

    def search(
        self,
        *,
        query: str,
        limit: int = 5,
        doctype: Optional[str] = None,
        department: Optional[str] = None,
        revised_after: Optional[str] = None,
    ) -> list[PolicyChunk]:
        limit = max(1, min(limit, 50))
        vector = self._embed(query)
        query_filter = self._build_filter(doctype, department, revised_after)

        # ✅ qdrant-client 최신 버전은 .search()가 없고, query_points()를 사용
        if hasattr(self._client, "query_points"):
            resp = self._client.query_points(
                collection_name=self._collection,
                query=vector,              # 벡터 검색
                using=self._vector_name,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )
            # 버전에 따라 resp.points 또는 resp.result.points 형태
            points = getattr(resp, "points", None)
            if points is None and getattr(resp, "result", None) is not None:
                points = getattr(resp.result, "points", None)
            if points is None:
                # 혹시라도 다른 형태면 그대로 반환(디버그)
                points = resp
        elif hasattr(self._client, "search_points"):
            # 일부 버전은 search_points를 제공
            points = self._client.search_points(
                collection_name=self._collection,
                vector=vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )
        else:
            raise RuntimeError(
                "Your qdrant-client version does not support query_points/search_points."
            )

        return [self._to_chunk(p) for p in points]

    def get(self, chunk_id: str | int) -> Optional[PolicyChunk]:
        records = self._client.retrieve(
            collection_name=self._collection,
            ids=[chunk_id],
            with_payload=True,
        )
        if not records:
            return None
        return self._to_chunk(records[0])

    def _embed(self, text: str) -> list[float]:
        response = self._openai.embeddings.create(model=self._embedding_model, input=text)
        return list(response.data[0].embedding)

    def _build_filter(
        self,
        doctype: Optional[str],
        department: Optional[str],
        revised_after: Optional[str],
    ) -> Optional[qmodels.Filter]:
        must: list[qmodels.FieldCondition] = []

        if doctype:
            must.append(
                qmodels.FieldCondition(key="doctype", match=qmodels.MatchValue(value=doctype))
            )
        if department:
            must.append(
                qmodels.FieldCondition(key="department", match=qmodels.MatchValue(value=department))
            )
        if revised_after:
            if self._datetime_range_cls is not None:
                date_range = self._datetime_range_cls(gte=revised_after)
            else:
                date_range = qmodels.Range(gte=revised_after)
            must.append(qmodels.FieldCondition(key="revised", range=date_range))

        if not must:
            return None
        return qmodels.Filter(must=must)

    def _to_chunk(self, point: Any) -> PolicyChunk:
        payload = point.payload or {}

        def pick(*keys: str) -> Optional[Any]:
            for key in keys:
                if key in payload and payload[key] is not None:
                    return payload[key]
            return None

        page = pick("page")
        try:
            if page is not None:
                page = int(page)
        except (TypeError, ValueError):
            pass

        return PolicyChunk(
            id=str(point.id),
            text=pick("text", "chunk", "content"),
            page=page,
            title_path=pick("title_path", "title", "heading"),
            revised=pick("revised", "revised_at"),
            source=pick("source", "url", "file"),
            score=getattr(point, "score", None),
            metadata=payload,
        )
