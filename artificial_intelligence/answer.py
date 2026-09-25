import datetime
import json
from decimal import Decimal
from uuid import UUID

from artificial_intelligence.agents.normal_agent import MainAgent

_PROMPT_ROWS = 30
_PROMPT_CHARS = 12000


def jsonable(value):
    """Converte tipos do driver ODBC em valores que o JSON aceita."""
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _compact_rows(rows):
    grouped = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("codigo") or "").strip()
        key = code.replace(" ", "").upper() or f"sem-codigo-{len(grouped)}"
        item = grouped.setdefault(key, {
            "codigo": code,
            "marcas": [],
            "descricoes": [],
            "tipos": [],
            "aplicacoes": [],
        })
        for source, target in (
            ("marca", "marcas"),
            ("descricao", "descricoes"),
            ("tipo", "tipos"),
        ):
            value = row.get(source)
            if value not in (None, "") and value not in item[target]:
                item[target].append(value)
        application = {
            "make": row.get("make"),
            "model": row.get("model"),
            "variant": row.get("variant"),
            "year_start": row.get("year_start"),
            "year_end": row.get("year_end"),
        }
        if application not in item["aplicacoes"]:
            item["aplicacoes"].append(application)

    for item in grouped.values():
        item["aplicacoes"] = item["aplicacoes"][:12]
    return list(grouped.values())


def build_answer_prompt(user_question, command, rows, truncated):
    compacted = _compact_rows(rows)
    shown = compacted[:_PROMPT_ROWS]
    payload = json.dumps(shown, ensure_ascii=False)
    if len(payload) > _PROMPT_CHARS:
        payload = payload[:_PROMPT_CHARS] + "... [recorte]"

    limit_note = "Todas as linhas retornadas estão abaixo."
    if truncated or len(compacted) > len(shown):
        limit_note = (
            f"A resposta deve usar só estes {len(shown)} códigos. "
            "Há mais códigos do que os exibidos aqui; avise isso na avaliação."
        )

    return f"""
Organize a resposta somente neste JSON, sem markdown e sem texto fora dele:
{{
  "vehicle": "marca e modelo, como Jeep Compass",
  "year": 2020,
  "assessment": "avaliação geral, objetiva e baseada nas aplicações encontradas",
  "products": [
    {{
      "position": "dianteiro",
      "type": "ventilado",
      "assessment": "avaliação da utilização deste grupo no veículo e ano pedidos",
      "codes": [{{"brand": "Fremax", "code": "BD3608"}}]
    }}
  ]
}}

Regras:
- Use somente linhas do resultado. Não invente marca, código, posição ou tipo.
- vehicle junta make e model. year é o ano pedido, se estiver entre year_start e year_end; senão use year_start.
- Agrupe por posição (dianteiro, traseiro ou o que a descrição disser) e por tipo (ventilado, solido ou o que a descrição/tipo disser).
- Em codes, brand é a marca da peça e code é o codigo. Não repita o mesmo par.
- assessment geral explica a utilização das peças no contexto do veículo/ano solicitado.
- assessment de cada produto informa posição, tipo, cobertura de anos e se há variações que exigem conferência.
- Não invente especificações. Quando versão, motorização ou posição não estiver clara, diga que é necessário conferir catálogo, chassi ou medidas antes da instalação.
- Não afirme que a montagem é garantida; descreva apenas o que as aplicações encontradas sustentam.
- Se não houver linhas, devolva vehicle, year e products vazio.
- Se a lista estiver cortada, inclua só os itens recebidos.

Pergunta:
{user_question}

Consulta executada:
{command}

Códigos considerados: {len(shown)}
{limit_note}

Resultado:
{payload}
""".strip()


def _cell(row, *names):
    pairs = [(str(key).lower(), value) for key, value in row.items()]
    for name in names:
        for key, value in pairs:
            if key == name and value not in (None, ""):
                return str(value).strip()
    for name in names:
        for key, value in pairs:
            if key.endswith(name) and value not in (None, ""):
                return str(value).strip()
    return ""


