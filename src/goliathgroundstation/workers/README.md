# Ground worker handler stubs

Lean **in-process handler placeholders** for GoliathGroundStation DomainPrograms. They implement the claim/submit **`output_json`** shape expected by program stubs under [`domain_programs/`](../../../domain_programs/) — not Astra ports, edge buffer I/O, or live OPC.

## Entry point

```python
from goliathgroundstation.workers import handle

output = handle("ground.it_event_flush_batch", {"campaignId": "c-1", "stagingRef": "..."})
```

- Unknown `action_name` → `UnknownActionError`.
- Every stub response includes `implementationStatus: "stub"` and a short `handlerNote`.

## Action → capability map

Workers on a test bed should advertise these **capabilities** (matches [`database/schema/05_domain_action_catalog.sql`](../../../database/schema/05_domain_action_catalog.sql) and [`docs/domain-programs.md`](../../../docs/domain-programs.md)):

| `action_name` | `capability` | Module |
| --- | --- | --- |
| `ground.it_event_collect_buffered` | `ground.it_event` | `handlers/it_event.py` |
| `ground.it_event_flush_batch` | `ground.it_event` | `handlers/it_event.py` |
| `ground.testlog_export_prepare` | `ground.testlog_export` | `handlers/testlog_export.py` |
| `ground.testlog_export_run` | `ground.testlog_export` | `handlers/testlog_export.py` |
| `ground.testlog_export_finalize` | `ground.testlog_export` | `handlers/testlog_export.py` |
| `ground.config_fixture_apply` | `ground.config_campaign` | `handlers/config_campaign.py` |
| `ground.config_promote_site` | `ground.config_campaign` | `handlers/config_campaign.py` |

Program graphs: [`sensor_actuator_event_logger.program.json`](../../../domain_programs/sensor_actuator_event_logger.program.json), [`testlog_export_campaign.program.json`](../../../domain_programs/testlog_export_campaign.program.json), [`config_fixture_promote_placeholder.program.json`](../../../domain_programs/config_fixture_promote_placeholder.program.json).

## Wake hints (tier 2)

Optional **`payload.worker_wake`** channel selection is **not** implemented here. Use [`goliathgroundstation.worker_wake`](../worker_wake.py) (`worker_wake_payload_for_program`, `worker_wake_hints_for_program`) when batch edges attach wake hints on gateway event ingest. Workers still **claim** tasks authoritatively; wakes only reduce idle latency.

## Out of scope

- Singleton gateway, Postgres wake broker, portal UI
- RunPod images or full GoliathApp worker enrollment
- `INSERT` into `testlog.it_event` or legacy export tables

Platform catalog seed should point `p_in_process_handler` (or equivalent) at these callables once a worker VM imports `goliathgroundstation`.
