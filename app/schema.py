"""Normalized document and chunk schema shared by all data sources."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Document:
    doc_id: str
    source: str  # "slack" | "drive" | "tickets"
    title: str
    body: str
    allowed_principals: list[str]
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Document":
        if not isinstance(d, dict):
            raise ValueError("Document must be an object")
        for name in ("doc_id", "source", "title", "body", "created_at"):
            if not isinstance(d.get(name), str) or not d[name].strip():
                raise ValueError(f"Document {name} must be a nonempty string")
        principals = d.get("allowed_principals")
        if not isinstance(principals, list) or any(
            not isinstance(p, str) or not p.startswith(("user:", "group:"))
            or not p.partition(":")[2].strip() for p in principals
        ):
            raise ValueError("Document ACL must be a list of user/group principals")
        if "metadata" in d and not isinstance(d["metadata"], dict):
            raise ValueError("Document metadata must be an object")
        return cls(**d)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    text: str
    allowed_principals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Chunk":
        return cls(**d)
