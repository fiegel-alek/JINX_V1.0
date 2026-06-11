# JINX-BUS / JINX-FABRIC

JINX-BUS, also called JINX-FABRIC, is the integration fabric for future tactical-radio and external-system access.

During early development it remains simulation-first. The current router is an internal policy-enforced message path used to prove validation, audit, and dead-letter behavior before any real tactical radio integration exists.

## Phase 1 Behavior

- Messages declare source, destination, payload schema, license scope, sensitivity label, provenance reference, and simulation status.
- The router denies unlicensed or schema-incompatible routes.
- Denied messages go to a dead-letter list.
- Allowed and denied routing decisions are written to the audit log.
- No real tactical radio access is implemented.

## Future Work

- Add topic subscriptions.
- Add replay mode.
- Add retry policies.
- Add persistent dead-letter storage.
- Add boundary redaction hooks before delivery.
- Add controlled tactical-radio adapter gates only after explicit authorization.
