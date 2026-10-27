# GoliathGroundStation

GoliathApp specialization for launch-ops ground station: singleton rocket gateway, OPC UA fan-out to N monitor stations, and platform identity without turning live telemetry into workflow workers.

This repository starts with the customer-facing [conversion plan](docs/conversion-plan.md). Runtime packaging lands in later phases as the private ground-station implementation migrates into this public product.

## Docs

- [Conversion plan](docs/conversion-plan.md) — deliverables, architecture (Mermaid), phases, and checklist

## Related

| Product | Role |
| --- | --- |
| [GoliathApp](https://github.com/Goliath-Research/GoliathApp) | Platform (RBAC, portal shell, optional DomainPrograms) |
| [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics) | Parallel customization pattern (genomics) |
| [GoliathWeb](https://github.com/Goliath-Research/GoliathWeb) | Public catalog (Phase 1 product page) |

## License

MIT — Copyright 2026 Goliath Research.
