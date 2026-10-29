import os
import threading
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from src.data_pipeline import (
    FEATURES, generate_dataset, save_dataset, load_dataset,
    validate_dataset
)
from src.fuzzy_systems import MamdaniSystem, SugenoSystem
from src.clustering import evaluate_clusters, pick_best, prepare_features
from src.optimization import optimize_mamdani
from src import visualization as viz
from src.gui import RiskApp

def run_background_calculations():
    print("Запуск фоновых расчетов")
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    if not os.path.exists("data/production.csv"):
        df = generate_dataset(n=1500, seed=42)
        save_dataset(df, "data/production.csv")
    else:
        df = load_dataset("data/production.csv")

    print("Валидация:", validate_dataset(df))

    mamdani = MamdaniSystem()
    sugeno = SugenoSystem()

    sample = df.sample(20, random_state=1)
    rows = []
    for _, row in sample.iterrows():
        inp = {k: float(row[k]) for k in FEATURES}
        rows.append({
            "Mamdani": mamdani.predict(inp),
            "Sugeno": sugeno.predict(inp),
            "expert_risk": row["expert_risk"],
        })
    cmp_df = pd.DataFrame(rows)
    cmp_df["diff"] = (cmp_df["Mamdani"] - cmp_df["Sugeno"]).abs()
    cmp_df.to_csv("reports/mamdani_vs_sugeno.csv", index=False)
    cluster_results = evaluate_clusters(df, c_range=range(2, 7))
    best = pick_best(cluster_results)
    print(f"\nЛучшее число кластеров: {best['n_clusters']}, FPC={best['fpc']:.3f}")

    X_scaled, scaler = prepare_features(df)
    labels = np.argmax(best["membership"], axis=0)
    train = df.sample(frac=0.7, random_state=42)
    val = df.drop(train.index)
    opt = optimize_mamdani(train, val, n_iter=20)
    print(f"\nRMSE до оптимизации: {opt['rmse_before']:.3f}")
    print(f"RMSE после оптимизации: {opt['rmse_after']:.3f}")

    viz.plot_descriptive(df)
    viz.plot_correlation(df)
    viz.plot_risk_distribution(df)
    viz.plot_membership_functions(opt["optimized_system"])
    viz.plot_rules_graph(mamdani)
    viz.plot_mamdani_vs_sugeno(sample, mamdani, sugeno)
    viz.plot_clusters(df, X_scaled, labels)

    print("\n Фоновые расчеты и графики успешно завершены!")

def main():
    bg_thread = threading.Thread(target=run_background_calculations, daemon=True)
    bg_thread.start()
    print("Открытие приложения...")
    app = RiskApp()
    app.mainloop()

if __name__ == "__main__":
    main()