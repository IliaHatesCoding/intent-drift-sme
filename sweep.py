"""
sweep.py — pilot sweep across conditions.

    python3 sweep.py                 # 3 runs each of B, P1, P2, P3
    python3 sweep.py 5               # 5 runs each
    python3 sweep.py 5 P2 P3         # 5 runs each of just P2 and P3

Every run gets its own log file, so nothing is overwritten and everything can
be re-scored later for free.
"""

import sys
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from batch_runner import run_one, LOG_DIR

# Which provider to use. Set with the SWEEP_PROVIDER environment variable so
# no file editing is required:
#   SWEEP_PROVIDER=hkust     -> gpt-4o via HKUST's gateway
#   SWEEP_PROVIDER=deepseek  -> deepseek-chat via DeepSeek's own API (default)
# Run IDs carry the model label, so runs from different providers never collide.
PROVIDER = os.environ.get("SWEEP_PROVIDER", "deepseek").strip().lower()
if PROVIDER not in ("hkust", "deepseek"):
    raise ValueError(f"Unknown SWEEP_PROVIDER={PROVIDER!r}. Use 'hkust' or 'deepseek'.")


def get_model():
    if PROVIDER == "deepseek":
        from deepseek_connector import make_deepseek_model
        return make_deepseek_model(), "deepseek-chat"
    if PROVIDER == "hkust":
        from hkust_connector import make_hkust_model
        return make_hkust_model("gpt-4o"), "gpt-4o"
    raise ValueError(f"Unknown PROVIDER: {PROVIDER}")


def main():
    args = sys.argv[1:]
    n = int(args[0]) if args and args[0].isdigit() else 3
    conds = [a for a in args if not a.isdigit()] or ["B", "P1", "P4"]

    model, label = get_model()
    variant = os.environ.get("MBC_DATASET", "default")
    from scorer import ContactLookup
    print(f"Provider: {PROVIDER}   Model: {label}")
    print(f"Dataset: {variant}   In-scope population: {ContactLookup().in_scope_count}\n")
    rows = []

    # Runs are independent, so they can go in parallel. Each has its own
    # Sandbox and its own log file; nothing is shared but the model connection.
    workers = int(os.environ.get("SWEEP_WORKERS", "3"))
    jobs = [(cond, rep) for cond in conds for rep in range(1, n + 1)]
    print(f"{len(jobs)} runs, {workers} at a time\n", flush=True)

    done = [0]
    abort = []

    def one(cond, rep):
        try:
            return run_one(model, cond, rep, label.replace(".", ""))
        except Exception as exc:
            msg = str(exc)
            if any(k in msg.lower() for k in
                   ("insufficient credit", "quota", "billing",
                    "401", "403", "invalid api key")):
                abort.append(msg)
            return {"run_id": f"{cond}-{rep}", "condition": cond,
                    "replicate": rep, "error": msg}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, c, r): (c, r) for c, r in jobs}
        for fut in as_completed(futures):
            cond, rep = futures[fut]
            row = fut.result()
            rows.append(row)
            done[0] += 1
            status = "FAILED" if row.get("error") else "ok"
            print(f"  [{done[0]}/{len(jobs)}] {cond} {rep}: {status}", flush=True)

    if abort:
        print(f"\n  Account problem detected: {abort[0][:80]}")
        print("  Top up or check the key, then re-run.")

    rows.sort(key=lambda r: (r.get("condition", ""), r.get("replicate", 0)))

    _summarise(rows)


def _summarise(rows):
    print("\n" + "=" * 92)
    hdr = (f"{'cond':9} {'rep':>3} {'stp':>4} {'qtry':>5} {'qdrift':>6} "
           f"{'adrift':>6} {'IDact':>6} {'IDina':>6} {'rcpt':>5} "
           f"{'blkQ':>5} {'blkS':>5} {'blkR':>5} {'errs':>4}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r.get("error"):
            print(f"{r['condition']:5} {r['replicate']:>3}  ERROR: {r['error'][:60]}")
            continue
        print(f"{r['condition']:9} {r['replicate']:>3} {r.get('steps_taken',0):>4} "
              f"{r.get('blocked_attempts',0):>5} {r.get('query_drift_events',0):>6} "
              f"{r.get('action_drift_breaches',0):>6} "
              f"{r.get('ID_actions',0):>6} {r.get('ID_inaction',0):>6} "
              f"{r.get('recipients_total',0):>5} "
              f"{r.get('coi_refused_queries',0):>5} {r.get('coi_refused_sends',0):>5} "
              f"{r.get('coi_blocked_recipients',0):>5} "
              f"{r.get('sandbox_errors',0):>4}")

    print("\nDROPPED CONSTRAINTS (query drift detail)")
    any_drift = False
    for r in rows:
        d = r.get("constraints_dropped")
        if d:
            any_drift = True
            print(f"  {r['run_id']}: dropped {d}  detail={r.get('query_drift_detail')}")
    if not any_drift:
        print("  none")

    print("\nMANAGER DEFLECTIONS")
    any_defl = False
    for r in rows:
        for d in (r.get("deflection_detail") or []):
            any_defl = True
            print(f"  {r['run_id']} step {d['step']}: {d['question'][:70]}")
            print(f"      -> {d['reply']}")
    if not any_defl:
        print("  none")


if __name__ == "__main__":
    main()
