import numpy as np
from scipy.optimize import minimize

from .fuzzy_systems import MamdaniSystem
from .data_pipeline import FEATURES


def extract_params(system: MamdaniSystem):
    keys = [
        ("defect_rate", "high", 3),
        ("downtime_pct", "high", 3),
        ("staff_availability", "low", 2),
        ("energy_overrun", "high", 3),
    ]
    values = []
    for var, term, idx in keys:
        values.append(system.terms[var][term][idx])
    return keys, np.array(values, dtype=float)


def apply_params(system: MamdaniSystem, keys, values):
    for (var, term, idx), v in zip(keys, values):
        system.terms[var][term][idx] = float(v)


def objective(values, system, keys, X_train, y_train, penalty=1e6):
    if np.any(values < 0) or np.any(values > 100):
        return penalty

    apply_params(system, keys, values)
    system._build_control_system()

    preds = []
    for row in X_train:
        inputs = {k: float(v) for k, v in row.items()}
        try:
            preds.append(system.predict(inputs))
        except Exception:
            return penalty

    preds = np.array(preds)
    rmse = float(np.sqrt(np.mean((preds - y_train) ** 2)))
    return rmse


def optimize_mamdani(df_train, df_val, n_iter=30):
    system = MamdaniSystem()
    keys, x0 = extract_params(system)

    X_train = df_train[FEATURES].to_dict("records")
    y_train = df_train["expert_risk"].values

    bounds = [(0, 100)] * len(x0)

    res = minimize(
        objective,
        x0,
        args=(system, keys, X_train, y_train),
        method="Powell",
        bounds=bounds,
        options={"maxiter": n_iter, "xtol": 1e-3, "ftol": 1e-3},
    )
    apply_params(system, keys, res.x)
    system._build_control_system()

    rmse_before = objective(x0, MamdaniSystem(), keys, X_train, y_train)
    rmse_after = objective(res.x, system, keys, X_train, y_train)

    return {
        "params_before": x0.tolist(),
        "params_after": res.x.tolist(),
        "rmse_before": rmse_before,
        "rmse_after": rmse_after,
        "optimized_system": system,
    }