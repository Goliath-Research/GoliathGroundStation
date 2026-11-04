# Semantic layer, actions, and NavTree

Plan for exposing GoliathGroundStation through GoliathApp's user-recognized entities. The raw Astra `config` / `testlog` schema (see [domain SQL](domain-sql.md)) stays as-is; this adds a thin semantic namespace over it. Live OPC UA telemetry stays outside the workflow engine ([conversion plan](conversion-plan.md)).

## Semantic layer

Raw tables are an internal detail. Users, the portal, and agents see **GoliathGroundStation** through GoliathApp's semantic registry ([semantic layer](https://goliath-research.github.io/GoliathApp/semantic-layer/), [semantic extensions](https://goliath-research.github.io/GoliathApp/semantic-extensions/)), the same pattern as GoliathOmics.

- **Namespace:** `ground` (row in `portal.semantic_namespace`; GoliathApp owns `core` and `engine`).
- **Registration:** Python `SemanticEntitySpec` / `SemanticRequestSpec` (`goliath_app.semantic.spec`) → `goliath-semantic-export` (Pydantic row models, `portal_semantic_row_types.sql`, `schemas/semantic/catalog.json`) → release seeder calling `portal.sp_semantic_register_entity`, `portal.sp_semantic_register_attribute`, `portal.sp_semantic_register_request`.
- **Reads:** every read is a named request run by `portal.sp_run_semantic_request` (RBAC permission + organization scope), via `goliath_app.portal.PortalClient` or the Exograph GraphQL/MCP façade.

### Entities

| Code | Display name | Key attributes | Backing (`storage_relation` / Meta class) |
| --- | --- | --- | --- |
| `ground.vehicle` | Vehicle | name, configuration version, active | view over Astra `config` vehicle tables |
| `ground.station` | Monitor station | name, allowed tag trees, last seen | view over Astra `config` station tables + OPC ACL |
| `ground.tag_tree` | OPC tag tree | root path, variables, owning subsystem | view over Astra `config` variable tables |
| `ground.campaign` | Test campaign | vehicle, kind (I&T, fixture, pre-launch), status, window | view over Astra `testlog` campaign/job tables |
| `ground.test_log` | Test log | campaign, started, ended, export status | view over Astra `testlog` tables |
| `ground.it_event` | I&T event | campaign, ts, sensor/actuator, value, severity | view `testlog.v_it_event` over `testlog.it_event` |

### Named requests

| `request_code` | Entity | Params | `required_permission` | Target |
| --- | --- | --- | --- | --- |
| `ground.campaign.list` | `ground.campaign` | vehicle_id?, status? | `ground.campaign.read` | view |
| `ground.test_log.by_campaign` | `ground.test_log` | campaign_id | `ground.testlog.read` | view |
| `ground.it_event.window` | `ground.it_event` | campaign_id, from, to, tag_prefix? | `ground.testlog.read` | view + filter template |
| `ground.station.list` | `ground.station` | — | `ground.station.read` | view |
| `ground.tag_tree.for_station` | `ground.tag_tree` | station_id | `ground.station.read` | function over OPC tag-tree ACL |

### Example entity spec

```python
from goliath_app.semantic.spec import SemanticAttributeSpec, SemanticEntitySpec, SemanticRequestSpec

IT_EVENT_ENTITY = SemanticEntitySpec(
    namespace="ground",
    code="it_event",
    display_name="I&T event",
    description="Sensor or actuator event logged during avionics / engine integration and test.",
    schema_version="1",
    row_model=ItEventRow,
    storage_relation="testlog.v_it_event",
    attributes=(
        SemanticAttributeSpec(code="event_id", column_name="id", json_type="integer", role="key"),
        SemanticAttributeSpec(code="campaign_id", column_name="campaign_id", json_type="integer", role="filter", filterable_ops=("eq",)),
        SemanticAttributeSpec(code="ts", column_name="ts", json_type="datetime", role="attribute", filterable_ops=("gte", "lte")),
        SemanticAttributeSpec(code="tag", column_name="tag", json_type="string", role="label", filterable_ops=("eq", "prefix")),
        SemanticAttributeSpec(code="value", column_name="value", json_type="number", role="measure"),
    ),
)

IT_EVENT_LIST = SemanticRequestSpec(
    request_code="ground.it_event.window",
    version="1",
    namespace="ground",
    entity_code="it_event",
    target_kind="view",
    target_name="testlog.v_it_event",
    params_model=ItEventListParams,
    result_row_model=ItEventRow,
    required_permission="ground.testlog.read",
    max_rows=500,
)
```

## Action layer

Business operations are typed `ActionSpec` rows (`goliath_app.actions.spec`), published through the `goliath.action_catalogs` entry point and synced into `wf.workflow_action` by the release (`seed_action_catalog.py --use-db`). Levels: `engine` = low-level workflow steps (GoliathApp), `core` = GoliathApp core-entity actions, `domain` = GoliathGroundStation business actions. Every user-facing action uses `exposure=ActionExposure.RBAC` and names its `entity_code`; internal helper steps use `ActionExposure.HIDDEN`.

