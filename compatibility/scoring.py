from __future__ import annotations

from dataclasses import dataclass, field

from compatibility.models import CompatibilityStatus, NormalizedQuery
from compatibility.validators import ValidationOutcome


@dataclass
class ScoreResult:
    compatibility: CompatibilityStatus
    confidence: float
    score: int
    max_score: int
    log: list[str] = field(default_factory=list)


def score_compatibility(
    intent: NormalizedQuery,
    validation: ValidationOutcome,
) -> ScoreResult:
    if validation.hard_rejects:
        log = [f"HARD_REJECT {reason}" for reason in validation.hard_rejects]
        return ScoreResult(
            compatibility=CompatibilityStatus.REJECTED,
            confidence=0.0,
            score=-100,
            max_score=100,
            log=log,
        )

    score = 0
    max_score = 0
    log: list[str] = []

    def apply(name: str, weight: int, value: bool | None, required: bool = True) -> None:
        nonlocal score, max_score
        if required:
            max_score += weight
        if value is True:
            score += weight
            log.append(f"{name} +{weight}")
        elif value is False:
            score -= weight
            log.append(f"{name} -{weight}")
        elif required:
            log.append(f"{name} +0 (UNKNOWN)")

    apply("PART_FAMILY", 20, validation.matched.get("part_family"))
    apply("MODEL", 15, validation.matched.get("model"))
    apply("APPLICATION_EVIDENCE", 20, validation.matched.get("application_evidence"))
    apply("MANUFACTURER", 10, validation.matched.get("manufacturer"), bool(intent.manufacturer))
    apply("YEAR", 10, validation.matched.get("year"), intent.year is not None)
    apply("POSITION", 12, validation.matched.get("position"), bool(intent.position))
    apply("ENGINE", 15, validation.matched.get("engine"), bool(intent.engine))
    apply("GENERATION", 20, validation.matched.get("generation"), bool(intent.generation))
    apply("TRIM", 8, validation.matched.get("trim"), bool(intent.trim))

    max_score += 20
    if validation.oem_references:
        score += 15
        log.append("OEM_REFERENCE +15")
    else:
        log.append("OEM_REFERENCE +0")
    if validation.independent_sources >= 2:
        bonus = min(5 + (validation.independent_sources - 2) * 2, 10)
        score += bonus
        log.append(f"INDEPENDENT_SOURCES +{bonus}")
    else:
        log.append("INDEPENDENT_SOURCES +0")

    if validation.conflicts:
        penalty = min(25 * len(validation.conflicts), 50)
        score -= penalty
        log.append(f"CONFLICTS -{penalty}")

    confidence = max(0.0, min(1.0, score / max(max_score, 1)))
    critical_matches = (
        validation.matched.get("part_family") is True
        and validation.matched.get("model") is True
        and validation.matched.get("application_evidence") is True
        and (intent.year is None or validation.matched.get("year") is True)
    )
    requested_attributes_match = all(
        validation.matched.get(name) is True
        for name, requested in (
            ("position", bool(intent.position)),
            ("engine", bool(intent.engine)),
            ("generation", bool(intent.generation)),
            ("trim", bool(intent.trim)),
        )
        if requested
    )
    ambiguity_warnings = {
        "MULTIPLE_ENGINES_REQUIRE_SELECTION",
        "MULTIPLE_POSITIONS",
        "GENERATION_UNKNOWN",
        "ENGINE_UNKNOWN",
        "POSITION_UNKNOWN",
        "SINGLE_SOURCE_ONLY",
    }
    has_ambiguity = bool(
        set(validation.warnings) & ambiguity_warnings
        or validation.conflicts
    )
    has_strong_corroboration = (
        validation.oem_references > 0
        or validation.independent_sources >= 2
    )

    if (
        critical_matches
        and requested_attributes_match
        and not has_ambiguity
        and has_strong_corroboration
        and confidence >= 0.78
    ):
        status = CompatibilityStatus.CONFIRMED
    elif (
        critical_matches
        and requested_attributes_match
        and not has_ambiguity
        and confidence >= 0.58
    ):
        status = CompatibilityStatus.PROBABLE
    else:
        status = CompatibilityStatus.AMBIGUOUS

    return ScoreResult(
        compatibility=status,
        confidence=round(confidence, 4),
        score=score,
        max_score=max_score,
        log=log,
    )
