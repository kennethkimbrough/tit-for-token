"""Command line.

    python -m tit_for_token run CONFIG.toml [--out DIR] [--replay] [--recording FILE]
    python -m tit_for_token report DIR [--reps N]
    python -m tit_for_token check DIR          replay DIR's config against its recording and compare
    python -m tit_for_token site DIR [--out site] [--featured MATCH_ID]   build the results site

``run`` plays (or resumes) a tournament. Without ``--replay`` it makes live
calls through OpenRouter, reusing any calls already in the recording; with
``--replay`` it makes no network calls at all.
"""

from __future__ import annotations

import argparse
import asyncio
import filecmp
import sys
import tempfile
from pathlib import Path

from .analysis import markdown_report
from .config import load_config
from .runner import copy_config, load_matches, run_tournament


def cmd_run(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = load_config(config_path)
    out_dir = Path(args.out) if args.out else Path("runs") / config.name
    copy_config(config_path, out_dir)
    recording = Path(args.recording) if args.recording else None
    result = asyncio.run(run_tournament(config, out_dir, replay=args.replay, recording_path=recording))
    if result.completed:
        print(f"results: python -m tit_for_token report {out_dir}")
        return 0
    return 3


def cmd_report(args: argparse.Namespace) -> int:
    matches = load_matches(Path(args.dir) / "matches.jsonl")
    if not matches:
        print(f"no matches in {args.dir}", file=sys.stderr)
        return 1
    print(markdown_report(list(matches.values()), reps=args.reps), end="")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Replay a committed run from its recording into a temporary directory and compare the matches."""
    run_dir = Path(args.dir)
    config = load_config(run_dir / "config.toml")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = asyncio.run(
            run_tournament(config, tmp_dir, replay=True, recording_path=run_dir / "calls.jsonl", log=lambda *a: None)
        )
        if not result.completed:
            print(f"{run_dir}: replay did not complete ({result.stopped_reason or 'missing recordings'})")
            return 1
        if filecmp.cmp(run_dir / "matches.jsonl", tmp_dir / "matches.jsonl", shallow=False):
            print(f"{run_dir}: replay reproduces matches.jsonl exactly ({result.total} matches)")
            return 0
        print(f"{run_dir}: replay differs from the committed matches.jsonl")
        return 1


def cmd_site(args: argparse.Namespace) -> int:
    from .site import build_site

    target = build_site(Path(args.dir), Path(args.out), reps=args.reps, featured=args.featured)
    print(f"wrote {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tit_for_token", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="play or resume a tournament")
    run.add_argument("config")
    run.add_argument("--out", help="run directory (default runs/<name>)")
    run.add_argument("--replay", action="store_true", help="no network: answer every call from the recording")
    run.add_argument("--recording", help="recording file (default <out>/calls.jsonl)")
    run.set_defaults(func=cmd_run)

    report = sub.add_parser("report", help="print the results of a run as Markdown")
    report.add_argument("dir")
    report.add_argument("--reps", type=int, default=1000, help="bootstrap resamples")
    report.set_defaults(func=cmd_report)

    check = sub.add_parser("check", help="verify a run replays exactly from its recording")
    check.add_argument("dir")
    check.set_defaults(func=cmd_check)

    site = sub.add_parser("site", help="build the static results site for a run")
    site.add_argument("dir")
    site.add_argument("--out", default="site", help="output directory (default site/)")
    site.add_argument("--featured", help="match id the viewer opens on")
    site.add_argument("--reps", type=int, default=2000, help="bootstrap resamples")
    site.set_defaults(func=cmd_site)

    args = parser.parse_args(argv)
    return args.func(args)
