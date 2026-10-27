# DomainProgram stubs (GoliathGroundStation)

JSON sketches for GoliathApp **DomainProgram** compile and seed. They follow the same IR as [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics) (`programVersion: 2`, `action` / `do` steps naming `wf.workflow_action.action_name`).

**Status:** program IR stubs plus in-repo **handler stubs** ([`src/goliathgroundstation/workers/`](../src/goliathgroundstation/workers/)). Platform compile/seed and real DB/export I/O remain open ([issue #8](https://github.com/Goliath-Research/GoliathGroundStation/issues/8)).

Validate locally:

```bash
pip install -e ".[dev]"
pytest tests/test_domain_program_stubs.py tests/test_worker_handlers.py -q
```

See [docs/domain-programs.md](../docs/domain-programs.md) for scope, OPC boundary, and action catalog. Dual activation (tier 2): [docs/dual-activation-tier2.md](../docs/dual-activation-tier2.md).
