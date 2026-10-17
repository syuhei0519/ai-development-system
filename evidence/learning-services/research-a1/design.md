# Payment #39 / Notification #41 — edited public research derivative

Research role: research-design. Public task aliases: PUBLIC-PAYMENT-RESEARCH-A1 and PUBLIC-NOTIFICATION-RESEARCH-A1. These are aliases, not platform task IDs.
Logical research attempt: 1 for each new service scope.
Representation: edited_derivative. Publication classification: public_safe. Private originals and their provenance map remain private. This derivative is not automatically original-equivalent; preservation of technical semantics is a producer attestation, not independent verification. Design responsibilities complete; all product AC measurements remain unverified.
The research work performed no implementation, product tests, credentials, GitHub writes, images or deployment. Evidence-only publication is a separate delivery step.

## Fixed evidence and scope

Backend repository: https://github.com/syuhei0519/backend-app
Actual source SHA: d48a97851619912e7efc80c470912907ce965dc7.
Read-only git ls-remote origin refs/heads/main and local HEAD agreed; working tree was clean.
System pin: 3394bb069be64bdc43e057b251fc320302d185f6, repository https://github.com/syuhei0519/ai-development-system.
Read agents/research-design.md, contracts/README.md, contracts/handoff.schema.json, workflows/single-issue.md and contracts/readiness.md at that pin.

Backend source inspected at the actual SHA:
- docs/order-api.md; internal/order/order.go; internal/orderhttp/server.go.
- internal/orderconfig/config.go; cmd/order-server/main.go.
- internal/store/orderpostgres/{store,migrate}.go; order-migrations/{embed.go,0001_create_orders.sql}.
- internal/ordertest/disposable.go; tests/orderintegration/order_test.go.
- Dockerfile.order; .dockerignore; go.mod; .github/workflows/ci.yml; ci/github/{test,oci}.sh; ci/build-oci.sh.
Order has independent process/config/database guard and migration history; its Account reference is historical without a cross-service lookup.
Current release CI explicitly supports backend/order, not these proposed services. Existing Order fixture restricts allowed DB identities to Account/Order.
Only existing migration locks 7742340081 and 7742340082 were found.
The exact public Issue text supplied for this design is saved alongside this derivative; no live issue read or inferred current issue revision is claimed.

Goal: finish the minimal Order/Account learning baseline, then add small Payment/Notification services for later monitoring/canary/release learning.
This design does not reopen or reset any Order attempt/retry/approval history.
New service scopes retain their own attempt1 record. Formal readiness/Issue Completion are Manager decisions.

## API and JSON decisions

Payment:
- POST /api/payments
- GET /api/payments/{id}
- GET /livez; GET /readyz
Input example:
{"request_id":"550e8400-e29b-41d4-a716-446655440000","order_id":1,"amount_minor":1000,"currency":"JPY","simulate_result":"success"}
Required keys: request_id, order_id, amount_minor, currency, simulate_result.
request_id: non-nil, lowercase canonical UUID. order_id and amount_minor: positive signed int64.
currency: JPY only for this bounded lab. simulate_result: success or decline.
Response: all input fields plus id (positive signed int64), status (succeeded or declined), created_at (DB timestamp, UTC RFC3339).

Notification:
- POST /api/notifications
- GET /api/notifications/{id}
- GET /livez; GET /readyz
Input example:
{"request_id":"550e8400-e29b-41d4-a716-446655440001","order_id":1,"recipient":"demo-user","message":"Order accepted","simulate_result":"success"}
Required keys: request_id, order_id, recipient, message, simulate_result.
request_id/order_id follow Payment. recipient is a test token matching ASCII [A-Za-z0-9][A-Za-z0-9._-]{0,63}.
message is valid UTF-8, nonempty, maximum 1024 bytes; no trimming.
simulate_result: success or failure.
Response: all input fields plus id, status (sent or failed), created_at, with Payment's ID/time rules.
No real email address, SMTP, SMS, external sink or paid API is involved.

Both services:
- New valid request: commit first, then HTTP 201 and Location pointing to the GET resource.
- Simulated decline/sink failure is a successfully saved terminal business result, also HTTP 201.
- GET returns HTTP 200 or 404 for absent ID.
- Exact valid replay returns HTTP 200, same resource/ID/status/timestamp and Location.
- Conflicting replay returns HTTP 409 idempotency_conflict and makes no write.
- Follow Order's strict JSON, 16 KiB body limit, accepted media type, duplicate/unknown/missing/null-key rejection, integer spelling, path/method and sanitized error envelope rules.
- Bad input is 400; oversized body 413; media type 415; methods 405 with Allow; store unavailable 503; internal failure 500.
- No list/update/delete API, authentication expansion, generic framework or new dependency.
- order_id is an immutable historical reference: accept any positive int64 without checking Order existence; no foreign key into Order, no HTTP lookup and no Account/Order modification.

