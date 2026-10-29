"""Tournament configuration, read from a TOML file (see ``configs/`` for examples)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .engine import Rules
from .llm import Price


@dataclass(frozen=True)
class ModelSpec:
    name: str  # short name used in match ids and results
    model: str  # provider's model id, e.g. "anthropic/claude-haiku-5.5"
    provider: str = "openrouter"
    price: Price = Price(0.0, 0.0)
    concurrency: int = 4
    temperature: float | None = None  # None = tournament default
    max_tokens: int | None = None
    reasoning: str | None = None  # reasoning effort for models that reason; None sends nothing


@dataclass(frozen=True)
class TournamentConfig:
    name: str
    seed: int
    matches_per_pairing: int
    bots: tuple[str, ...]
    models: tuple[ModelSpec, ...]
    rules: Rules = Rules()
    spending_cap_usd: float = 1.0
    temperature: float = 0.7
    max_tokens: int = 50
    self_play: bool = True
    parallel_matches: int = 16
    source: dict = field(default_factory=dict, compare=False)

    @property
    def player_names(self) -> tuple[str, ...]:
        return tuple(self.bots) + tuple(m.name for m in self.models)

    def validate(self) -> None:
        names = list(self.player_names)
        if len(set(names)) != len(names):
            raise ValueError(f"player names must be unique: {names}")
        for n in names:
            if not n or "/" in n or "--" in n or any(c.isspace() for c in n):
                raise ValueError(f"player name {n!r} may not contain '/', '--' or whitespace")
        if self.parallel_matches < 1:
            raise ValueError("parallel_matches must be at least 1")
        if self.matches_per_pairing < 1:
            raise ValueError("matches_per_pairing must be at least 1")
        if self.spending_cap_usd < 0:
            raise ValueError("spending_cap_usd must not be negative")


def load_config(path: Path | str) -> TournamentConfig:
    path = Path(path)
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return config_from_dict(raw)


def config_from_dict(raw: dict) -> TournamentConfig:
    defaults = raw.get("model_defaults", {})
    models = []
    for m in raw.get("models", []):
        price = m.get("price", {})
        models.append(
            ModelSpec(
                name=m["name"],
                model=m["model"],
                provider=m.get("provider", "openrouter"),
                price=Price(float(price.get("input_usd_per_million", 0.0)), float(price.get("output_usd_per_million", 0.0))),
                concurrency=int(m.get("concurrency", 4)),
                temperature=m.get("temperature"),
                max_tokens=m.get("max_tokens"),
                reasoning=m.get("reasoning"),
            )
        )
    cfg = TournamentConfig(
        name=raw["name"],
        seed=int(raw["seed"]),
        matches_per_pairing=int(raw.get("matches_per_pairing", 10)),
        bots=tuple(raw.get("bots", [])),
        models=tuple(models),
        rules=Rules(end_probability=float(raw.get("end_probability", 0.1)), max_rounds=int(raw.get("max_rounds", 200))),
        spending_cap_usd=float(raw.get("spending_cap_usd", 1.0)),
        temperature=float(defaults.get("temperature", 0.7)),
        max_tokens=int(defaults.get("max_tokens", 50)),
        self_play=bool(raw.get("self_play", True)),
        parallel_matches=int(raw.get("parallel_matches", 16)),
        source=raw,
    )
    cfg.validate()
    return cfg
