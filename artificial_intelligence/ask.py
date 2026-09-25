import json
import os
import re
import unicodedata

from artificial_intelligence.answer import NaturalAnswer, jsonable, organize_parts
from artificial_intelligence.sql_guard import extract_sql, is_read_query
from compatibility.repository import UnsupportedIntentError
from compatibility.service import PartCompatibilityService
from response.formatted import Formatted
from sql_database.read_query import SqlDatabaseReadQuery


_QUESTION_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "da", "das", "de", "do", "dos", "e",
    "em", "me", "meu", "minha", "o", "os", "ou", "para", "por", "preciso",
    "procuro", "qual", "quero", "tem", "uma", "um", "carro", "peca", "pecas",
}


def _normalize_words(value):
    return re.findall(r"[a-z0-9]+", _normalize_text(value))


def _normalize_text(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.lower()


def _current_question(value):
    marker = "Pergunta atual:"
    text = str(value or "")
    return text.rsplit(marker, 1)[-1].strip() if marker in text else text.strip()


def _supports_vehicle_evidence(evidence, vehicle_words, requested_year):
    if not vehicle_words:
        return True

    normalized = _normalize_text(evidence)
    if not normalized:
        return False

    anchor = max(vehicle_words, key=len)
    positions = [match.start() for match in re.finditer(rf"\b{re.escape(anchor)}\b", normalized)]
    for position in positions:
        window = normalized[max(0, position - 50):position + 220]
        if not all(re.search(rf"\b{re.escape(word)}\b", window) for word in vehicle_words):
            continue
        if requested_year is None:
            return True
        if re.search(rf"\b{requested_year}\b", window):
            return True
        for start, end in re.findall(
            r"\b((?:19|20)\d{2})\s*(?:-|a|ate)?\s*((?:19|20)\d{2})\b",
            window,
        ):
            if int(start) <= requested_year <= int(end):
                return True
    return False


def filter_relevant_part_rows(user_question, rows):
    """
    Mantém um código somente quando alguma descrição dele corresponde à
    família de peça solicitada. A validação é genérica e não depende de
    veículo, fabricante ou códigos específicos.
    """
    if not rows:
        return []

    current_question = _current_question(user_question)
    query_words = set(_normalize_words(current_question))
    model_words = set()
    make_words = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_words.update(set(_normalize_words(row.get("model"))) & query_words)
        make_words.update(set(_normalize_words(row.get("make"))) & query_words)

    vehicle_words = model_words or make_words
    requested_year_match = re.search(r"\b(19|20)\d{2}\b", current_question)
    requested_year = int(requested_year_match.group(0)) if requested_year_match else None
    part_words = {
        word for word in _normalize_words(current_question)
        if word not in _QUESTION_STOPWORDS
        and word not in model_words
        and word not in make_words
        and not word.isdigit()
    }

    codes_in_question = {
        "".join(_normalize_words(row.get("codigo"))).upper()
        for row in rows
        if isinstance(row, dict) and row.get("codigo")
        and "".join(_normalize_words(row.get("codigo"))).lower()
        in "".join(_normalize_words(current_question)).lower()
    }
    if not part_words and not codes_in_question:
        return rows

    valid_codes = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = "".join(_normalize_words(row.get("codigo"))).upper()
        description_words = set(_normalize_words(row.get("descricao")))
        family_matches = code in codes_in_question or (
            part_words and part_words.issubset(description_words)
        )
        evidence_matches = _supports_vehicle_evidence(
            row.get("specs") or row.get("descricao"),
            vehicle_words,
            requested_year,
        )
        if family_matches and evidence_matches:
            valid_codes.add(code)

    return [
        row for row in rows
        if isinstance(row, dict)
        and "".join(_normalize_words(row.get("codigo"))).upper() in valid_codes
    ]


def _equivalents_from_specs(specs):
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

    equivalents = []
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        code = str(candidate.get("code") or candidate.get("codigo") or "").strip()
        brand = str(candidate.get("brand") or candidate.get("marca") or "").strip()
        key = code.replace(" ", "").upper()
        if code and key not in seen:
            equivalents.append({"code": code, "brand": brand})
            seen.add(key)
    return equivalents


class Ask:
    """
    Pergunta em linguagem natural, executa a leitura no banco
    e devolve uma resposta escrita a partir das linhas.
    """

    def __init__(self, driver, server, database, uid, pwd, schema, user_question, type_sql):
        self.driver = driver
        self.server = server
        self.database = database
        self.uid = uid
        self.pwd = pwd
        self.schema = schema
        self.user_question = user_question
        self.type_sql = type_sql
        self.generated = self.run()

    def run(self):
        use_engine = (
            "postgres" in self.type_sql.strip().lower()
            and os.getenv("COMPATIBILITY_ENGINE", "deterministic").lower() != "legacy"
        )
        if not use_engine:
            return self._run_legacy()
        try:
            service = PartCompatibilityService(
                driver=self.driver,
                server=self.server,
                database=self.database,
                uid=self.uid,
                pwd=self.pwd,
            )
            return service.search(_current_question(self.user_question))
        except (UnsupportedIntentError, ValueError) as error:
            return {
                "success": False,
                "error": "INVALID_PART_QUERY",
                "message": str(error),
                "data": [],
            }

    def _run_legacy(self):
        formatted = Formatted(
            self.driver,
            self.server,
            self.database,
            self.uid,
            self.pwd,
            self.schema,
        )
        raw_sql = formatted.response_sql(
            self.user_question,
            type_sql=self._dialect_label(),
            only_select=True,
        )

        try:
            command = extract_sql(raw_sql)
        except ValueError as error:
            return {
                "success": False,
                "error": str(error),
                "message": "Falha ao gerar a consulta a partir da pergunta.",
            }

        if not is_read_query(command):
            return {
                "success": False,
                "error": "A pergunta não gerou uma consulta somente de leitura.",
                "message": "A resposta em linguagem natural usa apenas SELECT.",
                "command": command,
            }

        executed = SqlDatabaseReadQuery(
            driver=self.driver,
            server=self.server,
            database=self.database,
            uid=self.uid,
            pwd=self.pwd,
            command_query=command,
        ).result

        if not executed.get("success"):
            return {
                "success": False,
                "error": executed.get("error", "Erro desconhecido"),
                "message": executed.get("message", "Falha ao executar a consulta."),
                "command": command,
            }

        if executed.get("row_count") == 0:
            retried = self._retry_empty(formatted, command)
            if retried is not None:
                command = retried["command"]
                executed = retried["executed"]

        rows = filter_relevant_part_rows(
            self.user_question,
            jsonable(executed["data"]),
        )
        for row in rows:
            row["equivalents"] = _equivalents_from_specs(row.get("specs"))
            row.pop("specs", None)
        catalog = organize_parts(self.user_question, rows)
        answer_text = NaturalAnswer(
            user_question=self.user_question,
            command=command,
            rows=rows,
            truncated=executed["truncated"],
        ).text

        return {
            "success": True,
            "message": "Resposta gerada a partir do resultado da consulta.",
            "answer": answer_text,
            "catalog": catalog,
            "command": command,
            "row_count": len(rows),
            "truncated": executed["truncated"],
            "data": rows,
        }

    def _retry_empty(self, formatted, failed_command):
        try:
            raw_sql = formatted.retry_select(
                self.user_question,
                self._dialect_label(),
                failed_command,
            )
            command = extract_sql(raw_sql)
        except (ValueError, RuntimeError):
            return None

        if not is_read_query(command):
            return None

        executed = SqlDatabaseReadQuery(
            driver=self.driver,
            server=self.server,
            database=self.database,
            uid=self.uid,
            pwd=self.pwd,
            command_query=command,
        ).result
        if not executed.get("success") or executed.get("row_count") == 0:
            return None
        return {"command": command, "executed": executed}

    def _dialect_label(self):
        key = self.type_sql.strip().lower()
        if key in ("sql server", "sqlserver", "mssql"):
            return "SQL SERVER"
        if key == "mysql":
            return "MYSQL"
        if key in ("postgresql", "postgres", "postgree"):
            return "POSTGRESQL"
        raise ValueError(
            f"Tipo de SQL desconhecido: '{self.type_sql}'. Use SQL SERVER, MYSQL ou POSTGRESQL."
        )