## Identity, state and transactions

Persist request_id as UUID with a service-wide UNIQUE constraint, no TTL/deletion.
Compare all decoded input values against stored input, including order_id and simulate_result.
Identity does not depend on raw JSON whitespace/key order. Do not add a second Idempotency-Key header identity.
A new request_id with the same order_id is a distinct permitted fake attempt; this is request deduplication, not one-payment-per-order enforcement.

Use a transaction with INSERT ... ON CONFLICT(request_id) DO NOTHING RETURNING ...
For an existing key, use a separate SELECT statement under READ COMMITTED after conflict resolution, compare stored typed fields and return replay or 409.
Do not process a duplicate before conflict resolution. Existing three-second operation deadlines bound lock waits.
Concurrent duplicates produce one accepted row; conflicting duplicates cannot change it.

Synchronous state flow within one transaction:
- Payment: received -> succeeded when success, or declined when decline.
- Notification: received -> sent when success, or failed when failure.
received is an internal processing step, not a committed/public pending state.
There is no worker, automatic retry, mutable state API, Saga, compensation or Kafka.
A crash before commit rolls back. A crash/lost response after commit is resolved by replay with the same request_id.
State and identity live in PostgreSQL, not a process cache.

Notification fake sink:
- public.notification_sink_receipts(notification_id PRIMARY KEY REFERENCES public.notifications(id), result CHECK sent/failed, created_at).
- The sink is the creation of that durable test receipt, not a network side effect.
- Notification row and one success/failure receipt commit in the same transaction.
- Invoke the sink only for the newly inserted notification, never the replay path.
- A simulated failure records failed plus one failed receipt; a success records sent plus one successful receipt.
- Real DB failures roll back the whole transaction and return a transport/store error rather than a fake business result.
- Preserve consistency between stored simulate_result, terminal status and receipt result.
This gives one committed fake sink invocation per accepted request, including failed results, and survives API restart.
It does not claim exactly-once external delivery.

## Independent ownership and entrypoints

Payment owns:
- cmd/payment-server/
- internal/payment/, internal/paymenthttp/, internal/paymentconfig/
- internal/store/paymentpostgres/
- payment-migrations/embed.go and 0001_create_payments.sql
- internal/paymenttest/ and tests/paymentintegration/
- Dockerfile.payment and docs/payment-api.md
- dedicated PostgreSQL instance, database payments, LOGIN role payment_app
- public.payments, public.payment_schema_migrations; migration version 1; advisory lock 7742340083.

Notification owns:
- cmd/notification-server/
- internal/notification/, internal/notificationhttp/, internal/notificationconfig/
- internal/store/notificationpostgres/
- notification-migrations/embed.go and 0001_create_notifications.sql (notification and receipt tables)
- internal/notificationtest/ and tests/notificationintegration/
- Dockerfile.notification and docs/notification-api.md
- dedicated PostgreSQL instance, database notifications, LOGIN role notification_app
- public.notifications, public.notification_sink_receipts, public.notification_schema_migrations; version 1; lock 7742340084.

Each main supports normal serve and migrate, rejecting unknown arguments like Order.
Default listen address is 0.0.0.0:8080; overrides PAYMENT_HTTP_ADDRESS and NOTIFICATION_HTTP_ADDRESS.
Use existing DATABASE_URL or PG environment behavior and LOG_LEVEL, never credentials in source/runbook.
Follow Order's per-connection actual/configured DB/user guard, parameterized/schema-qualified SQL, fixed search_path, pool/timeouts, bounded migration wait, transaction/history atomicity, forward-only migration and unknown-version rejection.
Use dedicated NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOINHERIT owner roles only in an explicitly approved environment.
Readiness checks the owned DB and exact owned migration version 1. Follow Order's process health/drain behavior.
Do not modify Account/Order code/data/migration embeds/history or create a shared migration runner.
Retain constraints for IDs, enum values, required fields and bounded values in owned SQL as well as input validation.

## Disjoint implementation and local build

The two path sets above are disjoint and can be assigned independently once Manager accepts this handoff.
Existing go.mod/go.sum dependencies suffice: stdlib HTTP/JSON, existing pgx and UUID support.
No shared build, CI, helper, go.mod or existing Dockerfile edit is necessary.
Do not expand internal/ordertest's identity allowlist; create narrowly owned fixture support from its existing isolation pattern.
If a genuinely necessary shared edit is later found, stop the conflicting edit and let Manager sequence one narrow shared patch before dependent work; do not expand release support incidentally.

