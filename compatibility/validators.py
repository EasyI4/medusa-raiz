from __future__ import annotations

import re
from dataclasses import dataclass, field

from compatibility.curation import rejection_reason
from compatibility.equivalence_graph import EquivalenceGraph
from compatibility.models import Candidate, NormalizedQuery
from compatibility.normalization import normalize_engine, normalize_text


@dataclass
class ValidationOutcome:
    matched: dict[str, bool | None] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    hard_rejects: list[str] = field(default_factory=list)
    independent_sources: int = 0
    oem_references: int = 0


def _word_set(value: str | None) -> set[str]:
    return set(normalize_text(value).split())


def _model_matches(expected: str | None, actual: str | None) -> bool:
    if not expected or not actual:
        return False
    expected_words = _word_set(expected)
    actual_words = _word_set(actual)
    return bool(expected_words) and expected_words.issubset(actual_words)


def _engine_signature(value: str | None) -> tuple[str | None, set[str]]:
    normalized = normalize_engine(value)
    if not normalized:
        return None, set()
    displacement = re.search(r"\b\d+(?:[.,]\d+)?\b", normalized)
    markers = {
        marker for marker in ("TURBO", "ASPIRADO", "FLEX", "DIESEL", "GASOLINA", "HIBRIDO")
        if marker in normalize_text(normalized)
    }
    return displacement.group(0).replace(",", ".") if displacement else None, markers


def _engines_compatible(expected: str, actual: str) -> bool:
    expected_displacement, expected_markers = _engine_signature(expected)
    actual_displacement, actual_markers = _engine_signature(actual)
    if expected_displacement and actual_displacement and expected_displacement != actual_displacement:
        return False
    critical = {"TURBO", "ASPIRADO", "DIESEL", "GASOLINA", "HIBRIDO"}
    expected_critical = expected_markers & critical
    actual_critical = actual_markers & critical
    if expected_critical and actual_critical and expected_critical != actual_critical:
        return False
    return bool(expected_displacement == actual_displacement or expected_markers & actual_markers)


def _application_evidence_status(
    evidence_text: str,
    model: str | None,
    year: int | None,
) -> bool | None:
    normalized = normalize_text(evidence_text)
    model_words = _word_set(model)
    if not model_words or not normalized:
        return None
    anchor = max(model_words, key=len)
    positions = [match.start() for match in re.finditer(rf"\b{re.escape(anchor)}\b", normalized)]
    if not positions:
        return None

    saw_explicit_range = False
    for position in positions:
        window = normalized[max(0, position - 50):position + 240]
        if not all(re.search(rf"\b{re.escape(word)}\b", window) for word in model_words):
            continue
        if year is None:
            return True
        if re.search(rf"\b{year}\b", window):
            return True
        ranges = re.findall(
            r"\b((?:19|20)\d{2})\s*(?:-|A|ATE)?\s*((?:19|20)\d{2})\b",
            window,
        )
        if ranges:
            saw_explicit_range = True
        if any(int(start) <= year <= int(end) for start, end in ranges):
            return True
    return False if saw_explicit_range else None


