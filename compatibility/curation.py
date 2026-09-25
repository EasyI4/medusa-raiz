from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from compatibility.models import Candidate, NormalizedQuery
from compatibility.normalization import normalize_code, normalize_text


@lru_cache(maxsize=1)
def load_rules() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("curated_rules.json")
    return json.loads(path.read_text(encoding="utf-8"))


def rejection_reason(
    intent: NormalizedQuery,
    candidate: Candidate,
) -> str | None:
    for rule in load_rules():
        if rule.get("action") != "REJECT":
            continue
        if normalize_code(rule.get("code")) != candidate.normalized_code:
            continue
        comparisons = (
            ("part_family", intent.part_family),
            ("manufacturer", intent.manufacturer),
            ("model", intent.model),
        )
        if any(
            rule.get(field)
            and normalize_text(rule[field]) != normalize_text(actual)
            for field, actual in comparisons
        ):
            continue
        if rule.get("year") and int(rule["year"]) != intent.year:
            continue
        if rule.get("position") and normalize_text(rule["position"]) != normalize_text(intent.position):
            continue
        if rule.get("engine") and normalize_text(rule["engine"]) != normalize_text(intent.engine):
            continue
        return str(rule.get("reason") or "Regra de curadoria rejeitou a aplicação.")
    return None
