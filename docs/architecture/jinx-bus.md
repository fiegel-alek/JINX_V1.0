# JINX-BUS / JINX-FABRIC

JINX-BUS is the policy-enforced message fabric. Modules publish messages to the bus, and the bus asks JINX-Core policy whether the route is allowed before delivery.

## Phase 1 Behavior

- Messages declare source, destination, payload schema, license scope, sensitivity label, provenance reference, and simulation status.
- The router denies unlicensed or schema-incompatible routes.
- Denied messages go to a dead-letter list.
- Allowed and denied routing decisions are written to the audit log.

## Future Work

- Add topic subscriptions.
- Add replay mode.
- Add retry policies.
- Add persistent dead-letter storage.
- Add boundary redaction hooks before delivery.
