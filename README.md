# GoliathGroundStation

GoliathApp specialization for launch-ops ground station: singleton rocket gateway, OPC UA fan-out to N monitor stations, and platform identity without turning live telemetry into workflow workers.

## Phase 2 layout (this repository)

| Path | Purpose |
| --- | --- |
| [`docs/conversion-plan.md`](docs/conversion-plan.md) | Customer deliverables, architecture, phased checklist |
| [`docs/operator-identity.md`](docs/operator-identity.md) | GoliathApp portal sessions vs worker sessions; deploy `operators` hooks |
| [`deploy/`](deploy/) | Deploy topology, systemd stubs, customer **target profiles** |
| [`deploy/targets/`](deploy/targets/) | `target.schema.json` + example JSON per site |
| [`src/goliathgroundstation/`](src/goliathgroundstation/) | Thin Python product shell (will specialize GoliathApp) |
| [`pyproject.toml`](pyproject.toml) | Packaging metadata; no private runtime dependencies |
| [`.goliath/product.json`](.goliath/product.json) | GoliathWeb catalog entry |

Runtime daemons (gateway, TMoIP, web, exporter) are **not** migrated in this slice. Deploy units and targets describe how a site is wired; implementation arrives in later Phase 2 work.

## Deploy profiles

Each customer site is a JSON file under `deploy/targets/` validated by `target.schema.json`:

- **One singleton gateway host** — ingest, decode, publish OPC UA (not a worker pool).
- **`monitors[]`** — inventory of OPC subscriber stations (LabVIEW, integration UIs). They subscribe; they do not claim leased GoliathApp tasks.
- **Sibling services** — TMoIP, configurator web, batch exporter as systemd units on the gateway or separate hosts.
- **Secrets** — only `secret:NAME` references in JSON; values live in env files on the host.
- **`operators`** (optional) — required RBAC roles, portal session source (`goliathapp_portal`), Phase 3 OPC tag-tree ACL flag; uses `database.portal_role` for the `goliath_portal` DB login.

See [`deploy/README.md`](deploy/README.md) for topology and validation commands.

```bash
pip install -e ".[dev]"
python scripts/validate_deploy_target.py deploy/targets/goliath-ground-test.example.json
```

## Docs

- [Conversion plan](docs/conversion-plan.md) — deliverables, architecture (Mermaid), phases, and checklist
- [Operator identity](docs/operator-identity.md) — portal RBAC for configurator operators; monitors are OPC clients, not workers ([GoliathApp RBAC](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/rbac.md), [workers contrast](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/workers.md))

## Related

| Product | Role |
| --- | --- |
| [GoliathApp](https://github.com/Goliath-Research/GoliathApp) | Platform (RBAC, portal shell, optional DomainPrograms) |
| [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics) | Parallel customization pattern (genomics; uses workflow workers) |
| [GoliathWeb](https://github.com/Goliath-Research/GoliathWeb) | Public catalog (Phase 1 product page) |

## License

MIT — Copyright 2026 Goliath Research.
