"""Motor determinístico de compatibilidade de autopeças."""

from compatibility.engine import CompatibilityEngine
from compatibility.intent_parser import IntentParser
from compatibility.models import CompatibilityStatus, NormalizedQuery

__all__ = [
    "CompatibilityEngine",
    "CompatibilityStatus",
    "IntentParser",
    "NormalizedQuery",
]
