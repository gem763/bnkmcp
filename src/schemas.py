from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field


class PolicyChunk(BaseModel):
    id: Union[str, int]
    text: Optional[str] = None
    page: Optional[int] = None
    title_path: Optional[Union[str, List[str]]] = None
    revised: Optional[str] = None
    source: Optional[str] = None
    score: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class SearchPolicyChunksArgs(BaseModel):
    query: str = Field(..., min_length=1)
    doctype: Optional[str] = None
    department: Optional[str] = None
    revised_after: Optional[str] = Field(
        None, description="ISO date string, e.g. 2024-01-01 or 2024-01-01T00:00:00Z"
    )
    limit: int = Field(default=5, ge=1, le=50)


class SearchPolicyChunksResult(BaseModel):
    items: List[PolicyChunk]


class GetPolicyChunkArgs(BaseModel):
    id: Union[str, int]


class GetPolicyChunkResult(BaseModel):
    item: Optional[PolicyChunk] = None