| `action_name` | Level | `entity_code` | Exposure | `required_permission` | Capability |
| --- | --- | --- | --- | --- | --- |
| `ground.it_event_collect_buffered` | domain | `ground.it_event` | HIDDEN | — | `ground.it_event` |
| `ground.it_event_flush_batch` | domain | `ground.it_event` | HIDDEN | — | `ground.it_event` |
| `ground.testlog_export_prepare` | domain | `ground.test_log` | RBAC | `ground.testlog.export` | `ground.testlog_export` |
| `ground.testlog_export_run` | domain | `ground.test_log` | HIDDEN | — | `ground.testlog_export` |
| `ground.testlog_export_finalize` | domain | `ground.test_log` | HIDDEN | — | `ground.testlog_export` |
| `ground.config_fixture_apply` | domain | `ground.campaign` | RBAC | `ground.config.apply` | `ground.config_campaign` |
| `ground.config_promote_site` | domain | `ground.vehicle` | RBAC | `ground.config.promote` | `ground.config_campaign` |

### Example ActionSpec

```python
from goliath_app.actions.spec import ActionExposure, ActionLevel, ActionSpec

TESTLOG_EXPORT_PREPARE = ActionSpec(
    action_name="ground.testlog_export_prepare",
    namespace="ground",
    level=ActionLevel.DOMAIN,
    entity_code="test_log",
    display_name="Prepare test-log export",
    description="Snapshot a campaign test log and stage export files.",
    exposure=ActionExposure.RBAC,
    required_permission="ground.testlog.export",
    input_model=TestlogExportPrepareInput,
    output_model=TestlogExportPrepareOutput,
    schema_version="1",
    capability="ground.testlog_export",
    tool="ground-testlog-export",
)
```

```toml
# pyproject.toml
[project.entry-points."goliath.action_catalogs"]
ground = "goliathgroundstation.actions.catalog:ACTIONS"
```

## NavTree extension

GoliathGroundStation **adds** nodes to `portal."NavTree"` with `portal.sp_nav_register_node(p_parent_id, p_caption, p_seq, p_info_id, p_node_path, p_sort_path)` and grants them in `portal."Role2Node"` (`ScopeId`, `RoleId`, `NodeId`). It never updates or deletes GoliathApp foundation nodes (home, organizations, users and roles, workflows, admin); it only attaches a top-level **Ground Station** node beside them and children under it. Captions stay within `varchar(50)`. Each leaf's `InfoID` points to the entity, request, or action it opens.

| Node path | Opens | Roles (`Role2Node`) |
| --- | --- | --- |
| Ground Station | group node beside foundation menus | all ground roles |
| Ground Station › Campaigns | `ground.campaign.list`; action `ground.config_fixture_apply` | test director, engineer |
| Ground Station › Test logs & export | `ground.test_log.by_campaign`; action `ground.testlog_export_prepare` | engineer, test director |
| Ground Station › I&T events | `ground.it_event.window` | engineer, viewer |
| Ground Station › Stations & tag trees | `ground.station.list`, `ground.tag_tree.for_station` | ops admin |
| Ground Station › Configuration | existing Astra configurator (live API until Phase 4); action `ground.config_promote_site` | ops admin, test director |

Role2Node rows are scoped per organization (`ScopeId`); the release seeder inserts them idempotently after the nodes exist. Foundation menus remain exactly as GoliathApp ships them.

## Reuse of GoliathApp

| Concern | Comes from GoliathApp | GoliathGroundStation adds |
| --- | --- | --- |
| Organizations and tenancy | `portal."Organizations"`, `portal.fn_semantic_user_organization_ids` | Site/vehicle program belongs to an organization; Astra config tables unchanged |
| RBAC | `RBAC` roles, `"RBAC"."UserRoleGrants"`, `"RBAC"."Role_Permissions"`, sessions | `ground.*` permissions and role bundles |
| Audit and e-signature | Platform append-only audit and signature service | Domain meanings for signatures |
| Read API | `portal.sp_run_semantic_request`, `PortalClient`, Exograph GraphQL + optional MCP (`goliath_portal` role, read-only) | Registry rows only |
| Writes | REST gateway → `wf.sp_*` / `portal.sp_*` ops and `ActionSpec` actions | Domain actions |

There is no per-app "stored procedures are the API" surface: internal domain procedures exist only as `target_name` of semantic requests or as action handlers.

## Appendix: physical mapping (internal)

| Source | Role |
| --- | --- |
| `database/schema/` Astra config tables (imported from astra-ground-station-py @ 2f91f43) | Back `ground.vehicle`, `ground.station`, `ground.tag_tree` through views; not rewritten into Meta |
| `database/schema/04_it_event_log.sql` (`testlog.it_event`) | Backs `ground.it_event` via `testlog.v_it_event` |
| Astra `testlog` campaign / job tables | Back `ground.campaign`, `ground.test_log` |
| `database/schema/05_domain_action_catalog.sql` | Former comment-only seed notes; superseded by the `ActionSpec` list above |

Views and the namespace seeder are planned work (tracked with #8); none of this changes the live gateway, TMoIP, or OPC publish path.
