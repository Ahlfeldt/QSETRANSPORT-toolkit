from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[2] / "src" / "python"
sys.path.insert(0, str(SRC))

from reporting.make_maps import classified_values, symmetric_thresholds


def test_symmetric_absolute_quantile_classes_are_zero_centered() -> None:
    pooled = pd.Series([-12, -8, -4, -1, 0, 2, 3, 6, 10, 20], dtype=float)
    thresholds = symmetric_thresholds(pooled)
    assert thresholds is not None
    assert np.all(thresholds > 0)
    assert np.all(np.diff(thresholds) > 0)

    q1, q2, q3 = thresholds
    values = pd.Series([-2 * q3, -q2, -0.5 * q1, 0, 0.5 * q1, q2, 2 * q3])
    classes, labels = classified_values(values, thresholds)
    assert classes.tolist() == [0, 1, 3, 3, 3, 5, 6]
    assert len(labels) == 7
    assert labels[3] == f"{-q1:.3g} to {q1:.3g}"


def test_repeated_magnitudes_use_symmetric_scale_fallback() -> None:
    thresholds = symmetric_thresholds(pd.Series([-2, -2, 0, 2, 2], dtype=float))
    np.testing.assert_allclose(thresholds, [1.0, 2.0, 4.0])


def test_all_zero_values_use_neutral_class() -> None:
    values = pd.Series([0.0, 0.0, np.nan])
    thresholds = symmetric_thresholds(values)
    classes, labels = classified_values(values, thresholds)
    assert thresholds is None
    assert classes.iloc[:2].tolist() == [3, 3]
    assert pd.isna(classes.iloc[2])
    assert labels == ["No change"]
