from __future__ import annotations

import json
import re
from typing import Any, Protocol

from artificial_intelligence.agents.normal_agent import MainAgent
from compatibility.models import NormalizedQuery
from compatibility.normalization import normalize_intent


class IntentAgent(Protocol):
    def ask_openai(self, prompt: str) -> str | dict[str, Any]:
        ...


_INTENT_PROMPT = """
Extraia a intenção de uma consulta brasileira de autopeças.
Responda SOMENTE com um objeto JSON válido, sem markdown:
{
  "manufacturer": "montadora ou null",
  "model": "modelo sem apagar geração ou plataforma, ou null",
  "year": 2020,
  "part_family": "família canônica ou null",
  "position": "FRONT, REAR, LEFT, RIGHT, INNER, OUTER ou null",
  "engine": "motorização completa ou null",
  "trim": "versão ou null",
  "generation": "geração/plataforma explícita ou null",
  "transmission": "transmissão explícita ou null",
  "market": "BR"
}

Famílias canônicas:
PASTILHA_FREIO, DISCO_FREIO, FILTRO_AR_MOTOR, FILTRO_OLEO,
FILTRO_COMBUSTIVEL, FILTRO_CABINE, KIT_EMBREAGEM, DISCO_EMBREAGEM,
CUBO_RODA, ROLAMENTO, AMORTECEDOR, BANDEJA, TERMINAL, BIELETA,
BOMBA_AGUA, BOMBA_COMBUSTIVEL, VELA_IGNICAO, CORREIA_DENTADA.

Regras:
- Não invente dado ausente; use null.
- DISCO nunca é suficiente: diferencie DISCO_FREIO de DISCO_EMBREAGEM.
- FILTRO nunca é suficiente: diferencie ar do motor, óleo, combustível e cabine.
- Preserve diferenças de motor como 1.5 TURBO e 2.0.
- Preserve geração, versão, transmissão e posição quando explícitas.
""".strip()


def _extract_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("A IA não retornou um objeto de intenção.")
    return parsed


class IntentParser:
    def __init__(self, agent: IntentAgent | None = None):
        self.agent = agent or MainAgent()

    def parse(self, query: str) -> NormalizedQuery:
        query = str(query or "").strip()
        if not query:
            raise ValueError("A consulta não pode estar vazia.")

        prompt = f"{_INTENT_PROMPT}\n\nConsulta:\n{query}"
        response = self.agent.ask_openai(prompt)
        try:
            if isinstance(response, dict):
                if response.get("success") is False:
                    raise ValueError(str(response.get("error") or "Falha na IA."))
                payload = response
            else:
                payload = _extract_json(str(response))
            return normalize_intent(query, payload, parser="ai")
        except (ValueError, TypeError, json.JSONDecodeError):
            # O fallback não adivinha veículo; ele preserva somente atributos
            # extraíveis deterministicamente da própria pergunta.
            return normalize_intent(query, {}, parser="fallback")
