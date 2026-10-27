# DomainProgram stubs (GoliathGroundStation)

JSON sketches for GoliathApp **DomainProgram** compile and seed. They follow the same IR as [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics) (`programVersion: 2`, `action` / `do` steps naming `wf.workflow_action.action_name`).

**Status:** stubs only — no workers in this repository yet; handlers await platform catalog seed and a ground-station worker package.

Validate locally:

```bash
pip install -e ".[dev]"
pytest tests/test_domain_program_stubs.py -q
```

See [docs/domain-programs.md](../docs/domain-programs.md) for scope, OPC boundary, and action catalog. Dual activation (tier 2): [docs/dual-activation-tier2.md](../docs/dual-activation-tier2.md).
