from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_reconciliation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NBIM vs Custodian dividend reconciliation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Execute the reconciliation workflow")
    run_parser.add_argument(
        "--nbim-file",
        type=Path,
        default=Path("data/NBIM_Dividend_Bookings.csv"),
        help="Path to the NBIM source CSV file.",
    )
    run_parser.add_argument(
        "--custodian-file",
        type=Path,
        default=Path("data/CUSTODY_Dividend_Bookings.csv"),
        help="Path to the custodian source CSV file.",
    )
    run_parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory that will receive the reconciliation artefacts.",
    )
    run_parser.add_argument(
        "--tolerance",
        type=float,
        default=0.5,
        help="Absolute amount tolerance before a difference is considered a break.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        run_reconciliation(
            nbim_path=args.nbim_file,
            custodian_path=args.custodian_file,
            out_dir=args.out_dir,
            tolerance=args.tolerance,
        )
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":  # pragma: no cover - exercised via CLI entry point
    raise SystemExit(main())
