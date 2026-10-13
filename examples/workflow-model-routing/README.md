# Synthetic workflow routing examples

These files contain synthetic identifiers only. They are not real approvals,
dispatches, UI evidence, budget renewals, Handoffs or evaluations. Keep actual
request/approval/business ledger/task reference/record/observations privately.
`approval.template.json` deliberately rejects planning until separately approved.
The example app-code flag describes a synthetic ordinary specialist request; it
authorizes no current app work. Knowledge/app/backend tasks remain off here.

[The workflow](../../workflows/workflow-model-routing.md) defines the route table,
source qualification, Strict/BestEffort gates and immutable history boundary.
`workflow_model_routing.py` has only `plan` and `observe`; no reserve/dispatch/reset.

Manager independently approves exact request/policy/history raw SHA256 and routing
checkout head. `explicit_dispatch_decision=true` is required even for redispatches.
`routine_scope_approved=true` only for `routine-consumer` and a specifically
approved read-only classification/extraction/formatting scope. Routine tasks exclude
app code, security and live infrastructure. A manual Astra request repeats its
model/effort/scope/reason/budget in approval with `approved=true`; it cannot exceed
remaining existing budget. No model change renews limits.

Use current business ledger and independently supplied pins (not hashes adopted
from untrusted downloaded content). Policy file is
`config/workflow-model-routing.yaml`; choose mode explicitly. Current routing head
is the reviewed system checkout; do not substitute its CI for the target app's CI.

```bash
WORKFLOW_ARGS=(
  --request "$WORKFLOW_PRIVATE_REQUEST"
  --policy config/workflow-model-routing.yaml
  --policy-sha256 "$WORKFLOW_POLICY_PIN"
  --approval "$WORKFLOW_PRIVATE_APPROVAL" --approval-sha256 "$WORKFLOW_APPROVAL_PIN"
  --history "$WORKFLOW_PRIVATE_HISTORY" --history-sha256 "$WORKFLOW_HISTORY_PIN"
  --repo . --head "$WORKFLOW_REVIEWED_HEAD"
)
python3 scripts/workflow_model_routing.py plan "${WORKFLOW_ARGS[@]}"
```

Manager saves the emitted private record's exact bytes/hash, reserves existing
business dispatch intent before create, then passes emitted create arguments with
the full task input only after every applicable quality/security/approval gate.
Do not execute from nonzero exit, stale ledger, exhausted counter or unknown
admission. The example planner is read-only, not a budget reservation guarantee.
`service_tier="default"` explicitly selects Standard; `standard` is invalid wire.

`observation.template.json` starts with all observations null. For independently
confirmed per-task UI evidence, set for example this evidence object privately:

```json
{
  "source": "human_confirmed_ui",
  "binding": "execution_task",
  "task_reference": "SYNTHETIC-PRIVATE-TASK-REF",
  "provenance": "SYNTHETIC per-task execution panel; observed 2030-01-01T00:00:00Z; identity/rerouting checked",
  "confirmed_by": "SYNTHETIC-HUMAN-CONFIRMER"
}
```

This is a schema illustration, not execution evidence. Selector/settings or
aggregate usage must use their corresponding source/binding and remain unverified.
Do not turn human UI provenance into platform metadata. Supply observed values only
when actually seen, otherwise null. Unknown usage stays null with no estimate.
Append using the original approved inputs/history snapshot and the latest routing
record pin independently preserved by Manager:

```bash
python3 scripts/workflow_model_routing.py observe "${WORKFLOW_ARGS[@]}" \
  --record "$WORKFLOW_PRIVATE_RECORD" --record-sha256 "$WORKFLOW_RECORD_PIN" \
  --observation "$WORKFLOW_PRIVATE_OBSERVATION"
```

Persist the successor separately, never overwrite old records. Mismatches remain
sticky; a later matching claim cannot silently erase them. Routing approval does
not prove Handoff AC, quality, independence, source truth, live permissions or
Merge Ready. No real runtime IDs, UI screenshots/usage or private logs go to Git.

```bash
python3 -m unittest discover -s tests -p 'test_workflow_model_routing.py' -v
python3 -m unittest discover -s tests -v
```

Tests use temporary synthetic records only. They perform no task executions,
benchmarks, real reservations or additional evaluations. The consumed pilot stays
1/1, historical total 3/6; its error is not a model-quality finding.
