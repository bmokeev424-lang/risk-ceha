import json
from abc import ABC, abstractmethod
from typing import List

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from .membership import build_universe, membership_degrees
from .rules import Rule, build_rules


class FuzzySystem(ABC):
    name = "base"

    def __init__(self, config_path: str = "config/model.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.terms = self.config["terms"]
        self.rules: List[Rule] = build_rules()

    def classify(self, score: float) -> str:
        mu = membership_degrees(score, self._risk_terms())
        return max(mu, key=mu.get)

    def explain(self, inputs: dict, top_n: int = 3) -> List[dict]:
        strengths = []
        for rule in self.rules:
            s = self._rule_strength(rule, inputs)
            strengths.append({"rule": rule.rid, "text": self._rule_text(rule), "strength": s})
        strengths.sort(key=lambda x: x["strength"], reverse=True)
        return strengths[:top_n]

    def _risk_terms(self):
        out = {}
        for name, params in self.terms["risk_score"].items():
            kind = "trap" if len(params) == 4 else "tri"
            out[name] = {"kind": kind, "params": params}
        return out

    def _term_params(self, var: str, term: str):
        return self.terms[var][term]

    def _rule_text(self, rule: Rule) -> str:
        return f"ЕСЛИ {rule.antecedent_text()} ТО риск = {rule.consequent}"

    def _membership(self, var: str, term: str, value: float) -> float:
        params = self._term_params(var, term)
        kind = "trap" if len(params) == 4 else "tri"
        if kind == "trap":
            mu = fuzz.trapmf(np.array([value]), params)
        else:
            mu = fuzz.trimf(np.array([value]), params)
        return float(mu[0])

    def _rule_strength(self, rule: Rule, inputs: dict) -> float:
        vals = []
        for var, term, is_not in rule.antecedents:
            mu = self._membership(var, term, inputs[var])
            vals.append(1.0 - mu if is_not else mu)
        return float(min(vals)) if vals else 0.0

    @abstractmethod
    def predict(self, inputs: dict) -> float:
        ...

    def predict_with_details(self, inputs: dict) -> dict:
        score = self.predict(inputs)
        return {
            "system": self.name,
            "score": score,
            "category": self.classify(score),
            "explanation": self.explain(inputs),
        }


class MamdaniSystem(FuzzySystem):
    name = "Mamdani"

    def __init__(self, config_path: str = "config/model.json"):
        super().__init__(config_path)
        self._build_control_system()

    def _build_control_system(self):
        self._inputs = {}
        for var in ["utilization", "defect_rate", "downtime_pct",
                    "overdue_orders", "staff_availability", "energy_overrun"]:
            lo, hi = build_universe(var)[0], build_universe(var)[-1]
            ant = ctrl.Antecedent(np.linspace(lo, hi, 501), var)

            for term, params in self.terms[var].items():
                params = sorted(list(params))
                if len(params) == 4:
                    ant[term] = fuzz.trapmf(ant.universe, params)
                elif len(params) == 3:
                    ant[term] = fuzz.trimf(ant.universe, params)
            self._inputs[var] = ant

        self._risk = ctrl.Consequent(np.linspace(0, 100, 501), "risk_score")
        for term, params in self.terms["risk_score"].items():
            params = sorted(list(params))
            if len(params) == 4:
                self._risk[term] = fuzz.trapmf(self._risk.universe, params)
            elif len(params) == 3:
                self._risk[term] = fuzz.trimf(self._risk.universe, params)

        ctrl_rules = []
        for r in self.rules:
            ant_parts = []
            for var, term, is_not in r.antecedents:
                a = self._inputs[var][term]
                ant_parts.append(~a if is_not else a)
            ant = ant_parts[0]
            for p in ant_parts[1:]:
                ant = ant & p
            ctrl_rules.append(ctrl.Rule(ant, self._risk[r.consequent]))

        self.control_system = ctrl.ControlSystem(ctrl_rules)
        self.sim = ctrl.ControlSystemSimulation(self.control_system)

    def predict(self, inputs: dict) -> float:
        for k, v in inputs.items():
            self.sim.input[k] = float(v)
        self.sim.compute()
        return float(self.sim.output["risk_score"])


class SugenoSystem(FuzzySystem):
    name = "Sugeno"

    def predict(self, inputs: dict) -> float:
        norm = self._normalize_inputs(inputs)
        num = 0.0
        den = 0.0
        for rule in self.rules:
            w = self._rule_strength(rule, inputs) * rule.weight
            if w <= 0:
                continue
            z = rule.sugeno_coeffs["bias"]
            for var, coeff in rule.sugeno_coeffs["coeffs"].items():
                z += coeff * norm[var]
            num += w * z
            den += w
        if den == 0:
            return 50.0
        return float(np.clip(num / den, 0, 100))

    @staticmethod
    def _normalize_inputs(inputs: dict) -> dict:
        centers = {
            "utilization": 85.0, "defect_rate": 3.0, "downtime_pct": 8.0,
            "overdue_orders": 8.0, "staff_availability": 90.0, "energy_overrun": 5.0,
        }
        scales = {
            "utilization": 30.0, "defect_rate": 5.0, "downtime_pct": 10.0,
            "overdue_orders": 15.0, "staff_availability": 15.0, "energy_overrun": 10.0,
        }
        return {k: (inputs[k] - centers[k]) / scales[k] for k in centers}