def _label(text):
    cleaned = text.replace("_", " ").strip().lower()
    names = {
        "filtro ar": "Filtro de ar",
        "disco freio": "Disco de freio",
        "pastilha freio": "Pastilha de freio",
    }
    return names.get(cleaned, cleaned.capitalize() if cleaned else "Peça")


def organize_parts(user_question, rows):
    """Agrupa as linhas da consulta no formato de catálogo de peças."""
    import re

    year_match = re.search(r"\b(19|20)\d{2}\b", user_question or "")
    engine_match = re.search(r"\b\d\.\d\b", user_question or "")
    asked_year = int(year_match.group(0)) if year_match else None
    asked_engine = engine_match.group(0) if engine_match else ""

    grouped = {}
    vehicle = ""
    engine = asked_engine
    kind = ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _cell(row, "codigo", "code", "pn")
        brand = _cell(row, "marca", "brand") or "Marca não informada"
        if not code:
            continue
        description = _cell(row, "descricao", "description")
        raw_kind = _cell(row, "tipo", "type")
        blob = f"{description} {raw_kind}".lower()
        position = "geral"
        for name in ("dianteiro", "traseiro", "esquerdo", "direito"):
            if name in blob:
                position = name
                break
        part_type = _label(raw_kind) if raw_kind else "Peça"
        for name in ("ventilado", "sólido", "solido", "paralela", "leve"):
            if name in blob:
                part_type = "solido" if name == "sólido" else name
                break
        make = _cell(row, "make", "marca_veiculo")
        model = _cell(row, "model", "modelo")
        if make or model:
            vehicle = " ".join(part for part in (make, model) if part)
        variant = _cell(row, "variant", "engine", "motor")
        if not engine and variant:
            found = re.search(r"\b\d\.\d\b", variant)
            engine = found.group(0) if found else variant
        if raw_kind and not kind:
            kind = _label(raw_kind)
        key = (position, part_type)
        bucket = grouped.setdefault(key, [])
        if not any(item["code"] == code and item["brand"] == brand for item in bucket):
            bucket.append({
                "brand": brand,
                "code": code,
                "description": description,
                "application": " ".join(part for part in (vehicle, str(asked_year or ""), engine) if part),
            })

    products = []
    for (position, part_type), codes in grouped.items():
        for index, item in enumerate(codes):
            siblings = [
                {"brand": other["brand"], "code": other["code"]}
                for other_index, other in enumerate(codes)
                if other_index != index
            ]
            products.append({
                "position": position,
                "type": part_type,
                "brand": item["brand"],
                "code": item["code"],
                "description": item["description"],
                "application": item["application"],
                "equivalents": siblings[:6],
                "extra": max(len(siblings) - 6, 0),
            })

    title_kind = kind or "Peça"
    title_bits = [title_kind, "para" if vehicle else "", vehicle, engine, str(asked_year or "")]
    title = " ".join(bit for bit in title_bits if bit).strip()
    application = " · ".join(bit for bit in (vehicle, str(asked_year or ""), f"motor {engine}" if engine else "") if bit)
    return {
        "title": title or (user_question or "Peças"),
        "vehicle": vehicle,
        "year": asked_year,
        "engine": engine,
        "application": application,
        "products": products,
    }


class NaturalAnswer:
    """Transforma as linhas de uma consulta em uma resposta em linguagem natural."""

    def __init__(self, user_question, command, rows, truncated=False):
        self.agent = MainAgent()
        self.text = self._answer(user_question, command, rows, truncated)

    def _answer(self, user_question, command, rows, truncated):
        prompt = build_answer_prompt(user_question, command, rows, truncated)
        content = self.agent.ask_openai(prompt)
        if isinstance(content, dict):
            raise RuntimeError(content.get("error") or "Falha ao gerar a resposta.")
        text = str(content).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[: text.rfind("```")].strip()
        if not text:
            raise RuntimeError("O modelo devolveu uma resposta vazia.")
        return text
