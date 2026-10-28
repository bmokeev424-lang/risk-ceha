from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Rule:
    rid: str
    antecedents: List[Tuple[str, str, bool]]
    consequent: str
    sugeno_coeffs: dict
    weight: float = 1.0

    def antecedent_text(self) -> str:
        parts = []
        for var, term, is_not in self.antecedents:
            op = "НЕ " if is_not else ""
            parts.append(f"{var} = {op}{term}")
        return " И ".join(parts)

def build_rules() -> List[Rule]:
    def sug(util=0.0, defect=0.0, down=0.0, overdue=0.0, staff=0.0, energy=0.0, bias=0.0):
        return {
            "bias": bias,
            "coeffs": {
                "utilization": util, "defect_rate": defect, "downtime_pct": down,
                "overdue_orders": overdue, "staff_availability": staff, "energy_overrun": energy,
            },
        }

    rules = [
        Rule("R01", [("utilization", "normal", False), ("defect_rate", "low", False), ("downtime_pct", "low", False)], "low", sug(bias=10)),
        Rule("R02", [("utilization", "normal", False), ("defect_rate", "medium", False), ("overdue_orders", "low", False)], "moderate", sug(bias=35)),
        Rule("R03", [("utilization", "high", False), ("defect_rate", "low", False), ("energy_overrun", "medium", False)], "moderate", sug(bias=40)),
        Rule("R04", [("utilization", "high", False), ("downtime_pct", "medium", False), ("overdue_orders", "medium", False)], "high", sug(bias=60)),
        Rule("R05", [("defect_rate", "high", False), ("downtime_pct", "high", False)], "critical", sug(bias=85)),
        Rule("R06", [("staff_availability", "low", False), ("overdue_orders", "high", False)], "critical", sug(bias=82)),
        Rule("R07", [("utilization", "low", False), ("staff_availability", "high", False)], "moderate", sug(bias=30)),
        Rule("R08", [("utilization", "low", False), ("downtime_pct", "high", False)], "high", sug(bias=65)),
        Rule("R09", [("energy_overrun", "high", False), ("utilization", "high", False)], "high", sug(bias=62)),
        Rule("R10", [("defect_rate", "medium", False), ("downtime_pct", "medium", False), ("staff_availability", "medium", False)], "moderate", sug(bias=45)),
        Rule("R11", [("overdue_orders", "high", False), ("energy_overrun", "high", False)], "high", sug(bias=68)),
        Rule("R12", [("staff_availability", "low", False), ("defect_rate", "high", False)], "critical", sug(bias=88)),
        Rule("R13", [("utilization", "normal", False), ("energy_overrun", "low", False), ("defect_rate", "low", False)], "low", sug(bias=12)),
        Rule("R14", [("downtime_pct", "low", False), ("overdue_orders", "low", False), ("staff_availability", "high", False)], "low", sug(bias=15)),
        Rule("R15", [("utilization", "high", False), ("staff_availability", "low", False)], "high", sug(bias=70)),
        Rule("R16", [("energy_overrun", "medium", False), ("downtime_pct", "medium", False)], "moderate", sug(bias=42)),
        Rule("R17", [("utilization", "low", False), ("defect_rate", "low", False)], "moderate", sug(bias=25)),
        Rule("R18", [("overdue_orders", "medium", False), ("energy_overrun", "medium", False), ("staff_availability", "medium", False)], "high", sug(bias=58)),
        Rule("R19", [("defect_rate", "high", False), ("energy_overrun", "high", False)], "critical", sug(bias=90)),
        Rule("R20", [("utilization", "normal", False), ("staff_availability", "medium", False), ("downtime_pct", "low", False)], "low", sug(bias=20)),
    ]
    return rules