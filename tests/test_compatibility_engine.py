import json
import unittest
from pathlib import Path

from compatibility.engine import CompatibilityEngine
from compatibility.intent_parser import IntentParser
from compatibility.metrics import classification_metrics
from compatibility.models import CompatibilityStatus, NormalizedQuery
from compatibility.normalization import normalize_intent, normalize_part_family
from compatibility.repository import PartCandidateRepository


FIXTURES = Path(__file__).parent / "fixtures" / "part-compatibility"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def intent_from_fixture(fixture):
    query = fixture["query"]
    return NormalizedQuery(
        raw_query=query["raw_query"],
        manufacturer=query.get("manufacturer"),
        model=query.get("model"),
        year=query.get("year"),
        part_family=query.get("part_family"),
        position=query.get("position"),
        engine=query.get("engine"),
    )


def rows_for_code(
    code,
    family,
    manufacturer,
    model,
    year_start,
    year_end,
    position=None,
    engine=None,
    description=None,
):
    description = description or family.replace("_", " ")
    position_text = f" {position}" if position else ""
    engine_text = f" {engine}" if engine else ""
    specs = {
        "_rag_text": (
            f"{description}{position_text} | Aplicações: "
            f"{manufacturer} {model}{engine_text} {year_start}-{year_end}"
        ),
        "position": position,
        "engine": engine,
    }
    base = {
        "codigo": code,
        "marca": "MARCA TESTE",
        "descricao": f"{description}{position_text}",
        "tipo": family,
        "make": manufacturer,
        "model": model,
        "variant": engine,
        "year_start": year_start,
        "year_end": year_end,
        "specs": specs,
    }
    return [
        {**base, "fonte": "fabricante_oficial", "source_tier": "MANUFACTURER"},
        {**base, "fonte": "catalogo_tecnico", "source_tier": "DISTRIBUTOR"},
    ]


class NormalizationTests(unittest.TestCase):
    def test_part_family_disambiguates_disc(self):
        self.assertEqual(normalize_part_family("disco de freio"), "DISCO_FREIO")
        self.assertEqual(normalize_part_family("disco de embreagem"), "DISCO_EMBREAGEM")
        self.assertIsNone(normalize_part_family("disco"))

    def test_ai_payload_is_normalized_without_losing_engine(self):
        intent = normalize_intent(
            "Pastilha traseira Civic Touring 1.5 Turbo 2018",
            {
                "manufacturer": "Honda",
                "model": "Civic",
                "year": 2018,
                "part_family": "PASTILHA_FREIO",
                "position": "traseira",
                "engine": "1.5 Turbo",
                "trim": "Touring",
            },
        )
        self.assertEqual(intent.manufacturer, "HONDA")
        self.assertEqual(intent.model, "CIVIC")
        self.assertEqual(intent.position, "REAR")
        self.assertEqual(intent.engine, "1.5 TURBO")
        self.assertEqual(intent.trim, "TOURING")

    def test_ai_is_primary_intent_parser(self):
        class FakeAgent:
            def ask_openai(self, _prompt):
                return json.dumps({
                    "manufacturer": "Honda",
                    "model": "Civic",
                    "year": 2018,
                    "part_family": "PASTILHA_FREIO",
                    "position": "FRONT",
                    "engine": "2.0",
                    "market": "BR",
                })

        intent = IntentParser(agent=FakeAgent()).parse("consulta livre")
        self.assertEqual(intent.parser, "ai")
        self.assertEqual(intent.part_family, "PASTILHA_FREIO")
        self.assertEqual(intent.model, "CIVIC")

    def test_query_builder_is_parameterized_and_limited(self):
        repository = PartCandidateRepository(
            driver="PostgreSQL", server="x", database="x", uid="x", pwd="x",
            max_rows=250,
        )
        intent = NormalizedQuery(
            raw_query="x",
            manufacturer="HONDA",
            model="CIVIC' OR 1=1 --",
            year=2018,
            part_family="PASTILHA_FREIO",
        )
        query, params = repository.build_query(intent)
        self.assertNotIn(intent.model, query)
        self.assertIn("%s", query)
        self.assertEqual(params[-1], 251)
        self.assertNotRegex(query.upper(), r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE)\b")

    def test_precision_and_recall_metrics(self):
        metrics = classification_metrics(
            predicted_positive={"A", "B"},
            expected_positive={"A", "B", "C"},
        )
        self.assertEqual(metrics["true_positives"], 2)
        self.assertEqual(metrics["false_positives"], 0)
        self.assertEqual(metrics["false_negatives"], 1)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 0.6667)


