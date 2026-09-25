from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from compatibility.models import NormalizedQuery
from compatibility.normalization import FAMILY_REQUIRED_TERMS
from sql_database.connection import SqlDatabaseConnection


class UnsupportedIntentError(ValueError):
    pass


@dataclass(frozen=True)
class RetrievalResult:
    rows: list[dict[str, Any]]
    evidence_rows: list[dict[str, Any]]
    truncated: bool
    limit: int


class PartCandidateRepository:
    """Busca candidatos com SQL parametrizado; não decide compatibilidade."""

    def __init__(
        self,
        driver: str,
        server: str,
        database: str,
        uid: str,
        pwd: str,
        max_rows: int = 2500,
        timeout_ms: int = 20000,
    ):
        self.connection_args = {
            "driver": driver,
            "server": server,
            "database": database,
            "uid": uid,
            "pwd": pwd,
        }
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms

    def search(self, intent: NormalizedQuery) -> RetrievalResult:
        query, params = self.build_query(intent)

        connection = SqlDatabaseConnection(**self.connection_args)
        try:
            cursor = connection.conn.cursor()
            try:
                if connection._use_postgres():
                    cursor.execute("SET LOCAL statement_timeout = %s", (self.timeout_ms,))
                cursor.execute(query, tuple(params))
                columns = [column[0] for column in cursor.description]
                fetched = cursor.fetchall()
                part_codes = sorted({
                    str(row[1] or "").strip()
                    for row in fetched
                    if row[1]
                })
                evidence_rows: list[dict[str, Any]] = []
                if part_codes and connection._use_postgres():
                    cursor.execute(
                        """
                        SELECT *
                        FROM public.part_evidence
                        WHERE part_code_norm = ANY(%s)
                        ORDER BY confidence DESC NULLS LAST, id
                        LIMIT %s
                        """,
                        (part_codes, self.max_rows * 4),
                    )
                    evidence_columns = [column[0] for column in cursor.description]
                    evidence_rows = [
                        dict(zip(evidence_columns, row))
                        for row in cursor.fetchall()
                    ]
            finally:
                cursor.close()
        finally:
            connection.close()

        truncated = len(fetched) > self.max_rows
        rows = fetched[: self.max_rows]
        return RetrievalResult(
            rows=[dict(zip(columns, row)) for row in rows],
            evidence_rows=evidence_rows,
            truncated=truncated,
            limit=self.max_rows,
        )

    def build_query(self, intent: NormalizedQuery) -> tuple[str, list[Any]]:
        if not intent.part_family:
            raise UnsupportedIntentError(
                "Não foi possível identificar a família da peça com segurança."
            )
        if not intent.model:
            raise UnsupportedIntentError(
                "Informe o modelo do veículo para validar a aplicação."
            )

        required_terms = FAMILY_REQUIRED_TERMS.get(intent.part_family)
        if not required_terms:
            raise UnsupportedIntentError(
                f"A família {intent.part_family} ainda não possui regra de busca."
            )

        where = []
        params: list[Any] = []
        for term in required_terms:
            where.append("p.descricao ILIKE %s")
            params.append(f"%{term}%")
        where.append("v.model_norm ILIKE %s")
        params.append(f"%{intent.model}%")
        if intent.manufacturer:
            where.append("v.make_norm ILIKE %s")
            params.append(f"%{intent.manufacturer}%")
        if intent.year is not None:
            where.append("v.year_start IS NOT NULL")
            where.append("v.year_end IS NOT NULL")
            where.append("%s BETWEEN v.year_start AND v.year_end")
            params.append(intent.year)

        params.append(self.max_rows + 1)
        query = f"""
            SELECT DISTINCT
                p.codigo,
                p.codigo_norm,
                p.marca,
                p.fonte,
                p.descricao,
                p.specs,
                t.tipo,
                v.make_norm AS make,
                v.model_norm AS model,
                NULL::text AS variant,
                v.year_start,
                v.year_end,
                sr.tier AS source_tier,
                sr.variant_trusted
            FROM public.peca p
            JOIN public.peca_tipo t ON t.peca_id = p.id
            JOIN public.part_fitment f ON f.pn_norm = p.codigo_norm
            JOIN public.vehicle v ON v.id = f.vehicle_id
            LEFT JOIN public.source_registry sr
              ON lower(sr.source) = lower(p.fonte)
            WHERE {" AND ".join(where)}
            ORDER BY p.codigo
            LIMIT %s
        """

        return query, params
