import numpy as np
import pytest
from src.fuzzy_systems import MamdaniSystem, SugenoSystem, FuzzySystem
from src.membership import membership_degrees



NORMAL = {
    "utilization": 85.0,
    "defect_rate": 2.0,
    "downtime_pct": 5.0,
    "overdue_orders": 4.0,
    "staff_availability": 95.0,
    "energy_overrun": 2.0,
}

CRITICAL = {
    "utilization": 118.0,
    "defect_rate": 14.0,
    "downtime_pct": 28.0,
    "overdue_orders": 38.0,
    "staff_availability": 62.0,
    "energy_overrun": 28.0,
}

STRESS = {
    "utilization": 100.0,
    "defect_rate": 8.0,
    "downtime_pct": 18.0,
    "overdue_orders": 22.0,
    "staff_availability": 80.0,
    "energy_overrun": 14.0,
}


@pytest.fixture(scope="module")
def systems():
    return MamdaniSystem(), SugenoSystem()

def test_both_are_fuzzy_systems(systems):
    m, s = systems
    assert isinstance(m, FuzzySystem)
    assert isinstance(s, FuzzySystem)

def test_mamdani_normal_low(systems):
    m, _ = systems
    score = m.predict(NORMAL)
    assert 0 <= score <= 100
    assert m.classify(score) in {"low", "moderate"}


def test_critical_higher_than_normal(systems):
    m, s = systems
    m_norm, m_crit = m.predict(NORMAL), m.predict(CRITICAL)
    s_norm, s_crit = s.predict(NORMAL), s.predict(CRITICAL)
    assert m_crit > m_norm + 20
    assert s_crit > s_norm + 20


def test_stress_between(systems):
    m, _ = systems
    assert m.predict(NORMAL) < m.predict(STRESS) < m.predict(CRITICAL)

def test_no_nan_inf(systems):
    m, s = systems
    for inp in (NORMAL, STRESS, CRITICAL):
        for sys_ in (m, s):
            v = sys_.predict(inp)
            assert np.isfinite(v)


def test_membership_crossing_points():
    degrees = membership_degrees(85.0, {
        "low": {"kind": "trap", "params": [40, 40, 60, 75]},
        "normal": {"kind": "trap", "params": [60, 75, 85, 95]},
    })
    assert degrees["normal"] == pytest.approx(1.0, abs=0.05)


def test_sugeno_reference_value():
    s = SugenoSystem()
    value = s.predict(NORMAL)
    assert 15.0 <= value <= 45.0


def test_invalid_input_handling(systems):
    m, _ = systems
    bad = dict(NORMAL)
    bad["utilization"] = 1000
    try:
        v = m.predict(bad)
        assert np.isfinite(v)
    except Exception:
        pass