from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CompatibilityStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROBABLE = "PROBABLE"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"


class Position(str, Enum):
    FRONT = "FRONT"
    REAR = "REAR"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    INNER = "INNER"
    OUTER = "OUTER"


@dataclass(frozen=True)
class NormalizedQuery:
    raw_query: str
    manufacturer: str | None = None
    model: str | None = None
    year: int | None = None
    part_family: str | None = None
    position: str | None = None
    engine: str | None = None
    trim: str | None = None
    generation: str | None = None
    transmission: str | None = None
    market: str = "BR"
    parser: str = "ai"
    parser_warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["parser_warnings"] = list(self.parser_warnings)
        return result


@dataclass(frozen=True)
class Application:
    manufacturer: str | None = None
    model: str | None = None
    variant: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    generation: str | None = None
    engine: str | None = None
    engine_code: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    body: str | None = None
    market: str | None = None
    position: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Reference:
    code: str
    brand: str | None = None
    kind: str | None = None
    source: str | None = None
    confidence: float | None = None
    is_oem: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Evidence:
    kind: str
    source: str
    value: str
    confidence: float
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Candidate:
    code: str
    normalized_code: str
    brands: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    declared_types: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    source_tiers: list[str] = field(default_factory=list)
    part_family: str | None = None
    position: str | None = None
    engines: list[str] = field(default_factory=list)
    generations: list[str] = field(default_factory=list)
    applications: list[Application] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    raw_record_count: int = 0


@dataclass
class CompatibilityDecision:
    candidate: Candidate
    compatibility: CompatibilityStatus
    confidence: float
    score: int
    max_score: int
    matched: dict[str, bool | None]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    cluster_id: str | None = None

    def to_dict(self, include_evidence: bool = True) -> dict[str, Any]:
        result = {
            "code": self.candidate.code,
            "brands": self.candidate.brands,
            "descriptions": self.candidate.descriptions,
            "part_family": self.candidate.part_family,
            "position": self.candidate.position,
            "engines": self.candidate.engines,
            "generations": self.candidate.generations,
            "applications": [item.to_dict() for item in self.candidate.applications],
            "references": [item.to_dict() for item in self.candidate.references],
            "sources": self.candidate.sources,
            "source_tiers": self.candidate.source_tiers,
            "raw_record_count": self.candidate.raw_record_count,
            "compatibility": self.compatibility.value,
            "confidence": self.confidence,
            "score": self.score,
            "max_score": self.max_score,
            "matched": self.matched,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "conflicts": self.conflicts,
            "cluster_id": self.cluster_id,
        }
        if include_evidence:
            result["evidence"] = [item.to_dict() for item in self.candidate.evidence]
        return result


@dataclass
class CompatibilityResult:
    query: NormalizedQuery
    decisions: list[CompatibilityDecision]
    rejected: list[CompatibilityDecision]
    metrics: dict[str, Any]

    def to_dict(self, include_rejected: bool = False) -> dict[str, Any]:
        result = {
            "query": self.query.to_dict(),
            "results": [item.to_dict() for item in self.decisions],
            "metrics": self.metrics,
        }
        if include_rejected:
            result["rejected"] = [item.to_dict() for item in self.rejected]
        return result
