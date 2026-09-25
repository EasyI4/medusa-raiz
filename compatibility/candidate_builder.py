from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from compatibility.models import Application, Candidate, Evidence, Reference
from compatibility.normalization import (
    infer_family_from_text,
    normalize_code,
    normalize_engine,
    normalize_manufacturer,
    normalize_model,
    normalize_position,
    normalize_text,
    normalize_year,
)


SOURCE_CONFIDENCE = {
    "OEM": 1.0,
    "OFFICIAL": 0.95,
    "MANUFACTURER": 0.92,
    "CURATED": 0.88,
    "DISTRIBUTOR": 0.75,
    "PARTNER": 0.72,
    "MARKETPLACE": 0.45,
    "UNKNOWN": 0.5,
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _unique_append(items: list[str], value: Any) -> None:
    value = _text(value)
    if value and normalize_text(value) not in {normalize_text(item) for item in items}:
        items.append(value)


def _source_tier(row: dict[str, Any]) -> str:
    tier = normalize_text(row.get("source_tier"))
    if tier:
        return tier
    source = normalize_text(row.get("fonte"))
    brand = normalize_text(row.get("marca"))
    if any(marker in brand for marker in ("ORIGINAL", "OEM", "GENUINA")):
        return "OEM"
    if "MERCADO LIVRE" in source or "MARKETPLACE" in source:
        return "MARKETPLACE"
    if source:
        return "UNKNOWN"
    return "UNKNOWN"


def _evidence_text(specs: Any) -> str:
    if isinstance(specs, (dict, list)):
        return json.dumps(specs, ensure_ascii=False, default=str)
    return _text(specs)


def _extract_references(specs: Any, source: str) -> list[Reference]:
    if not isinstance(specs, dict):
        return []
    candidates = (
        specs.get("_crossRefs")
        or specs.get("crossRefs")
        or specs.get("equivalentes")
        or specs.get("equivalents")
        or []
    )
    if not isinstance(candidates, list):
        return []

    references: list[Reference] = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        code = _text(item.get("code") or item.get("codigo"))
        brand = _text(item.get("brand") or item.get("marca")) or None
        normalized = normalize_code(code)
        if not normalized or normalized in seen:
            continue
        brand_norm = normalize_text(brand)
        is_oem = any(marker in brand_norm for marker in ("ORIGINAL", "OEM", "GENUINA"))
        references.append(Reference(
            code=code,
            brand=brand,
            kind="OEM_EQUIVALENCE" if is_oem else "CROSS_REFERENCE",
            source=source or None,
            confidence=0.9 if is_oem else 0.7,
            is_oem=is_oem,
        ))
        seen.add(normalized)
    return references


def _extract_position(row: dict[str, Any]) -> str | None:
    specs = row.get("specs")
    if isinstance(specs, dict):
        for key in ("position", "posicao", "Posição", "Posi��o", "Lado"):
            position = normalize_position(specs.get(key))
            if position:
                return position
    return normalize_position(
        " ".join((_text(row.get("position")), _text(row.get("descricao")), _evidence_text(specs)))
    )


def _extract_engines(row: dict[str, Any]) -> list[str]:
    engines: list[str] = []
    for field in ("engine", "motor", "variant"):
        engine = normalize_engine(row.get(field))
        if engine and any(char.isdigit() for char in engine) and engine not in engines:
            engines.append(engine)
    specs = row.get("specs")
    if isinstance(specs, dict):
        for key in ("engine", "motor", "motorizacao", "Motorização"):
            engine = normalize_engine(specs.get(key))
            if engine and engine not in engines:
                engines.append(engine)
    evidence_text = _evidence_text(specs).upper().replace(",", ".")
    for displacement, aspiration in re.findall(
        r"\b([0-6]\.\d)\s*(TURBO|ASPIRADO)?\b",
        evidence_text,
    ):
        engine = " ".join(filter(None, (displacement, aspiration)))
        if engine not in engines:
            engines.append(engine)
    return engines


def _extract_generation(row: dict[str, Any]) -> str | None:
    specs = row.get("specs")
    if not isinstance(specs, dict):
        return None
    for key in ("generation", "geracao", "geração", "platform", "plataforma"):
        value = normalize_text(specs.get(key))
        if value:
            return value
    return None


def _application_from_row(row: dict[str, Any], source: str) -> Application:
    engines = _extract_engines(row)
    return Application(
        manufacturer=normalize_manufacturer(row.get("make") or row.get("manufacturer")),
        model=normalize_model(row.get("model")),
        variant=normalize_text(row.get("variant")) or None,
        year_start=normalize_year(row.get("year_start")),
        year_end=normalize_year(row.get("year_end")),
        generation=_extract_generation(row),
        engine=engines[0] if len(engines) == 1 else None,
        engine_code=normalize_text(row.get("engine_code")) or None,
        fuel=normalize_text(row.get("fuel")) or None,
        transmission=normalize_text(row.get("transmission")) or None,
        body=normalize_text(row.get("body")) or None,
        market=normalize_text(row.get("market")) or None,
        position=_extract_position(row),
        source=source or None,
    )


def _application_key(application: Application) -> tuple[Any, ...]:
    return (
        application.manufacturer,
        application.model,
        application.variant,
        application.year_start,
        application.year_end,
        application.generation,
        application.engine,
        application.position,
        application.source,
    )


def build_candidates(
    rows: list[dict[str, Any]],
    structured_evidence: list[dict[str, Any]] | None = None,
) -> list[Candidate]:
    candidates: dict[str, Candidate] = {}
    family_votes: dict[str, Counter[str]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _text(row.get("codigo") or row.get("code"))
        normalized_code = normalize_code(code)
        if not normalized_code:
            continue
        candidate = candidates.setdefault(
            normalized_code,
            Candidate(code=code, normalized_code=normalized_code),
        )
        candidate.raw_record_count += 1
        _unique_append(candidate.brands, row.get("marca") or row.get("brand"))
        _unique_append(candidate.descriptions, row.get("descricao") or row.get("description"))
        _unique_append(candidate.declared_types, row.get("tipo") or row.get("type"))
        _unique_append(candidate.sources, row.get("fonte") or row.get("source"))

        tier = _source_tier(row)
        _unique_append(candidate.source_tiers, tier)
        source = _text(row.get("fonte") or row.get("source"))
        confidence = SOURCE_CONFIDENCE.get(tier, SOURCE_CONFIDENCE["UNKNOWN"])
        candidate.evidence.append(Evidence(
            kind="SOURCE_RECORD",
            source=source or "unknown",
            value=_text(row.get("descricao") or row.get("description")),
            confidence=confidence,
            attributes={"tier": tier},
        ))
        specs_text = _evidence_text(row.get("specs"))
        if specs_text:
            candidate.evidence.append(Evidence(
                kind="APPLICATION_TEXT",
                source=source or "unknown",
                value=specs_text,
                confidence=confidence,
                attributes={"tier": tier},
            ))

        family = infer_family_from_text(
            row.get("part_family"),
            row.get("tipo"),
            row.get("descricao"),
        )
        if family:
            family_votes.setdefault(normalized_code, Counter())[family] += 1

        position = _extract_position(row)
        if position and not candidate.position:
            candidate.position = position
        for engine in _extract_engines(row):
            _unique_append(candidate.engines, engine)
        generation = _extract_generation(row)
        _unique_append(candidate.generations, generation)

        application = _application_from_row(row, source)
        if _application_key(application) not in {
            _application_key(item) for item in candidate.applications
        }:
            candidate.applications.append(application)

        existing_refs = {normalize_code(item.code) for item in candidate.references}
        for reference in _extract_references(row.get("specs"), source):
            if normalize_code(reference.code) not in existing_refs:
                candidate.references.append(reference)
                candidate.evidence.append(Evidence(
                    kind=reference.kind or "CROSS_REFERENCE",
                    source=source or "unknown",
                    value=reference.code,
                    confidence=reference.confidence or 0.5,
                    attributes={
                        "brand": reference.brand,
                        "is_oem": reference.is_oem,
                    },
                ))
                existing_refs.add(normalize_code(reference.code))

    for code, candidate in candidates.items():
        votes = family_votes.get(code)
        if votes:
            candidate.part_family = votes.most_common(1)[0][0]
    _merge_structured_evidence(candidates, structured_evidence or [])
    return list(candidates.values())


def _merge_structured_evidence(
    candidates: dict[str, Candidate],
    rows: list[dict[str, Any]],
) -> None:
    for row in rows:
        code = normalize_code(row.get("part_code_norm") or row.get("part_code"))
        candidate = candidates.get(code)
        if not candidate:
            continue
        source = _text(row.get("source_name")) or "part_evidence"
        confidence = float(row.get("confidence") or row.get("source_trust_score") or 0.5)
        kind = _text(row.get("evidence_kind")) or "STRUCTURED_EVIDENCE"
        value = _text(row.get("evidence_text") or row.get("application_description") or row.get("ref_code"))
        candidate.evidence.append(Evidence(
            kind=kind,
            source=source,
            value=value,
            confidence=max(0.0, min(1.0, confidence)),
            attributes={
                "strength": row.get("evidence_strength"),
                "supports_oem": row.get("supports_oem"),
                "supports_aftermarket": row.get("supports_aftermarket"),
                "supports_application": row.get("supports_application"),
                "supports_position": row.get("supports_position"),
            },
        ))
        _unique_append(candidate.sources, source)
        position = normalize_position(row.get("position"))
        if position and not candidate.position:
            candidate.position = position
        engine = normalize_engine(row.get("engine") or row.get("engine_displacement"))
        _unique_append(candidate.engines, engine)

        application = Application(
            manufacturer=normalize_manufacturer(row.get("vehicle_make")),
            model=normalize_model(row.get("vehicle_model")),
            variant=normalize_text(row.get("vehicle_version")) or None,
            year_start=normalize_year(row.get("year_start")),
            year_end=normalize_year(row.get("year_end")),
            engine=engine,
            engine_code=normalize_text(row.get("engine_code")) or None,
            fuel=normalize_text(row.get("fuel")) or None,
            transmission=normalize_text(row.get("transmission")) or None,
            body=normalize_text(row.get("body")) or None,
            position=position,
            source=source,
        )
        if any(application.to_dict().values()) and _application_key(application) not in {
            _application_key(item) for item in candidate.applications
        }:
            candidate.applications.append(application)

        ref_code = _text(row.get("ref_code"))
        if ref_code:
            ref_brand = _text(row.get("ref_brand")) or None
            is_oem = bool(row.get("supports_oem")) or any(
                marker in normalize_text(ref_brand)
                for marker in ("ORIGINAL", "OEM", "GENUINA")
            )
            if normalize_code(ref_code) not in {
                normalize_code(item.code) for item in candidate.references
            }:
                candidate.references.append(Reference(
                    code=ref_code,
                    brand=ref_brand,
                    kind="OEM_EQUIVALENCE" if is_oem else (_text(row.get("ref_kind")) or "REFERENCE"),
                    source=source,
                    confidence=max(0.0, min(1.0, confidence)),
                    is_oem=is_oem,
                ))
