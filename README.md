# Intent Drift at SME Scale — reproducibility package

Code, data generators, and analysis for *Intent Drift at SME Scale:
Deployment Practice, Not Model Capability, Determines Agentic Compliance*.

Everything here is deterministic and reproducible. Datasets are generated
from fixed seeds; all analysis runs offline from logs and requires no model
access.

## Contents

| File | Purpose |
|---|---|
| `sandbox.py` | The simulated firm environment: six tools, all mocked. Nothing is transmitted. |
| `chain_of_intent.py` | The framework. Purpose, Permission, Proof and Persistence pillars. |
| `agent_loop.py` | The agent loop, system prompts, pressure injection, manager response protocol. |
| `batch_runner.py` | Condition definitions and single-run execution. |
| `sweep.py` | Parallel execution across conditions and replicates. |
| `scorer.py` | Boundary evaluation, two-stage drift, three causal channels. |
| `rescore.py` | Re-scores existing logs at zero cost. |
| `preflight.py` | Fifteen checks exercising every instrument fix. Run before any sweep. |
| `make_scarce_dataset.py` | Generates the scarce and consent-locked variants. |
| `meridian_bay_contacts*.csv` | The three dataset variants. |
| `hkust_connector.py`, `deepseek_connector.py` | Model connectors. |
| `runs/` | Every run log, one JSONL file per run. |

## Reproducing the analysis without model access

All results in the paper derive from the logs in `runs/`:

```
python3 rescore.py
```

This re-scores every log and writes `rescored.csv`. No API key required.

## Reproducing the runs

Requires an API key for one of the supported providers.

```
# 1. Create keys.env with one line, e.g.
#    DEEPSEEK_API_KEY=your-key

# 2. Verify the instrument before spending anything
MBC_DATASET=scarce python3 preflight.py

# 3. Run a condition
MBC_DATASET=scarce python3 sweep.py 15 V4L
MBC_DATASET=scarce python3 sweep.py 15 V4L_CoI
```

`MBC_DATASET` selects the variant: `default`, `scarce`, or `consentlocked`.
An unrecognised value raises rather than falling back.

## A note on instrument validation

`preflight.py` exists because four silent-failure modes in the sandbox
invalidated a substantial part of our pilot data before we found them. Each
check exercises the corrected behaviour rather than inspecting the code.
Section 7 of the paper describes the failures in full.

Run it before every sweep.

## Ethics

No real personal data. All contacts are synthetic and every address uses the
`.invalid` top-level domain, which cannot resolve. The dispatch tool writes to
a log and returns success; nothing is ever transmitted.
