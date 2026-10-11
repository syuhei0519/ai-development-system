# Synthetic Knowledge collector fixture

All events, Issue aliases and Knowledge documents here are synthetic sample data. There was no
Agent execution or actual curation. Event sources point to the two synthetic source files at the
fixed P-A commit. The checked-in registry uses a fictional inbox snapshot and grants no authority.

Offline full regression (includes real local Git tree tests, crash points and legacy suites):

```bash
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
```

For a real fixed HTTPS Git scan, obtain the **pushed P-B head** from Manager. Generate a registry
outside the checkout; the two source references remain fixed to P-A, while inbox events are read
from that P-B head. Do not substitute a floating ref.

```bash
python scripts/prepare_collector_fixture.py \
  --repository syuhei0519/ai-development-system --commit <FIXED_PB_HEAD> \
  --output <PRIVATE_DIRECTORY>/registry.json
```

Manager then prepares a private authorization according to
[the template](../../templates/knowledge-collection.md), with operation=scan and the exact
registry digest, supplies its independent pin, and runs the scan command. No fixture or CLI
creates the approval. Expected counts: two verified events, other states zero. Reconcile with a
fresh operation=reconcile authorization against the same registry and new current state digest;
there must still be exactly two events. The scan history grows, while original event bytes and
retry history remain unchanged. State is never an acceptable public artifact.

Read the private current state SHA256, retain it independently, and reproduce the plan without
mutating that state or acquiring any permission:

```bash
python scripts/knowledge_collector.py replay --store <PRIVATE_STORE> \
  --previous-sha256 <CURRENT_STATE_SHA256> --private-plan <NEW_PRIVATE_PLAN_PATH>
```

`input.json` has one raw finding per event; source files, article, context and handoff support
unit-test typed bundle checks. They are deliberately simulated output, not operational evidence.
Tests also use artificial commit IDs only through an in-memory source adapter. Git tree tests
create local fixed commits and test the production reader without network access. The production
CLI has no file:// adapter, local-source bypass, pretend-clock option or mock authority flag.

No schedule, Agent, API, Git write, PR, deployment or development gate is exercised by this fixture.