class RegressionTests(unittest.TestCase):
    def test_compass_disc_rejects_clutch_disc(self):
        fixture = load_fixture("compass-disc-2020.json")
        intent = intent_from_fixture(fixture)
        rows = []
        for code in fixture["accepted"]:
            rows.extend(rows_for_code(
                code, "DISCO_FREIO", "JEEP", "COMPASS", 2017, 2022,
                position=fixture["position_by_code"][code],
                description="DISCO DE FREIO",
            ))
        rows.extend(rows_for_code(
            "5708", "DISCO_EMBREAGEM", "JEEP", "COMPASS", 2017, 2022,
            description="DISCO DE EMBREAGEM",
        ))
        rows.extend(rows_for_code(
            "35897", "DISCO_EMBREAGEM", "JEEP", "COMPASS", 2017, 2022,
            description="DISCO DE EMBREAGEM MOTOCICLETA",
        ))
        rows.extend(rows_for_code(
            "BD5086", "DISCO_FREIO", "JEEP", "COMPASS", 2017, 2022,
            description="DISCO DE FREIO",
        ))

        result = CompatibilityEngine().evaluate(intent, rows)
        visible = {item.candidate.code for item in result.decisions}
        rejected = {item.candidate.code for item in result.rejected}
        self.assertEqual(visible, set(fixture["accepted"]))
        self.assertEqual(rejected, set(fixture["rejected"]))
        self.assertTrue(all(
            item.compatibility is CompatibilityStatus.CONFIRMED
            for item in result.decisions
        ))

    def test_civic_pads_preserve_front_and_rear_families(self):
        fixture = load_fixture("civic-pads-2018.json")
        intent = intent_from_fixture(fixture)
        rows = []
        for code in fixture["accepted_front"]:
            rows.extend(rows_for_code(
                code, "PASTILHA_FREIO", "HONDA", "CIVIC", 2017, 2021,
                position="FRONT", description="PASTILHA DE FREIO",
            ))
        for code in fixture["accepted_rear"]:
            rows.extend(rows_for_code(
                code, "PASTILHA_FREIO", "HONDA", "CIVIC", 2017, 2021,
                position="REAR", description="PASTILHA DE FREIO",
            ))
        for code in fixture["rejected"]:
            rows.extend(rows_for_code(
                code, "PASTILHA_FREIO", "HONDA", "CIVIC", 2012, 2016,
                position="FRONT", description="PASTILHA DE FREIO",
            ))

        result = CompatibilityEngine().evaluate(intent, rows)
        visible = {item.candidate.code for item in result.decisions}
        rejected = {item.candidate.code for item in result.rejected}
        self.assertEqual(
            visible,
            set(fixture["accepted_front"] + fixture["accepted_rear"]),
        )
        self.assertEqual(rejected, set(fixture["rejected"]))
        positions = {item.candidate.position for item in result.decisions}
        self.assertEqual(positions, {"FRONT", "REAR"})

    def test_civic_air_filter_is_ambiguous_without_engine(self):
        fixture = load_fixture("civic-air-filter-2017.json")
        intent = intent_from_fixture(fixture)
        rows = []
        for engine, codes in fixture["engine_groups"].items():
            for code in codes:
                rows.extend(rows_for_code(
                    code, "FILTRO_AR_MOTOR", "HONDA", "CIVIC", 2017, 2021,
                    engine=engine, description="FILTRO DE AR MOTOR",
                ))
        rows.extend(rows_for_code(
            "C24021", "FILTRO_AR_MOTOR", "HONDA", "CIVIC", 2017, 2021,
            engine="2.0", description="FILTRO DE AR MOTOR",
        ))

        result = CompatibilityEngine().evaluate(intent, rows)
        visible = {item.candidate.code for item in result.decisions}
        rejected = {item.candidate.code for item in result.rejected}
        expected = {
            code
            for codes in fixture["engine_groups"].values()
            for code in codes
        }
        self.assertEqual(visible, expected)
        self.assertIn("C24021", rejected)
        self.assertTrue(result.metrics["requires_engine_selection"])
        self.assertTrue(all(
            item.compatibility is CompatibilityStatus.AMBIGUOUS
            for item in result.decisions
        ))

    def test_explicit_wrong_engine_is_hard_rejected(self):
        intent = NormalizedQuery(
            raw_query="Filtro de ar Civic 1.5 Turbo 2017",
            manufacturer="HONDA",
            model="CIVIC",
            year=2017,
            part_family="FILTRO_AR_MOTOR",
            engine="1.5 TURBO",
        )
        rows = rows_for_code(
            "ARL1043", "FILTRO_AR_MOTOR", "HONDA", "CIVIC", 2017, 2021,
            engine="2.0", description="FILTRO DE AR MOTOR",
        )
        result = CompatibilityEngine().evaluate(intent, rows)
        self.assertFalse(result.decisions)
        self.assertEqual(result.rejected[0].compatibility, CompatibilityStatus.REJECTED)
        self.assertIn("ENGINE_MISMATCH", result.rejected[0].reasons[0])

    def test_original_part_is_prioritized_within_same_classification(self):
        intent = NormalizedQuery(
            raw_query="Disco de freio Compass 2020",
            manufacturer="JEEP",
            model="COMPASS",
            year=2020,
            part_family="DISCO_FREIO",
        )
        parallel = rows_for_code(
            "PAR1", "DISCO_FREIO", "JEEP", "COMPASS", 2017, 2022,
            description="DISCO DE FREIO",
        )
        original = rows_for_code(
            "OEM1", "DISCO_FREIO", "JEEP", "COMPASS", 2017, 2022,
            description="DISCO DE FREIO",
        )
        for index, row in enumerate(original):
            row["marca"] = "JEEP ORIGINAL"
            row.pop("source_tier", None)
            row["fonte"] = f"oem_catalog_{index}"

        result = CompatibilityEngine().evaluate(intent, parallel + original)
        self.assertEqual(result.decisions[0].candidate.code, "OEM1")


if __name__ == "__main__":
    unittest.main()
