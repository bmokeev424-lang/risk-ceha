import pandas as pd
from src.data_pipeline import generate_dataset, RANGES, validate_dataset


def test_reproducible_generation():
    a = generate_dataset(500, seed=123)
    b = generate_dataset(500, seed=123)
    pd.testing.assert_frame_equal(a, b)


def test_different_seeds_differ():
    a = generate_dataset(500, seed=1)
    b = generate_dataset(500, seed=2)
    assert not a.equals(b)


def test_ranges_respected():
    df = generate_dataset(1000, seed=7)
    for col, (lo, hi) in RANGES.items():
        assert df[col].min() >= lo
        assert df[col].max() <= hi


def test_no_missing_values():
    df = generate_dataset(300, seed=3)
    report = validate_dataset(df)
    assert all(v == 0 for v in report["missing"].values())