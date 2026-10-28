import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
import skfuzzy as fuzz

from .membership import build_universe
from .data_pipeline import FEATURES, correlation_matrix


def plot_descriptive(df: pd.DataFrame, save_path="reports/descriptive.png"):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, col in zip(axes.ravel(), FEATURES):
        sns.histplot(df[col], kde=True, ax=ax)
        ax.set_title(col)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_correlation(df: pd.DataFrame, save_path="reports/correlation.png"):
    corr = correlation_matrix(df)
    plt.figure(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
    plt.title("Корреляции показателей")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_risk_distribution(df: pd.DataFrame, save_path="reports/risk_dist.png"):
    plt.figure(figsize=(8, 5))
    sns.histplot(df["expert_risk"], kde=True, bins=30)
    plt.title("Распределение экспертной оценки риска")
    plt.xlabel("expert_risk")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_membership_functions(system, save_path="reports/mf_all.png"):
    variables = ["utilization", "defect_rate", "downtime_pct",
                 "overdue_orders", "staff_availability", "energy_overrun", "risk_score"]
    fig, axes = plt.subplots(4, 2, figsize=(14, 12))
    axes = axes.ravel()
    for ax, var in zip(axes, variables):
        x = build_universe(var)
        for term, params in system.terms[var].items():
            params = sorted(list(params))
            if len(params) == 4:
                y = fuzz.trapmf(x, params)
            else:
                y = fuzz.trimf(x, params)
            ax.plot(x, y, label=term)
        ax.set_title(var)
        ax.legend(fontsize=7)
    axes[-1].axis("off")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_rules_graph(system, save_path="reports/rules_graph.png"):
    G = nx.DiGraph()
    for rule in system.rules:
        node = rule.rid
        for var, term, _ in rule.antecedents:
            G.add_edge(f"{var}:{term}", node)
        G.add_edge(node, f"risk:{rule.consequent}")
    pos = nx.spring_layout(G, seed=42, k=0.7)
    plt.figure(figsize=(16, 12))
    nx.draw(
        G, pos, with_labels=True, node_size=1200, font_size=7,
        node_color="#cce5ff", edge_color="#888888", arrows=True,
    )
    plt.title("Граф базы правил")
    plt.savefig(save_path)
    plt.close()


def plot_mamdani_vs_sugeno(df_sample: pd.DataFrame, mamdani, sugeno,
                           save_path="reports/mamdani_vs_sugeno.png"):
    m_scores, s_scores = [], []
    for _, row in df_sample.iterrows():
        inp = {k: float(row[k]) for k in FEATURES}
        m_scores.append(mamdani.predict(inp))
        s_scores.append(sugeno.predict(inp))
    plt.figure(figsize=(8, 5))
    plt.scatter(m_scores, s_scores, alpha=0.6)
    plt.plot([0, 100], [0, 100], "r--", label="y = x")
    plt.xlabel("Мамдани")
    plt.ylabel("Сугено")
    plt.title("Сравнение методов вывода")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_clusters(df, X_scaled, labels, save_path="reports/clusters.png"):
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2)
    Z = pca.fit_transform(X_scaled)
    plt.figure(figsize=(8, 6))
    plt.scatter(Z[:, 0], Z[:, 1], c=labels, cmap="viridis", s=12)
    plt.title("FCM-кластеры (PCA-проекция)")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()