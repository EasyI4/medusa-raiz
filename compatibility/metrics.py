from __future__ import annotations

from typing import Iterable


def classification_metrics(
    predicted_positive: Iterable[str],
    expected_positive: Iterable[str],
) -> dict[str, float | int]:
    predicted = set(predicted_positive)
    expected = set(expected_positive)
    true_positive = len(predicted & expected)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)
    precision = true_positive / (true_positive + false_positive) if predicted else 0.0
    recall = true_positive / (true_positive + false_negative) if expected else 0.0
    return {
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }
