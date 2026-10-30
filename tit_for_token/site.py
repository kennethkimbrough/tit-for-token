"""Build the static results site for a committed run.

    python -m tit_for_token site runs/m1-small-models --out site

The output is one self-contained ``index.html``: the template in
``site_template.html`` with the run's data embedded as JSON. Every number on
the page is computed here from the run's ``matches.jsonl`` with the same
analysis functions the Markdown report uses, so the site and the report
cannot disagree.
"""

from __future__ import annotations

import html
import json
import re
from importlib import resources
from pathlib import Path

from .analysis import Change, Estimate, compare_runs, mutual_cooperation, payoff_matrix, summarize_players
from .config import load_config
from .runner import load_matches

BOT_LABELS = {
    "always-cooperate": "Always Cooperate",
    "always-defect": "Always Defect",
    "tit-for-tat": "Tit-for-Tat",
    "grim-trigger": "Grim Trigger",
    "random": "Random",
}

BOT_RULES_TEXT = {
    "always-cooperate": "Always plays A.",
    "always-defect": "Always plays B.",
    "tit-for-tat": "Plays A first, then copies the opponent's last move.",
    "grim-trigger": "Plays A until the opponent plays B once, then B forever.",
    "random": "Plays A or B with equal chance.",
}

#: Display names for model ids, used when a config does not give a ``label``.
MODEL_LABELS = {
    "anthropic/claude-haiku-5.5": "Claude Haiku 5.5",
    "openai/gpt-5-mini": "GPT-5 mini",
    "google/gemini-2.5-flash": "Gemini 2.5 Flash",
    "deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash",
}

#: Short names for the pairing grid's row and column headers.
SHORT_LABELS = {
    "always-cooperate": "Always A",
    "always-defect": "Always B",
    "tit-for-tat": "Tit-for-Tat",
    "grim-trigger": "Grim",
    "random": "Random",
    "anthropic/claude-haiku-5.5": "Haiku",
    "openai/gpt-5-mini": "GPT-5 mini",
    "google/gemini-2.5-flash": "Gemini",
    "deepseek/deepseek-v4.1-flash": "DeepSeek",
}

REPO_URL = "https://github.com/kennethkimbrough/tit-for-token"


def _estimate(e: Estimate) -> dict | None:
    if e.n_matches == 0 or e.value != e.value:
        return None
    return {"v": round(e.value, 4), "lo": round(e.low, 4), "hi": round(e.high, 4), "n": e.n_matches}


def render_markdown(text: str) -> str:
    """A small Markdown subset for run notes: ### headings, - bullets, paragraphs, **bold**, *italic*, `code`, [links](url)."""

    def inline(s: str) -> str:
        s = html.escape(s, quote=False)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", s)

        def link(m: re.Match) -> str:
            url = m.group(2)
            if not re.match(r"^(https?://|#)", url):
                return m.group(1)  # relative links have no meaning on the site
            return f'<a href="{html.escape(url)}">{m.group(1)}</a>'

        return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)

    out: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []

    def flush() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
        elif line.startswith("### "):
            flush()
            out.append(f"<h3>{inline(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            if paragraph:
                flush()
            items.append(line[2:].strip())
        elif items and raw.startswith("  "):
            items[-1] += " " + line.strip()
        else:
            if items:
                flush()
            paragraph.append(line.strip())
    flush()
    return "\n".join(out)


def _change(c: Change) -> dict | None:
    d = c.diff
    if d.n_matches == 0 or d.value != d.value:
        return None
    return {"a": round(c.first.value, 4), "b": round(c.second.value, 4), "d": round(d.value, 4),
            "lo": round(d.low, 4), "hi": round(d.high, 4), "n": d.n_matches}


def framing_data(base_dir: Path, other_dir: Path, reps: int = 2000) -> dict:
    """The paired comparison of a second run (e.g. a different framing) against the main run."""
    base = list(load_matches(Path(base_dir) / "matches.jsonl").values())
    other = list(load_matches(Path(other_dir) / "matches.jsonl").values())
    rows = compare_runs(base, other, reps)
    config = load_config(Path(other_dir) / "config.toml")
    notes = Path(other_dir) / "notes.md"
    return {
        "path": f"runs/{Path(other_dir).name}",
        "framing": config.framing,
        "shared": len({m.match_id for m in base} & {m.match_id for m in other}),
        "rows": [
            {"name": r.player, "matches": r.matches, "cooperation": _change(r.cooperation),
             "retaliation": _change(r.retaliation), "forgiveness": _change(r.forgiveness)}
            for r in rows
        ],
        "notes_html": render_markdown(notes.read_text(encoding="utf-8")) if notes.exists() else "",
    }


def site_data(run_dir: Path, reps: int = 2000, featured: str | None = None, compare: Path | None = None) -> dict:
    run_dir = Path(run_dir)
    config = load_config(run_dir / "config.toml")
    matches = list(load_matches(run_dir / "matches.jsonl").values())
    if not matches:
        raise ValueError(f"no matches in {run_dir}")
    run_info = json.loads((run_dir / "run.json").read_text(encoding="utf-8")) if (run_dir / "run.json").exists() else {}
    call_stats = run_info.get("calls_by_model", {})
    specs = {m.name: m for m in config.models}

    players = []
    for p in summarize_players(matches, reps):
        spec = specs.get(p.player)
        if spec is not None:
            stats = call_stats.get(spec.model, {})
            calls = stats.get("calls") or 0
            info = {
                "kind": "model",
                "label": getattr(spec, "label", None) or MODEL_LABELS.get(spec.model, spec.model),
                "short": SHORT_LABELS.get(spec.model, p.player),
                "model": spec.model,
                "reasoning": spec.reasoning,
                "reasoning_tokens_per_call": round(stats["reasoning_tokens"] / calls) if calls else None,
                "latency_ms_p50": stats.get("latency_ms_p50"),
            }
        else:
            info = {
                "kind": "bot",
                "label": BOT_LABELS.get(p.player, p.player),
                "short": SHORT_LABELS.get(p.player, p.player),
                "rule": BOT_RULES_TEXT.get(p.player, ""),
            }
        players.append({
            "name": p.player,
            **info,
            "matches": p.matches,
            "payoff": _estimate(p.payoff),
            "cooperation": _estimate(p.cooperation),
            "retaliation": _estimate(p.retaliation),
            "forgiveness": _estimate(p.forgiveness),
            "vs_always_cooperate": _estimate(p.vs_always_cooperate),
            "fingerprints": {k: _estimate(v) for k, v in p.fingerprints.items()},
            "retried": _estimate(p.retried),
            "forfeits": _estimate(p.forfeits),
            "truncated": _estimate(p.truncated),
        })

    mutual = {f"{a}|{b}": _estimate(e) for (a, b), e in sorted(mutual_cooperation(matches, reps).items())}
    payoff = {row: {col: round(v, 4) for col, v in sorted(cols.items()) if v == v} for row, cols in sorted(payoff_matrix(matches).items())}

    encoded = []
    for m in sorted(matches, key=lambda m: m.match_id):
        flags = []
        for i, r in enumerate(m.rounds):
            for seat in (0, 1):
                if r.flags[seat]:
                    flags.append([seat, i, ",".join(r.flags[seat])])
        encoded.append({
            "id": m.match_id,
            "p": list(m.players),
            "m": ["".join(m.moves_of(0)), "".join(m.moves_of(1))],
            "s": list(m.scores),
            "f": flags,
        })

    ids = {m["id"] for m in encoded}
    if featured is not None and featured not in ids:
        raise ValueError(f"featured match {featured!r} is not in {run_dir}")

    notes_path = run_dir / "notes.md"
    return {
        "framing": framing_data(run_dir, compare, reps) if compare else None,
        "featured": featured or encoded[0]["id"],
        "run": {
            "name": config.name,
            "path": f"runs/{run_dir.name}",
            "matches": len(matches),
            "rounds": sum(len(m.rounds) for m in matches),
            "model_calls": run_info.get("recorded_calls"),
            "matches_per_pairing": config.matches_per_pairing,
            "end_probability": config.rules.end_probability,
            "temperature": config.temperature,
            "seed": config.seed,
            "bootstrap_reps": reps,
        },
        "repo": REPO_URL,
        "players": players,
        "mutual": mutual,
        "payoff": payoff,
        "matches": encoded,
        "notes_html": render_markdown(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else "",
    }


def build_site(run_dir: Path, out_dir: Path, reps: int = 2000, featured: str | None = None,
               compare: Path | None = None) -> Path:
    data = site_data(run_dir, reps, featured, compare)
    # "</" must not appear inside a <script> element; "<\/" is the same string to JSON.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True).replace("</", "<\\/")
    template = resources.files("tit_for_token").joinpath("site_template.html").read_text(encoding="utf-8")
    page = template.replace("/*__DATA__*/null", payload)
    if page == template:
        raise RuntimeError("site template has no data placeholder")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "index.html"
    target.write_text(page, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return target
