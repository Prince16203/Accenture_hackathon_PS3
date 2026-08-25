"""
Runs all 5 mandated demo scenarios back to back, in the order that
tells the clearest story: clean case first (establishes trust), then
multi-factor (shows nuance), then low-confidence (shows honesty),
then sparse-history (shows edge-case handling), then security (shows
governance). Use this as the single script to run live during judging.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scenario_5_clean_case
import scenario_1_multifactor
import scenario_2_low_confidence
import scenario_3_sparse_history
import scenario_4_security


def run_all():
    print("\n" + "#" * 70)
    print("# ROOTCAUSE.AI — FULL SCENARIO WALKTHROUGH (5/5 mandated cases)")
    print("#" * 70 + "\n")

    scenario_5_clean_case.run()
    print("\n\n")
    scenario_1_multifactor.run()
    print("\n\n")
    scenario_2_low_confidence.run()
    print("\n\n")
    scenario_3_sparse_history.run()
    print("\n\n")
    scenario_4_security.run()

    print("\n" + "#" * 70)
    print("# ALL 5 SCENARIOS COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    run_all()