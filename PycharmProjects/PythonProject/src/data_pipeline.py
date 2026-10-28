import numpy as np
import pandas as pd

FEATURES = [
    "utilization", "defect_rate", "downtime_pct",
    "overdue_orders", "staff_availability", "energy_overrun",
]

RANGES = {
    "utilization": (40, 120), "defect_rate": (0, 15),
    "downtime_pct": (0, 30), "overdue_orders": (0, 40),
    "staff_availability": (60, 100), "energy_overrun": (-10, 30),
    "expert_risk": (0, 100),
}


def generate_dataset(n: int = 1500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    utilization = rng.normal(85, 12, n).clip(40, 120)
    defect_rate = rng.gamma(2.0, 1.5, n).clip(0, 15)
    downtime_pct = rng.gamma(2.0, 4.0, n).clip(0, 30)
    overdue_orders = rng.poisson(8, n).clip(0, 40).astype(int)
    staff_availability = rng.normal(88, 8, n).clip(60, 100)
    energy_overrun = rng.normal(6, 7, n).clip(-10, 30)

    risk = (
            0.4 * np.abs(utilization - 85) + 3.0 * defect_rate
            + 1.5 * downtime_pct + 1.2 * overdue_orders
            + 0.8 * (100 - staff_availability)
            + 0.7 * np.maximum(energy_overrun, 0)
    )
    risk = risk + rng.normal(0, 5, n)
    risk = np.clip(risk, 0, 100)

    return pd.DataFrame({
        "period": rng.integers(1, 13, n),
        "workshop": rng.choice(["A", "B", "C"], n),
        "shift": rng.choice([1, 2, 3], n),
        "utilization": utilization, "defect_rate": defect_rate,
        "downtime_pct": downtime_pct, "overdue_orders": overdue_orders,
        "staff_availability": staff_availability, "energy_overrun": energy_overrun,
        "expert_risk": risk,
    })


def save_dataset(df: pd.DataFrame, path: str = "data/production.csv") -> None:
    df.to_csv(path, index=False)


def load_dataset(path: str = "data/production.csv") -> pd.DataFrame:
    return pd.read_csv(path)


def validate_dataset(df: pd.DataFrame) -> dict:
    report = {"missing": df.isna().sum().to_dict(), "dtypes": df.dtypes.astype(str).to_dict()}
    out_of_range = {}
    for col, (lo, hi) in RANGES.items():
        if col in df.columns:
            bad = df[(df[col] < lo) | (df[col] > hi)]
            out_of_range[col] = len(bad)
    report["out_of_range"] = out_of_range

    outliers = {}
    for col in FEATURES + ["expert_risk"]:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
        outliers[col] = int(mask.sum())
    report["iqr_outliers"] = outliers
    return report


def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATURES + ["expert_risk"]].describe()


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATURES + ["expert_risk"]].corr()