"""Round-robin tournaments: scheduling, concurrency, the spending cap, resume, and the output files.

A run directory holds:

    config.toml     a copy of the configuration the run was made with
    calls.jsonl     the recording of every model call (``recorder.py``)
    matches.jsonl   one finished match per line, sorted by match id when the run completes
    run.json        summary: counts, spending, whether the run completed

Matches are appended to ``matches.jsonl`` as they finish so a crashed or
budget-capped run can resume; on completion the file is rewritten sorted so
two runs of the same tournament produce byte-identical files.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from .config import ModelSpec, TournamentConfig
from .engine import MatchRecord, Player, match_seed, play_match
from .llm import (
    Budget,
    BudgetExceeded,
    BudgetedTransport,
    OpenRouterTransport,
    RetryingTransport,
    ThrottledTransport,
    Transport,
)
from .players.bots import RandomBot, bot_by_name
from .players.model import ModelPlayer
from .recorder import Recording, RecordingTransport, ReplayTransport


@dataclass(frozen=True)
class Pairing:
    first: str
    second: str


def pairings(config: TournamentConfig) -> list[Pairing]:
    """Every unordered pair of distinct players, plus each model against itself."""
    names = config.player_names
    result = [Pairing(a, b) for a, b in combinations(names, 2)]
    if config.self_play:
        result += [Pairing(m.name, m.name) for m in config.models]
    return result


def match_id(pairing: Pairing, index: int) -> str:
    return f"{pairing.first}--{pairing.second}--{index:03d}"


def all_match_ids(config: TournamentConfig) -> list[tuple[Pairing, str]]:
    return [(p, match_id(p, i)) for p in pairings(config) for i in range(config.matches_per_pairing)]


class PlayerFactory:
    """Builds a fresh player object for each match (bots are cheap; the random bot needs the match seed)."""

    def __init__(self, config: TournamentConfig, transports: dict[str, Transport]) -> None:
        self._config = config
        self._transports = transports
        self._models = {m.name: m for m in config.models}

    def make(self, name: str, seed: int) -> Player:
        if name in self._models:
            spec: ModelSpec = self._models[name]
            return ModelPlayer(
                name=spec.name,
                model=spec.model,
                transport=self._transports[spec.name],
                temperature=spec.temperature if spec.temperature is not None else self._config.temperature,
                max_tokens=spec.max_tokens if spec.max_tokens is not None else self._config.max_tokens,
                reasoning=spec.reasoning,
                framing=self._config.framing,
            )
        bot = bot_by_name(name)
        if isinstance(bot, RandomBot):
            bot.reseed(seed)
        return bot


def build_transports(
    config: TournamentConfig,
    recording: Recording,
    replay: bool,
    budget: Budget,
    live_factory=None,
) -> dict[str, Transport]:
    """One transport per model. ``live_factory(spec)`` builds the raw transport; the default is OpenRouter."""
    if replay:
        return {m.name: ReplayTransport(recording) for m in config.models}

    if live_factory is None:
        def live_factory(spec: ModelSpec) -> Transport:
            return OpenRouterTransport()

    per_provider: dict[str, Transport] = {}
    transports: dict[str, Transport] = {}
    for spec in config.models:
        if spec.provider not in per_provider:
            per_provider[spec.provider] = RetryingTransport(live_factory(spec))
        throttled = ThrottledTransport(per_provider[spec.provider], spec.concurrency)  # a limit per model
        budgeted = BudgetedTransport(throttled, budget, spec.price)
        transports[spec.name] = RecordingTransport(budgeted, recording)
    return transports


def load_matches(path: Path) -> dict[str, MatchRecord]:
    matches: dict[str, MatchRecord] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = MatchRecord.from_dict(json.loads(line))
                    matches[rec.match_id] = rec
    return matches


def write_matches_sorted(path: Path, matches: dict[str, MatchRecord]) -> None:
    lines = [json.dumps(matches[k].to_dict(), sort_keys=True) for k in sorted(matches)]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


@dataclass
class RunResult:
    completed: bool
    played: int
    skipped: int
    total: int
    spent_usd: float
    live_calls: int
    stopped_reason: str = ""


async def run_tournament(
    config: TournamentConfig,
    out_dir: Path,
    replay: bool = False,
    recording_path: Path | None = None,
    live_factory=None,
    parallel_matches: int | None = None,
    log=print,
) -> RunResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    recording = Recording(recording_path or out_dir / "calls.jsonl")
    budget = Budget(config.spending_cap_usd)
    transports = build_transports(config, recording, replay, budget, live_factory)
    factory = PlayerFactory(config, transports)

    matches_path = out_dir / "matches.jsonl"
    done = load_matches(matches_path)
    todo = [(p, mid) for p, mid in all_match_ids(config) if mid not in done]
    total = len(done) + len(todo)
    log(f"{config.name}: {len(done)} of {total} matches already done, {len(todo)} to play"
        + (" (replay)" if replay else ""))

    write_lock = asyncio.Lock()
    gate = asyncio.Semaphore(parallel_matches or config.parallel_matches)
    stop = asyncio.Event()
    stopped_reason = ""

    async def one(pairing: Pairing, mid: str) -> None:
        nonlocal stopped_reason
        async with gate:
            if stop.is_set():
                return
            seed = match_seed(config.seed, mid)
            first = factory.make(pairing.first, seed)
            second = factory.make(pairing.second, seed + 1)
            try:
                rec = await play_match(mid, first, second, seed, config.rules)
            except BudgetExceeded as e:
                if not stop.is_set():
                    stopped_reason = str(e)
                    stop.set()
                return
            async with write_lock:
                done[mid] = rec
                finished = len(done) - (total - len(todo))
                if finished % 25 == 0 or finished == len(todo):
                    log(f"  {finished}/{len(todo)} matches played, ${budget.spent:.4f} spent")
                with matches_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec.to_dict(), sort_keys=True) + "\n")

    await asyncio.gather(*(one(p, mid) for p, mid in todo))

    completed = len(done) == total
    if completed:
        write_matches_sorted(matches_path, done)
    live_calls = sum(getattr(t, "live_calls", 0) for t in transports.values())
    result = RunResult(
        completed=completed,
        played=len(done) - (total - len(todo)),
        skipped=total - len(todo),
        total=total,
        spent_usd=budget.spent,
        live_calls=live_calls,
        stopped_reason=stopped_reason,
    )
    (out_dir / "run.json").write_text(
        json.dumps(
            {
                "name": config.name,
                "completed": completed,
                "matches": len(done),
                "matches_total": total,
                "live_calls": live_calls,
                "recorded_calls": len(recording),
                "calls_by_model": recording.call_stats(),
                "spent_usd": round(budget.spent, 6),
                "replay": replay,
                "stopped_reason": stopped_reason,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if stopped_reason:
        log(f"stopped: {stopped_reason}")
    log(f"{'completed' if completed else 'incomplete'}: {len(done)}/{total} matches, "
        f"{live_calls} live calls, ${budget.spent:.4f} spent")
    return result


def copy_config(config_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "config.toml"
    if not target.exists() or target.read_bytes() != Path(config_path).read_bytes():
        shutil.copyfile(config_path, target)
