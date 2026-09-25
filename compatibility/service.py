from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from typing import Any

from artificial_intelligence.agents.normal_agent import MainAgent
from compatibility.engine import CompatibilityEngine
from compatibility.intent_parser import IntentParser
from compatibility.models import (
    Application,
    CompatibilityDecision,
    CompatibilityResult,
    CompatibilityStatus,
)
from compatibility.repository import PartCandidateRepository


class PartCompatibilityService:
    def __init__(
        self,
        driver: str,
        server: str,
        database: str,
        uid: str,
        pwd: str,
        intent_parser: IntentParser | None = None,
        repository: PartCandidateRepository | None = None,
        engine: CompatibilityEngine | None = None,
        answer_agent: MainAgent | None = None,
    ):
        self.intent_parser = intent_parser or IntentParser()
        self.repository = repository or PartCandidateRepository(
            driver=driver,
            server=server,
            database=database,
            uid=uid,
            pwd=pwd,
            max_rows=int(os.getenv("PART_CANDIDATE_MAX_ROWS", "2500")),
            timeout_ms=int(os.getenv("PART_QUERY_TIMEOUT_MS", "20000")),
        )
        self.engine = engine or CompatibilityEngine()
        self.answer_agent = answer_agent or MainAgent()

    def search(self, question: str) -> dict[str, Any]:
        intent = self.intent_parser.parse(question)
        retrieval = self.repository.search(intent)
        result = self.engine.evaluate(
            intent,
            retrieval.rows,
            retrieval.evidence_rows,
        )
        data = self._flatten_visible_results(result)
        answer = self._build_answer(question, result)

        response: dict[str, Any] = {
            "success": True,
            "message": self._message(result),
            "answer": json.dumps(answer, ensure_ascii=False),
            "data": data,
            "row_count": len(data),
            "truncated": retrieval.truncated,
            "command": None,
            "compatibility": {
                "query": intent.to_dict(),
                "metrics": result.metrics,
            },
        }
        if os.getenv("COMPATIBILITY_DEBUG", "").strip() == "1":
            response["compatibility"]["rejected"] = [
                item.to_dict(include_evidence=False)
                for item in result.rejected
            ]
        return response

    def _flatten_visible_results(
        self,
        result: CompatibilityResult,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for rank, decision in enumerate(result.decisions, start=1):
            candidate = decision.candidate
            applications = candidate.applications or [Application()]
            equivalents = [item.to_dict() for item in candidate.references]
            evidence = [item.to_dict() for item in candidate.evidence]
            is_original = (
                "OEM" in candidate.source_tiers
                or any(
                    re.search(r"\b(ORIGINAL|OEM|GENU[IÍ]NA?)\b", brand, flags=re.IGNORECASE)
                    for brand in candidate.brands
                )
            )
            for application in applications:
                rows.append({
                    "codigo": candidate.code,
                    "marca": ", ".join(candidate.brands),
                    "descricao": candidate.descriptions[0] if candidate.descriptions else None,
                    "descricoes": candidate.descriptions,
                    "tipo": candidate.part_family,
                    "part_family": candidate.part_family,
                    "position": candidate.position or application.position,
                    "make": application.manufacturer,
                    "model": application.model,
                    "variant": application.variant,
                    "year_start": application.year_start,
                    "year_end": application.year_end,
                    "engine": application.engine,
                    "engine_code": application.engine_code,
                    "fuel": application.fuel,
                    "transmission": application.transmission,
                    "generation": application.generation,
                    "body": application.body,
                    "market": application.market,
                    "fonte": application.source or (
                        candidate.sources[0] if candidate.sources else None
                    ),
                    "sources": candidate.sources,
                    "equivalents": equivalents,
                    "compatibility": decision.compatibility.value,
                    "confidence": decision.confidence,
                    "matched": decision.matched,
                    "warnings": decision.warnings,
                    "conflicts": decision.conflicts,
                    "evidence": evidence,
                    "cluster_id": decision.cluster_id,
                    "is_original": is_original,
                    "rank": rank,
                })
        return rows

    def _build_answer(
        self,
        question: str,
        result: CompatibilityResult,
    ) -> dict[str, Any]:
        fallback = self._fallback_answer(result)
        compact = [
            {
                "code": item.candidate.code,
                "brands": item.candidate.brands,
                "family": item.candidate.part_family,
                "position": item.candidate.position,
                "engines": item.candidate.engines,
                "compatibility": item.compatibility.value,
                "confidence": item.confidence,
                "warnings": item.warnings,
                "applications": [
                    application.to_dict()
                    for application in item.candidate.applications[:8]
                ],
            }
            for item in result.decisions
        ]
        prompt = f"""
Você explica resultados já classificados por um motor determinístico de autopeças.
NÃO altere compatibility, confidence, códigos ou evidências.
NÃO invente OEM, geração, motor, posição, versão ou aplicação.
Quando houver AMBIGUOUS ou engine_options, peça ao usuário o atributo faltante.
Responda somente em JSON válido, sem markdown:
{{
  "vehicle": "veículo consultado",
  "year": "ano ou vazio",
  "assessment": "avaliação geral curta e cautelosa",
  "products": [
    {{
      "position": "posição ou não informada",
      "type": "família",
      "assessment": "explicação baseada na classificação e avisos",
      "compatibility": "CONFIRMED|PROBABLE|AMBIGUOUS",
      "confidence": 0.0,
      "codes": [{{"brand": "marca", "code": "código"}}]
    }}
  ]
}}

Pergunta: {question}
Intenção normalizada: {json.dumps(result.query.to_dict(), ensure_ascii=False)}
Métricas: {json.dumps(result.metrics, ensure_ascii=False)}
Resultados classificados: {json.dumps(compact, ensure_ascii=False)}
""".strip()
        response = self.answer_agent.ask_openai(prompt)
        try:
            if isinstance(response, dict):
                return fallback
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(response).strip())
            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                return fallback
            parsed["products"] = (
                parsed.get("products")
                if isinstance(parsed.get("products"), list)
                else fallback["products"]
            )
            return {
                "vehicle": parsed.get("vehicle") or fallback["vehicle"],
                "year": parsed.get("year") or fallback["year"],
                "assessment": parsed.get("assessment") or fallback["assessment"],
                "products": parsed["products"],
            }
        except (ValueError, TypeError, json.JSONDecodeError):
            return fallback

    def _fallback_answer(self, result: CompatibilityResult) -> dict[str, Any]:
        grouped: dict[tuple[str, str, str], list[CompatibilityDecision]] = defaultdict(list)
        for decision in result.decisions:
            grouped[(
                decision.candidate.position or "não informada",
                decision.candidate.part_family or "PEÇA",
                decision.compatibility.value,
            )].append(decision)

        products = []
        for (position, family, status), decisions in grouped.items():
            products.append({
                "position": position,
                "type": family,
                "assessment": self._deterministic_assessment(decisions),
                "compatibility": status,
                "confidence": round(
                    sum(item.confidence for item in decisions) / len(decisions),
                    4,
                ),
                "codes": [
                    {
                        "brand": ", ".join(item.candidate.brands),
                        "code": item.candidate.code,
                    }
                    for item in decisions
                ],
            })

        return {
            "vehicle": " ".join(filter(None, (
                result.query.manufacturer,
                result.query.model,
            ))),
            "year": result.query.year or "",
            "assessment": self._general_assessment(result),
            "products": products,
        }

    def _general_assessment(self, result: CompatibilityResult) -> str:
        if not result.decisions:
            return "Nenhuma peça atingiu evidência mínima de compatibilidade."
        if result.metrics.get("requires_engine_selection"):
            options = ", ".join(result.metrics.get("engine_options") or [])
            return (
                "Existem aplicações diferentes por motorização. "
                f"Informe o motor para confirmar: {options}."
            )
        counts = result.metrics.get("status_counts") or {}
        return (
            f"{counts.get('CONFIRMED', 0)} confirmadas, "
            f"{counts.get('PROBABLE', 0)} prováveis e "
            f"{counts.get('AMBIGUOUS', 0)} que precisam de confirmação."
        )

    def _deterministic_assessment(
        self,
        decisions: list[CompatibilityDecision],
    ) -> str:
        warnings = sorted({warning for item in decisions for warning in item.warnings})
        if warnings:
            return "Compatibilidade condicionada: " + ", ".join(warnings) + "."
        return "Compatibilidade sustentada pelas evidências e aplicações disponíveis."

    def _message(self, result: CompatibilityResult) -> str:
        if not result.decisions:
            return "Nenhuma peça atingiu evidência mínima de compatibilidade."
        if result.metrics.get("requires_engine_selection"):
            return "Foram encontradas famílias diferentes por motorização."
        return "Peças avaliadas e classificadas pelo motor de compatibilidade."
