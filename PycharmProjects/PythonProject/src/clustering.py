import numpy as np
import skfuzzy as fuzz
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .data_pipeline import FEATURES

def prepare_features(df):
    X = df[FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, scaler

def evaluate_clusters(df, c_range=range(2, 7), m=2.0, seed=42):
    X_scaled, _ = prepare_features(df)
    results = []
    for c in c_range:
        cntr, u, u0, d, jm, p, fpc = fuzz.cluster.cmeans(
            X_scaled.T, c, m, error=0.005, maxiter=1000, seed=seed
        )
        labels = np.argmax(u, axis=0)
        try:
            sil = silhouette_score(X_scaled, labels)
        except ValueError:
            sil = float("nan")
        results.append({
            "n_clusters": c,
            "fpc": float(fpc),
            "silhouette": float(sil),
            "centers": cntr,
            "membership": u,
        })
    return results

def pick_best(results):
    def score(r):
        s = r["silhouette"]
        return (r["fpc"] if np.isnan(s) else r["fpc"] + s)  # простая эвристика
    return max(results, key=score)
def describe_clusters(centers, scaler):
    centers_orig = scaler.inverse_transform(centers)
    descriptions = []
    for i, row in enumerate(centers_orig):
        desc = {feat: round(float(val), 2) for feat, val in zip(FEATURES, row)}
        descriptions.append({"cluster": i, "center": desc})
    return descriptions