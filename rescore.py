"""
rescore.py — re-scores every log in runs/ with the current scorer.

Costs nothing. Logs are permanent, so any improvement to the scorer can be
applied retroactively to all data ever collected.

    python3 rescore.py
"""

import os
import glob
import json
import csv

from scorer import score_run, ContactLookup

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "runs")
OUT_CSV = os.path.join(HERE, "rescored.csv")


def main():
    logs = sorted(glob.glob(os.path.join(LOG_DIR, "*.jsonl")))
    if not logs:
        print(f"No logs found in {LOG_DIR}")
        return

    contacts = ContactLookup(rule="strict")
    print(f"In-scope population: {contacts.in_scope_count}")
    print(f"Re-scoring {len(logs)} log(s)\n")

    header = (f"{'log':34} {'stp':>4} {'mode':>6} {'qtry':>5} {'qdrift':>6} "
              f"{'adrift':>6} {'data':>5} {'exec':>5} {'rcpt':>5} {'errs':>4}  dropped")
    print(header)
    print("-" * len(header))

    rows = []
    for path in logs:
        name = os.path.basename(path).replace(".jsonl", "")
        # Vague-purpose conditions (V*) must be scored in policy mode: the
        # agent was never told the constraints, so "dropped a constraint it
        # previously used" never triggers and drift reads as zero. The sweep
        # sets this automatically; rescoring must infer it from the run name.
        policy = os.path.basename(path).startswith("V")
        r = score_run(path, contacts=contacts, policy_mode=policy)
        if r.get("error"):
            print(f"{name:28} {r['error']}")
            continue

        print(f"{name:34} {r['total_steps']:>4} "
              f"{'policy' if policy else 'stated':>6} "
              f"{r.get('blocked_attempts',0):>5} {r['query_drift_events']:>6} "
              f"{r['action_drift_breaches']:>6} "
              f"{r['data_breaches']:>5} {r['execution_breaches']:>5} "
              f"{r['recipients_total']:>5} {r['sandbox_errors']:>4}  "
              f"{','.join(r['constraints_dropped']) or '-'}")

        flat = {"log": name}
        for k, v in r.items():
            flat[k] = json.dumps(v, default=str) if isinstance(v, (dict, list)) else v
        rows.append(flat)

    if rows:
        fields = sorted({k for row in rows for k in row})
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"\nWrote {len(rows)} rows to {OUT_CSV}")

    # Summary
    q = sum(1 for r in rows if int(r.get("query_drift_events", 0)) > 0)
    a = sum(1 for r in rows if int(r.get("action_drift_breaches", 0)) > 0)
    e = sum(1 for r in rows if int(r.get("sandbox_errors", 0)) > 0)
    print(f"\nRuns with query drift : {q}/{len(rows)}")
    print(f"Runs with action drift: {a}/{len(rows)}")
    print(f"Runs with sandbox errors (EXCLUDE from findings): {e}/{len(rows)}")


if __name__ == "__main__":
    main()
