from __future__ import annotations

import json
import logging
import re
from typing import Any

from compatibility.candidate_builder import build_candidates
from compatibility.equivalence_graph import EquivalenceGraph
from compatibility.models import (
    CompatibilityDecision,
    CompatibilityResult,
    CompatibilityStatus,
    NormalizedQuery,
)
from compatibility.scoring import score_compatibility
from compatibility.validators import validate_candidate


audit_logger = logging.getLogger("compatibility.audit")

_STATUS_ORDER = {
    CompatibilityStatus.CONFIRMED: 0,
    CompatibilityStatus.PROBABLE: 1,
    CompatibilityStatus.AMBIGUOUS: 2,
    CompatibilityStatus.REJECTED: 3,
}


def _is_original_candidate(decision: CompatibilityDecision) -> bool:
    if "OEM" in decision.candidate.source_tiers:
        return True
    return any(
        re.search(r"\b(ORIGINAL|OEM|GENU[IÍ]NA?)\b", brand, flags=re.IGNORECASE)
        for brand in decision.candidate.brands
    )


def _displacement(value: str) -> str | None:
    match = re.search(r"\b\d+(?:[.,]\d+)?\b", value)
    return match.group(0).replace(",", ".") if match else None


class CompatibilityEngine:
    def evaluate(
        self,
        intent: NormalizedQuery,
        rows: list[dict[str, Any]],
        evidence_rows: list[dict[str, Any]] | None = None,
    ) -> CompatibilityResult:
        candidates = build_candidates(rows, evidence_rows)
        graph = EquivalenceGraph()
        for candidate in candidates:
            graph.add_candidate(candidate)

        global_displacements = {
            displacement
            for candidate in candidates
            for engine in candidate.engines
            if (displacement := _displacement(engine))
        }
        decisions: list[CompatibilityDecision] = []
        rejected: list[CompatibilityDecision] = []

        for candidate in candidates:
            validation = validate_candidate(intent, candidate, graph)
            if not intent.engine and len(global_displacements) > 1:
                if "MULTIPLE_ENGINES_REQUIRE_SELECTION" not in validation.warnings:
                    validation.warnings.append("MULTIPLE_ENGINES_REQUIRE_SELECTION")

            scored = score_compatibility(intent, validation)
            decision = CompatibilityDecision(
                candidate=candidate,
                compatibility=scored.compatibility,
                confidence=scored.confidence,
                score=scored.score,
                max_score=scored.max_score,
                matched=validation.matched,
                reasons=(
                    [f"HARD_REJECT {reason}" for reason in validation.hard_rejects]
                    + validation.reasons
                    + scored.log
                ),
                warnings=validation.warnings,
                conflicts=validation.conflicts,
                cluster_id=graph.cluster_id(candidate.code),
            )
            self._log_decision(intent, decision)
            if decision.compatibility is CompatibilityStatus.REJECTED:
                rejected.append(decision)
            else:
                decisions.append(decision)

        decisions.sort(
            key=lambda item: (
                _STATUS_ORDER[item.compatibility],
                0 if _is_original_candidate(item) else 1,
                -item.confidence,
                item.candidate.code,
            )
        )
        rejected.sort(key=lambda item: item.candidate.code)
        status_counts = {
            status.value: sum(
                item.compatibility is status
                for item in decisions + rejected
            )
            for status in CompatibilityStatus
        }
        return CompatibilityResult(
            query=intent,
            decisions=decisions,
            rejected=rejected,
            metrics={
                "candidate_count": len(candidates),
                "visible_count": len(decisions),
                "rejected_count": len(rejected),
                "status_counts": status_counts,
                "equivalence_clusters": len({
                    item.cluster_id for item in decisions + rejected if item.cluster_id
                }),
                "requires_engine_selection": (
                    not intent.engine and len(global_displacements) > 1
                ),
                "engine_options": sorted(global_displacements),
            },
        )

    def _log_decision(
        self,
        intent: NormalizedQuery,
        decision: CompatibilityDecision,
    ) -> None:
        audit_logger.info(
            "compatibility_decision %s",
            json.dumps({
                "query": intent.raw_query,
                "code": decision.candidate.code,
                "compatibility": decision.compatibility.value,
                "confidence": decision.confidence,
                "score": decision.score,
                "matched": decision.matched,
                "reasons": decision.reasons,
                "warnings": decision.warnings,
                "conflicts": decision.conflicts,
            }, ensure_ascii=False),
        )
