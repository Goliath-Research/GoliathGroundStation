# Operator identity (GoliathApp RBAC)

How **human operators** authenticate for GoliathGroundStation: portal sessions and RBAC from [GoliathApp](https://github.com/Goliath-Research/GoliathApp), not worker gateway sessions. This document is the public Phase 2 design slice; enforcement hooks land in later releases.

## What operators do here

| Surface | Who | Auth model |
| --- | --- | --- |
| Configurator / test campaigns (`goliath-ground-web`) | Integration and launch-ops staff | **Portal session** → RBAC roles → HTTP API |
| Monitor stations (LabVIEW, OPC clients) | Engineers at consoles | OPC subscribe today; **tag-tree ACL** via RBAC in Phase 3 |
| Singleton gateway ingest | Vehicle / RF path | **No operator session** — domain service, not a user login |

Operators change configuration, approve campaigns, and (later) control which OPC subtrees a station may read. They do **not** claim leased workflow tasks for live telemetry.

## Non-goal: live OPC is not worker claim

The ground gateway **publishes once** on the OPC UA bus. Monitor stations are **OPC subscribers**, not GoliathApp workers polling `POST /v1/workers/tasks/request`.

| Concern | Operators & monitors | Workflow workers (e.g. GoliathOmics) |
| --- | --- | --- |
| Session type | [Portal user session](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/rbac.md#portal-sessions) (`portal.sp_session_open` → bearer token) | [Gateway worker session](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/workers.md#session-authentication) (`worker_token` → `POST /v1/workers/authenticate`) |
| Credential store | `"RBAC"."SessionTokens"` | `wf.worker_session` |
| Typical DB login | `goliath_portal` (semantic + session procs) | `goliath_gateway` (`wf.sp_*` only) |
| Ground station use | Configurator, audit, future OPC ACL | **Not used** for umbilical poll, decode, or OPC publish |

See GoliathApp [RBAC](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/rbac.md) and [workers](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/workers.md) for the platform split.

## Portal sessions and RBAC

GoliathApp stores accounts, roles, scopes, and permissions in the `"RBAC"` schema. Interactive users authenticate through **portal session** procedures (`portal.sp_session_open`, `portal.fn_session_resolve`, …) documented in [rbac.md](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/rbac.md#portal-sessions).

Ground station configurator APIs (today: sibling `goliath-ground-web`; Phase 4: optional portal shell) should:

1. Accept a **portal bearer token** from the customer BFF or future Goliath portal chrome.
2. Resolve the session to a user, active scope, and role set (via `portal.fn_session_resolve` or the app’s semantic client — not by calling `"RBAC"` tables directly from monitor hosts).
3. Check **required roles** declared in the deploy target `operators.required_roles` (and optional `operators.configurator.required_roles` when configurator policy is stricter than generic operator access).
4. Use the **`goliath_portal`** database role from the deploy profile for session and semantic reads — separate from **`goliath_gateway`** used by the workflow REST gateway for workers.

Permissions are Meta object + operation pairs (`"RBAC"."Permissions"`). Ground-station-specific permission names and Meta classes will ship with domain SQL in Phase 3; this slice only documents the wiring contract.

## OPC monitors and tag trees (Phase 3)

Deploy targets already inventory monitors under `monitors[]` with optional `tag_trees[]` labels. **Phase 2 does not enforce** those trees at the OPC server. Phase 3 will map RBAC scopes or roles to allowed OPC namespaces and align with `monitors[].tag_trees` for audit and policy.

Until then, treat `tag_trees` as **documentation for operators and RBAC designers**, not runtime ACL.

## Deploy profile hooks

Customer targets (`deploy/targets/*.json`) express operator policy beside gateway and database settings.

| Field | Purpose |
| --- | --- |
| `database.portal_role` | Postgres login for portal session + semantic procedures (`user` / `secret:…` password). Already in `target.schema.json`. |
| `operators.session_source` | Must be `goliathapp_portal` for this product — documents that sessions come from GoliathApp, not worker enroll. |
| `operators.app_base_url` | Optional public base URL for the GoliathApp BFF used to resolve sessions in front of configurator HTTP (TLS terminator or shared portal host). |
| `operators.required_roles` | Role names every ground-station operator must hold (site-wide minimum). |
| `operators.configurator.required_roles` | Optional stricter role set for configurator / test-campaign HTTP only. |
| `operators.opc_tag_tree_acl` | `enforce: false` in Phase 2; set `enforce: true` when Phase 3 enforcement ships. |

Planned **environment variables** (names only — values are `secret:NAME` or host env files, never in git):

| Variable | Consumer | Notes |
| --- | --- | --- |
| `GOLIATH_PORTAL_DB_URL` | Configurator / product shell | Built from `database.*` + `portal_role` at deploy time. |
| `GOLIATH_APP_BASE_URL` | Session validation client | From `operators.app_base_url` when HTTP validation is used. |
| `GOLIATH_GROUND_OPERATOR_ROLES` | Optional comma-separated mirror of `required_roles` for legacy services until they read target JSON. |

Systemd stubs under `deploy/systemd/` do not yet inject these; a future `deploy_target.sh` will render env files from the target document.

## Implementation status (this repository)

| Piece | Status |
| --- | --- |
| `docs/operator-identity.md` (this file) | **Landed** — public contract |
| `deploy/targets/target.schema.json` `operators` block | **Landed** — declarative policy |
| `goliathgroundstation.operator_identity` | **Stub** — no network/DB calls yet |
| Configurator session middleware | **Pending** — requires runtime migration off private Astra |
| OPC tag-tree enforcement | **Phase 3** |

Optional Python dependency: when [GoliathApp](https://github.com/Goliath-Research/GoliathApp) publishes a installable client for `portal.fn_session_resolve`, this package may add an **optional** `goliathapp` extra. Until then, integrators call their existing BFF or database boundary consistent with GoliathOmics.

## Related docs

- [Conversion plan](conversion-plan.md) — phased checklist and architecture
- [Deploy README](../deploy/README.md) — topology and target validation
- [GoliathApp RBAC](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/rbac.md)
- [GoliathApp workers](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/workers.md) — contrast only; not used for live OPC
- [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics) — parallel app-on-GoliathApp pattern (uses workers for batch compute)
