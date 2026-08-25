"""
calculator_tool.py
Small deterministic math utilities the agent can call directly instead
of asking the LLM to do arithmetic — magnitude checks, comparisons,
significance framing. Deliberately tiny; this is not meant to grow.
"""


def pct_change(old_value: float, new_value: float) -> float:
    if old_value == 0:
        return float("inf") if new_value != 0 else 0.0
    return round((new_value - old_value) / old_value, 4)


def dollar_change(old_value: float, new_value: float) -> float:
    return round(new_value - old_value, 2)


def is_significant(pct_change_value: float, threshold: float = 0.10) -> bool:
    return abs(pct_change_value) >= threshold


def compare_magnitudes(value_a: float, value_b: float, label_a: str = "A", label_b: str = "B") -> dict:
    """Quick comparison helper — which is bigger, by how much, as a ratio and a difference."""
    if value_b == 0:
        ratio = None
    else:
        ratio = round(value_a / value_b, 3)
    return {
        "larger": label_a if value_a > value_b else label_b,
        "difference": round(abs(value_a - value_b), 2),
        "ratio": ratio,
    }


if __name__ == "__main__":
    print(pct_change(1000, 530))          # -0.47
    print(dollar_change(1000, 530))       # -470.0
    print(is_significant(-0.47))          # True
    print(compare_magnitudes(606983.52, 522683.25, "Store 18", "Store 27"))