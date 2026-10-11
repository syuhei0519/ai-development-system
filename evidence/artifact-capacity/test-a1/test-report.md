# Independent System capacity Test — epoch 1 attempt 1

Result: **completed for assigned independent Test scope**, AC-C1–AC-C4 covered.
No implementation change, PR operation, merge, deployment or Issue final acceptance.

Fixed head: `4e38376404d9486daae93829735f11166a01e062`.
Canonical/base: `4693887fa79c2b4a291c555b8bd27b6903eb4199`.
Config: `sha256:f02d090639034d8882e827dfbc9da4a181c3a6218a4d389a46e62c69f30eb1ad`.
PR: https://github.com/syuhei0519/ai-development-system/pull/9

## Measured evidence

- All 356 existing/new suite methods passed independently in 27.395 seconds.
- All eight workflow contract-validation commands passed independently.
- 59 independently authored CLI/schema checks passed in 38.333 seconds. The
  reproducer imports no implementation test helpers. It generates synthetic Git
  objects and temporary authorizations, invokes actual preparation/Consumer CLI
  functions in subprocesses, and substitutes only network fetch with local Git.
- Incoming 12-artifact bundle passed fixed canonical Delivery 1.2 using fresh
  HTTPS Git retrieval and independently supplied authorization pin. Manifest,
  publication, Handoff, context and config hashes match Manager inputs. Candidate
  1.3 schema files remain generic JSON review data, never the incoming trust root.
- Independently observed same-head push and PR CI success; run IDs
  38168383783 and 38168394077. PR remains draft/open/unmerged at observation.

## Assigned AC verification

| AC | Independent result and basis |
| --- | --- |
| AC-C1 | Legacy 128 accepted, dependent Handoff added at 129, all original 128 output bytes compared equal. Preparation and normal Consumer accept 256 and preserve complete nested upstream closure. Representations and separate authorization retained. |
| AC-C2 | Four new schemas differ from canonical 1.2 only in identity/version and three artifact-array limits. Legacy schema bytes unchanged; old Consumer accepts 1.2 and rejects 1.3; new Consumer accepts 1.0/1.1/1.2. Explicit version addition rationale is sound and documented. 16MiB/blob, 64MiB including trees, 4096 slots, candidate/Knowledge 128, tree entries4096/trees1024/raw1MiB/total4MiB/path512 remain unchanged. |
| AC-C3 | 128/129/256 success,257 fail; legacy129 fail. CLI rejects missing upstream/slot, duplicates, size/hash tamper, wrong Handoff/candidate type, truncated/duplicate/nonfinite JSON, unapproved use, wrong pin/scope/representation/expiry and mixed versions. Exact64MiB succeeds; extra bytes and single16MiB+1 fail. Independent candidate/tree cases reject missing/profile/ID/source bindings and tree missing/file size/hash/mode/root OID/child inventory mismatches. All failures leave no verified output. Full suite additionally replays raw-tree truncation/type/symlink/gitlink/resource limits, retry and no-overwrite checks under 1.3. |
| AC-C4 | Inspected all 18 changed files. README, contracts/index, template, examples and workflow consistently describe explicit 1.3 finite capacity, legacy128, unchanged budgets and approval gates. CI discovers new tests; record validator includes all four 1.3 schemas. No old evidence, Handoff/Readiness/retry schemas or retry validator changed. Only validation workflow, contents:read, no deployment job; deployment effect none. Independent Review/Manager refresh remain gates; no merge performed. |

## Reproduction

With checkouts at the fixed commits and requirements-dev.txt installed:

```sh
python -m unittest discover -s tests -v
python reproducer.py /path/to/head /path/to/canonical independent-results.json
```

Run the eight commands recorded in ci-command-replay.json from the head checkout.
The synthetic temporary origin, authorization and output directories are removed
when the reproducer finishes. No real application data or public large bundle is
required. The first 40-case run passed before extending the independent harness
with candidate/tree cases; final 59-case run passed. No implementation fixes made.

## Limits, validity and responsibility

Measurements have a justified maximum 24-hour validity as recorded in
readiness-evidence.json, conditional on unchanged head/base/target/config and no
contradictory evidence. Manager's policy window ends 2026-10-11T20:22:16Z and is
not extended by this Test. Manager must refresh mutable GitHub policy immediately
before action. Merge-group is null in supplied context; no merge-group tested.
Readiness schema requires assessor_role=manager, so this Test emits bound evidence
for aggregation rather than falsely acting as Manager. No final_assessment issued.

The supplied AC/focus constitutes the verification plan; no separate Research
bundle was supplied or assumed. Private original equivalence and real application
bundle execution were not tested or claimed. Network/disk pack resource limits
remain the preexisting environment boundary. Synthetic CLI success does not
replace real fresh delivery; incoming delivery was separately observed.

Public output contains purpose-made aliases, synthetic reproducer and curated
measurements only. Authorization/Consumption Receipt, runtime identities, private
conversations and internal execution logs are excluded. Original upstream closure
is referenced at its fixed public commits with unchanged bytes. Independent Review
and integration remain pending, and all earlier B2/retry histories stay unchanged.
