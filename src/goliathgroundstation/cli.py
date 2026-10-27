"""Placeholder CLI until gateway and configurator entrypoints migrate here."""

from __future__ import annotations

import argparse
import sys

from goliathgroundstation import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="goliath-ground",
        description="GoliathGroundStation product CLI (packaging shell).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.parse_args(argv)
    print(
        "GoliathGroundStation packaging shell — see deploy/README.md for topology.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