Each new Dockerfile follows Dockerfile.order's exact pinned builder/runtime bases, build CA optional-secret pattern, CGO-disabled linux/amd64 binary, nonroot UID/GID and OCI source/build stamps.
Use service-specific binary/entrypoint and narrow unit/build commands, not another full suite.
Build directly from repository root using Dockerfile.payment or Dockerfile.notification; place local outputs outside source context.
Do not route through the existing RELEASE_SERVICE publication machinery or add these services to GHCR/release matrices.

Implementation runbook must provide:
- full implemented source commit SHA, matching checkout, Dockerfile/runbook identity and platform;
- go build target, migrate/serve and health/API examples;
- direct local build command with VCS_REF and VCS_SOURCE, local image ID and startup inputs;
- dedicated DB identity, failure-stop rule and exact owned fixture cleanup;
- measured results and limitations.
Deliver Payment source/runbook/local-image identity to deployment #21 and Notification equivalents to #22.
No image or implementation commit exists from this design task.

## AC mapping and bounded verification

All following mappings are covered for research/design responsibilities only; all product AC outcomes are unverified.
All can first be measured premerge in the approved test environment.

#39 AC-1: 模擬成功/拒否の状態をAPIで取得できる
Design: POST/GET of succeeded and declined terminal rows. Fixture measures success and decline and persisted input/result.

#39 AC-2: 同一要求の再送で二重決済状態を作らない
Design: unique request_id, typed replay/conflict behavior and transaction. Fixture measures sequential/concurrent replay, changed-field 409, one DB row and post-process-restart replay.

#39 AC-3: Order識別子との関連と所有DB migration境界が維持される
Design: immutable historical order_id, dedicated target guards and migration ownership. Fixture confirms positive arbitrary Order ID is retained, owned tables/history, migration rerun keeps history timestamps. Source/diff review confirms no Account/Order/shared migration edits.

#41 AC-1: テストsinkの成功/失敗をAPIから確認できる
Design: POST/GET sent and failed plus a corresponding durable fake receipt. Fixture measures both terminal results.

#41 AC-2: 同一要求を再送してもsinkに重複送出しない
Design: one receipt primary key, single transaction and new-insert-only sink. Fixture measures sequential/concurrent replay, conflict 409 and one receipt for successful and failed requests, including replay after API restart.

#41 AC-3: 再起動後も受付済み状態を取得できる
Design: all accepted state/identity/receipts in owned DB. Fixture restarts the API OS process with the same owned DB, checks changed PID, GET and replay retain identity/state/timestamps/receipt count.

Use one disposable API/DB integration fixture per service and one lifecycle within it.
Mandatory persistence restart is API process restart with the same owned DB. DB-server restart is not a separate mandatory acceptance gate.
Cover representative valid/invalid input, simulated success/failure, duplicates/conflicts/concurrent duplicate, process restart, migration initial/no-op behavior and representative DB-unavailable 503.
Keep pure units narrow: validation boundaries, strict decoder, result decision, conflict comparison, config/target rejection.
Do not repeat broad app, Account/Order, kind or release suites. Routine CI still runs its unchanged required checks; this plan does not waive them.
An opt-in skipped DB test is not Integration evidence.

Environment boundary:
- Code, unit work and fixture implementation can proceed independently of kind availability.
- Integration execution belongs in an explicitly approved isolated Kubernetes test environment. k3d/k3s may now be tried in place of kind; no environment success is claimed.
- An approval scoped to a dedicated test environment does not authorize generating/provisioning credentials in a separate implementation workspace.
- Fixture execution there uses only explicitly approved resources/credential handling, no external operator DSN, no reused/shared container/volume and exact-created-resource cleanup.
- Current test environment readiness was not measured in this research task.
- Local image execution/build runtime access must be confirmed in its separately authorized environment.
- New credentials or privileges outside the explicitly scoped approval require owner decision.

## Gates, decisions and remaining responsibilities

Recommended choices above eliminate unresolved API/DB design decisions; no per-field user decision is needed.
Synchronous terminal rows and a transactional DB sink are chosen over pending workers/external sends because they satisfy these learning AC with a small crash/replay contract.
Service-local patterns are chosen over extracting common abstractions to avoid shared-file conflicts and framework scope.

Formal GHCR/release work and existing release-pipeline vulnerability-database freshness blockers are not prerequisites for design/local code.
Do not bypass CI, independent Test/Review or GitHub protections to merge.
No formal Implementation/Deployment/Merge Ready assessment or final_assessment is produced by this Research role.
Manager must accept the fixed design/Handoff, authorize downstream exact scope, preserve current attempt/retry history and delegate Integration to the approved environment.
Implementation-ready recommendation: code, narrow units, owned fixture code, local Dockerfile and runbook paths specified above.
Integration/environment readiness remains pending independent confirmation; deployment/publication/merge/Issue Close are not authorized by this handoff.
Fixed-Git publication and structural validation are separate from semantic business acceptance and independently approved Consumer use. No Consumer permission or Consumption Receipt is supplied by this derivative.