def _explicit_engine_values(candidate: Candidate) -> list[str]:
    values = list(candidate.engines)
    values.extend(
        application.engine
        for application in candidate.applications
        if application.engine
    )
    unique: list[str] = []
    for value in values:
        normalized = normalize_engine(value)
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def validate_candidate(
    intent: NormalizedQuery,
    candidate: Candidate,
    graph: EquivalenceGraph,
) -> ValidationOutcome:
    outcome = ValidationOutcome()

    curated_rejection = rejection_reason(intent, candidate)
    if curated_rejection:
        outcome.hard_rejects.append("CURATED_INCOMPATIBILITY")
        outcome.reasons.append(curated_rejection)

    family_match = (
        candidate.part_family == intent.part_family
        if candidate.part_family and intent.part_family
        else None
    )
    outcome.matched["part_family"] = family_match
    if family_match is False:
        outcome.hard_rejects.append("PART_FAMILY_MISMATCH")
    elif family_match is True:
        outcome.reasons.append("PART_FAMILY_MATCH")
    else:
        outcome.warnings.append("PART_FAMILY_UNKNOWN")

    make_values = {application.manufacturer for application in candidate.applications if application.manufacturer}
    model_values = {application.model for application in candidate.applications if application.model}
    make_match = (
        any(value == intent.manufacturer for value in make_values)
        if intent.manufacturer else None
    )
    model_match = any(_model_matches(intent.model, value) for value in model_values) if intent.model else None
    outcome.matched["manufacturer"] = make_match
    outcome.matched["model"] = model_match
    if make_match is False:
        outcome.hard_rejects.append("MANUFACTURER_MISMATCH")
    if model_match is False:
        outcome.hard_rejects.append("MODEL_MISMATCH")
    if make_match:
        outcome.reasons.append("MANUFACTURER_MATCH")
    if model_match:
        outcome.reasons.append("MODEL_MATCH")

    year_statuses = []
    if intent.year is not None:
        for application in candidate.applications:
            if application.year_start is None or application.year_end is None:
                continue
            year_statuses.append(application.year_start <= intent.year <= application.year_end)
        year_match = any(year_statuses) if year_statuses else None
    else:
        year_match = None
    outcome.matched["year"] = year_match
    if year_match is False:
        outcome.hard_rejects.append("YEAR_MISMATCH")
    elif year_match:
        outcome.reasons.append("YEAR_MATCH")
    elif intent.year is not None:
        outcome.warnings.append("YEAR_UNKNOWN")

    evidence_by_source: dict[str, list[bool]] = {}
    for evidence in candidate.evidence:
        if evidence.kind != "APPLICATION_TEXT":
            continue
        status = _application_evidence_status(evidence.value, intent.model, intent.year)
        if status is not None:
            evidence_by_source.setdefault(evidence.source, []).append(status)
    evidence_statuses = [status for statuses in evidence_by_source.values() for status in statuses]
    evidence_match = any(evidence_statuses) if evidence_statuses else None
    outcome.matched["application_evidence"] = evidence_match
    if evidence_match is not True:
        outcome.hard_rejects.append("APPLICATION_EVIDENCE_MISSING")
    else:
        outcome.reasons.append("APPLICATION_EVIDENCE_MATCH")
    if any(evidence_statuses) and any(status is False for status in evidence_statuses):
        outcome.conflicts.append("YEAR_OR_APPLICATION_SOURCE_CONFLICT")

    known_positions = {
        value for value in [candidate.position]
        + [application.position for application in candidate.applications]
        if value
    }
    if intent.position:
        position_match = intent.position in known_positions if known_positions else None
        outcome.matched["position"] = position_match
        if position_match is False:
            outcome.hard_rejects.append("POSITION_MISMATCH")
        elif position_match:
            outcome.reasons.append("POSITION_MATCH")
        else:
            outcome.warnings.append("POSITION_UNKNOWN")
    else:
        outcome.matched["position"] = None
        if len(known_positions) > 1:
            outcome.warnings.append("MULTIPLE_POSITIONS")

    engines = _explicit_engine_values(candidate)
    if intent.engine:
        engine_match = any(_engines_compatible(intent.engine, value) for value in engines) if engines else None
        outcome.matched["engine"] = engine_match
        if engine_match is False:
            outcome.hard_rejects.append("ENGINE_MISMATCH")
        elif engine_match:
            outcome.reasons.append("ENGINE_MATCH")
        else:
            outcome.warnings.append("ENGINE_UNKNOWN")
    else:
        outcome.matched["engine"] = None
        displacements = {value[0] for value in map(_engine_signature, engines) if value[0]}
        if len(displacements) > 1:
            outcome.warnings.append("MULTIPLE_ENGINES_REQUIRE_SELECTION")

    if intent.generation:
        generation_match = intent.generation in candidate.generations if candidate.generations else None
        outcome.matched["generation"] = generation_match
        if generation_match is False:
            outcome.hard_rejects.append("GENERATION_MISMATCH")
        elif generation_match:
            outcome.reasons.append("GENERATION_MATCH")
        else:
            outcome.warnings.append("GENERATION_UNKNOWN")
    else:
        outcome.matched["generation"] = None
        if len(candidate.generations) > 1:
            outcome.conflicts.append("MULTIPLE_GENERATIONS")

    if intent.trim:
        variants = {application.variant for application in candidate.applications if application.variant}
        trim_match = any(intent.trim in value for value in variants) if variants else None
        outcome.matched["trim"] = trim_match
        if trim_match is False:
            outcome.hard_rejects.append("TRIM_MISMATCH")
        elif trim_match:
            outcome.reasons.append("TRIM_MATCH")
        else:
            outcome.warnings.append("TRIM_UNKNOWN")
    else:
        outcome.matched["trim"] = None

    oem_refs = graph.oem_refs(candidate.code)
    outcome.oem_references = len(oem_refs)
    outcome.matched["oem"] = True if oem_refs else None
    if oem_refs:
        outcome.reasons.append("OEM_REFERENCE_CONFIRMED")

    outcome.independent_sources = len({
        evidence.source for evidence in candidate.evidence if evidence.source != "unknown"
    })
    outcome.matched["multiple_sources"] = (
        outcome.independent_sources >= 2 if outcome.independent_sources else None
    )
    if outcome.independent_sources >= 2:
        outcome.reasons.append("MULTIPLE_INDEPENDENT_SOURCES")
    elif outcome.independent_sources <= 1:
        outcome.warnings.append("SINGLE_SOURCE_ONLY")

    return outcome
