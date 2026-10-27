# GoliathGroundStation deploy

Customer topology for launch-ops ground station: **one singleton gateway** that ingests telemetry, decodes, and **publishes OPC UA once**; **N monitor stations** that subscribe; optional **sibling systemd services** for TMoIP, configurator web, and batch export.

This is **not** the GoliathOmics pattern of a gateway plus a farm of workflow workers that claim leased tasks. Live vehicle data never enters the GoliathApp worker claim loop.

## Topology

```text
                    ┌─────────────────────────────────────┐
  Umbilical / RF ──►│  Singleton ground gateway (1 host) │
                    │  ingest → decode → OPC UA publish   │
                    └──────────────┬──────────────────────┘
                                   │ opc.tcp (one bus)
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        Monitor A            Monitor B            Monitor N
     (OPC subscribe)       (LabVIEW host)      (integration UI)

  Colocated on gateway (typical) or documented separate hosts:
    • goliath-ground-tmoip     — minor-frame reassembly before decode
    • goliath-ground-web       — configurator / test campaigns (HTTP)
    • goliath-ground-exporter  — batch test-log jobs (not live OPC)
```

| Role | Count | GoliathApp workers? |
| --- | --- | --- |
| Ground gateway | **1** per site | No — domain service |
| Monitor station | **N** (engines, variables) | No — OPC clients only |
| TMoIP / web / exporter | 0–3 units | No — long-running or batch siblings |

Operator identity and RBAC come from **GoliathApp portal sessions** (not worker gateway sessions). Declarative policy lives in the target’s optional **`operators`** block and [`database.portal_role`](../deploy/targets/target.schema.json); see [operator identity](../docs/operator-identity.md). Domain SQL for `config` / `testlog` lives in [`database/schema/`](../database/schema/) with [`scripts/apply_domain_schema.sh`](../scripts/apply_domain_schema.sh) (target `schema.domain`: `per-release`). **DomainPrograms** (required in Phase 3) own sensor/actuator event logging and export campaigns; they do not replace the live OPC path. See [conversion-plan.md](../docs/conversion-plan.md).

## Deploy targets

JSON files under [`targets/`](targets/) describe a customer site:

- [`target.schema.json`](targets/target.schema.json) — JSON Schema (draft-07)
- [`goliath-ground-test.example.json`](targets/goliath-ground-test.example.json) — example test-bed profile (placeholders only)

Secrets in target files are **`secret:NAME` references** only. Real values live in `/etc/goliath/.env`, provider consoles, or your secret store — never in git.

### Validate an example target

```bash
# From repo root (requires Python 3.10+)
pip install -e ".[dev]"
python scripts/validate_deploy_target.py deploy/targets/goliath-ground-test.example.json
```

Or with Node (no Python deps):

```bash
npx --yes ajv-cli validate -s deploy/targets/target.schema.json -d deploy/targets/goliath-ground-test.example.json
```

## Systemd stubs

Unit templates under [`systemd/`](systemd/) are **placeholders** for the product-named services. Install paths and `ExecStart` are filled by a future `deploy_target.sh` (same idea as GoliathOmics). They do not bundle private Astra source code.

| Unit | Purpose |
| --- | --- |
| `goliath-ground-gateway.service` | Singleton ingest/decode/OPC publisher |
| `goliath-ground-tmoip.service` | TMoIP reassembly |
| `goliath-ground-web.service` | Configurator HTTP API |
| `goliath-ground-exporter.service` | Batch export to testlog |

Typical layout on the gateway host:

- `install_root` from the target (e.g. `/opt/goliath-ground`)
- `env/gateway.env`, `env/tmoip.env`, … — non-secret `EnvironmentFile`
- `/etc/goliath/ground-secrets.env` — mode `0600`, referenced as `secret:*` in the target

## Related docs

- [Conversion plan](../docs/conversion-plan.md) — phases, architecture, checklist
- [Operator identity](../docs/operator-identity.md) — portal RBAC hooks in deploy targets
- [GoliathApp RBAC](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/rbac.md) · [workers (contrast)](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/workers.md)
- [GoliathOmics deploy targets](https://github.com/Goliath-Research/GoliathOmics/tree/main/deploy/targets) — parallel *packaging* pattern (omics uses workers; ground station does not)
