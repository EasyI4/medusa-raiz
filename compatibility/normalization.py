from __future__ import annotations

import re
import unicodedata
from typing import Any

from compatibility.models import NormalizedQuery, Position


MANUFACTURER_ALIASES = {
    "VW": "VOLKSWAGEN",
    "VOLKS": "VOLKSWAGEN",
    "VOLKSWAGEN": "VOLKSWAGEN",
    "GM": "CHEVROLET",
    "CHEVROLET": "CHEVROLET",
    "MERCEDES": "MERCEDES-BENZ",
    "MERCEDES BENZ": "MERCEDES-BENZ",
}

POSITION_ALIASES = {
    "DIANTEIRA": Position.FRONT.value,
    "DIANTEIRO": Position.FRONT.value,
    "FRONT": Position.FRONT.value,
    "EIXO DIANTEIRO": Position.FRONT.value,
    "D": Position.FRONT.value,
    "TRASEIRA": Position.REAR.value,
    "TRASEIRO": Position.REAR.value,
    "REAR": Position.REAR.value,
    "EIXO TRASEIRO": Position.REAR.value,
    "T": Position.REAR.value,
    "ESQUERDA": Position.LEFT.value,
    "ESQUERDO": Position.LEFT.value,
    "LEFT": Position.LEFT.value,
    "DIREITA": Position.RIGHT.value,
    "DIREITO": Position.RIGHT.value,
    "RIGHT": Position.RIGHT.value,
    "INTERNA": Position.INNER.value,
    "INTERNO": Position.INNER.value,
    "INNER": Position.INNER.value,
    "EXTERNA": Position.OUTER.value,
    "EXTERNO": Position.OUTER.value,
    "OUTER": Position.OUTER.value,
}

PART_FAMILY_PATTERNS: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ("PASTILHA_FREIO", (("PASTILHA", "FREIO"), ("PASTILHA",))),
    ("DISCO_FREIO", (("DISCO", "FREIO"),)),
    ("KIT_EMBREAGEM", (("KIT", "EMBREAGEM"),)),
    ("DISCO_EMBREAGEM", (("DISCO", "EMBREAGEM"),)),
    ("FILTRO_AR_MOTOR", (("FILTRO", "AR", "MOTOR"), ("FILTRO", "AR"))),
    ("FILTRO_OLEO", (("FILTRO", "OLEO"),)),
    ("FILTRO_COMBUSTIVEL", (("FILTRO", "COMBUSTIVEL"),)),
    ("FILTRO_CABINE", (("FILTRO", "CABINE"), ("FILTRO", "AR", "CONDICIONADO"))),
    ("CUBO_RODA", (("CUBO", "RODA"), ("CUBO",))),
    ("ROLAMENTO", (("ROLAMENTO",),)),
    ("AMORTECEDOR", (("AMORTECEDOR",),)),
    ("BANDEJA", (("BANDEJA",),)),
    ("TERMINAL", (("TERMINAL",),)),
    ("BIELETA", (("BIELETA",),)),
    ("BOMBA_AGUA", (("BOMBA", "AGUA"),)),
    ("BOMBA_COMBUSTIVEL", (("BOMBA", "COMBUSTIVEL"),)),
    ("VELA_IGNICAO", (("VELA", "IGNICAO"), ("VELA",))),
    ("CORREIA_DENTADA", (("CORREIA", "DENTADA"),)),
)

FAMILY_REQUIRED_TERMS = {
    family: pattern_groups[0]
    for family, pattern_groups in PART_FAMILY_PATTERNS
}


def normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().upper()


def normalize_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", normalize_text(value))


def normalize_manufacturer(value: Any) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    return MANUFACTURER_ALIASES.get(normalized, normalized)


def normalize_model(value: Any, manufacturer: str | None = None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    if manufacturer:
        manufacturer_tokens = set(normalize_text(manufacturer).split())
        tokens = [token for token in normalized.split() if token not in manufacturer_tokens]
        normalized = " ".join(tokens)
    for prefix in ("NEW ", "NOVO ", "NOVA "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    for suffix in (" NEW", " NOVO", " NOVA"):
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    return normalized.strip() or None


def normalize_position(value: Any) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    if normalized in POSITION_ALIASES:
        return POSITION_ALIASES[normalized]
    for alias, canonical in POSITION_ALIASES.items():
        if len(alias) > 1 and re.search(rf"\b{re.escape(alias)}\b", normalized):
            return canonical
    return None


def normalize_engine(value: Any) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    normalized = re.sub(r"(\d)[.,](\d)", r"\1.\2", str(value).upper())
    normalized = normalize_text(normalized).replace(" TURBO FLEX", " TURBO FLEX")
    displacement = re.search(r"\b(\d(?:[.,]\d)?)\s*L?\b", str(value).upper())
    tokens: list[str] = []
    if displacement:
        tokens.append(displacement.group(1).replace(",", "."))
    source = normalize_text(value)
    for marker in ("TURBO", "ASPIRADO", "FLEX", "DIESEL", "GASOLINA", "HIBRIDO"):
        if marker in source and marker not in tokens:
            tokens.append(marker)
    engine_code = re.search(r"\b[A-Z][A-Z0-9-]{2,}\b", source)
    if engine_code and engine_code.group(0) not in tokens:
        tokens.append(engine_code.group(0))
    return " ".join(tokens) if tokens else source


def normalize_part_family(value: Any) -> str | None:
    normalized = normalize_text(value).replace("Ç", "C")
    canonical = normalized.replace(" ", "_")
    known = {family for family, _ in PART_FAMILY_PATTERNS}
    if canonical in known:
        return canonical
    words = set(normalized.split())
    for family, patterns in PART_FAMILY_PATTERNS:
        if any(set(pattern).issubset(words) for pattern in patterns):
            return family
    return None


def infer_family_from_text(*values: Any) -> str | None:
    return normalize_part_family(" ".join(str(value or "") for value in values))


def normalize_year(value: Any) -> int | None:
    if isinstance(value, int) and 1900 <= value <= 2100:
        return value
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return int(match.group(0)) if match else None


def normalize_intent(raw_query: str, payload: dict[str, Any], parser: str = "ai") -> NormalizedQuery:
    manufacturer = normalize_manufacturer(payload.get("manufacturer"))
    warnings: list[str] = []
    part_family = normalize_part_family(payload.get("part_family"))
    if not part_family:
        part_family = infer_family_from_text(raw_query)
        warnings.append("PART_FAMILY_INFERRED_BY_FALLBACK")

    return NormalizedQuery(
        raw_query=raw_query,
        manufacturer=manufacturer,
        model=normalize_model(payload.get("model"), manufacturer),
        year=normalize_year(payload.get("year") or raw_query),
        part_family=part_family,
        position=normalize_position(payload.get("position") or raw_query),
        engine=normalize_engine(payload.get("engine")),
        trim=normalize_text(payload.get("trim")) or None,
        generation=normalize_text(payload.get("generation")) or None,
        transmission=normalize_text(payload.get("transmission")) or None,
        market=normalize_text(payload.get("market")) or "BR",
        parser=parser,
        parser_warnings=tuple(warnings),
    )
