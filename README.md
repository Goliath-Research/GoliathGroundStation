# GoliathGroundStation

GoliathApp specialization for launch-ops ground station: singleton rocket gateway, OPC UA fan-out to N monitor stations, and platform identity without turning live telemetry into workflow workers.

This repository starts with the customer-facing conversion plan from [astra-ground-station-py](https://github.com/Goliath-Research/astra-ground-station-py). Runtime packaging lands in later phases.

## Docs

- [Conversion plan](docs/conversion-plan.md) — deliverables, architecture (Mermaid), phases, and checklist

## Related

| Product | Role |
| --- | --- |
| [GoliathApp](https://github.com/Goliath-Research/GoliathApp) | Platform (RBAC, portal shell, optional DomainPrograms) |
| [astra-ground-station-py](https://github.com/Goliath-Research/astra-ground-station-py) | Current ground-station implementation |
| [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics) | Parallel customization pattern (genomics) |
| [GoliathWeb](https://github.com/Goliath-Research/GoliathWeb) | Public catalog (Phase 1 product page) |

## License

MIT — Copyright 2026 Goliath Research.
