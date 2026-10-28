import numpy as np
import skfuzzy as fuzz

def make_mf(kind: str, x: np.ndarray, params):
    params = list(params)
    if kind == "tri":
        return fuzz.trimf(x, params)
    if kind == "trap":
        return fuzz.trapmf(x, params)
    raise ValueError(f"Unknown MF kind: {kind}")

def build_universe(col: str) -> np.ndarray:
    ranges = {
        "utilization": (40, 120), "defect_rate": (0, 15),
        "downtime_pct": (0, 30), "overdue_orders": (0, 40),
        "staff_availability": (60, 100), "energy_overrun": (-10, 30),
        "risk_score": (0, 100),
    }
    lo, hi = ranges[col]
    return np.linspace(lo, hi, 501)

def membership_degrees(value: float, terms: dict) -> dict:
    result = {}
    for name, t in terms.items():
        x = np.array([value])
        params = sorted(t["params"]) # Сортировка на всякий случай
        kind = t.get("kind", "trap" if len(params) == 4 else "tri")
        if kind == "tri":
            mu = fuzz.trimf(np.array([value]), params)
        else:
            mu = fuzz.trapmf(np.array([value]), params)
        result[name] = float(mu[0])
    return result