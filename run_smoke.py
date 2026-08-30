"""
run_smoke.py — runs ONE real agent run and stops.

USAGE (in Terminal, from the project folder):

    python3 run_smoke.py B      <- baseline, no pressure. DO THIS FIRST.
    python3 run_smoke.py P1     <- explicit instruction pressure
    python3 run_smoke.py P2     <- incentive framing pressure

Start with B. If the agent cannot complete the ordinary task cleanly, results
from the pressure conditions mean nothing — you would not know whether drift
was caused by pressure or by the agent simply being confused.

Each run costs a few cents at most.
"""

import sys

from hkust_connector import make_hkust_model
from batch_runner import smoke_test

DEPLOYMENT = "gpt-4o"        # confirmed working on HKUST's gateway


def main():
    condition = sys.argv[1] if len(sys.argv) > 1 else "B"
    if condition not in ("B", "P1", "P2", "C1", "C2", "C3"):
        print(f"Unknown condition: {condition}")
        print("Use one of: B, P1, P2, C1, C2, C3")
        return

    print(f"Model: {DEPLOYMENT} via HKUST")
    print(f"Condition: {condition}")
    print("This makes real API calls. One run only.\n")

    model = make_hkust_model(DEPLOYMENT)
    smoke_test(model, condition=condition, model_label=DEPLOYMENT.replace(".", ""))


if __name__ == "__main__":
    main()
