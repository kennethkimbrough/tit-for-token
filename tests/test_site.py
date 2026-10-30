import asyncio
import json
import re

import pytest
from conftest import FakeModelTransport

from tit_for_token.analysis import summarize_players
from tit_for_token.config import config_from_dict
from tit_for_token.runner import load_matches, run_tournament
from tit_for_token.site import build_site, render_markdown, site_data

RAW = {
    "name": "site-test",
    "seed": 5,
    "matches_per_pairing": 2,
    "end_probability": 0.3,
    "bots": ["tit-for-tat", "always-defect"],
    "models": [{"name": "m1", "model": "fake/one", "reasoning": "low"}],
}


@pytest.fixture
def run_dir(tmp_path):
    out = tmp_path / "runs" / "site-test"
    out.mkdir(parents=True)
    (out / "config.toml").write_text(
        'name = "site-test"\nseed = 5\nmatches_per_pairing = 2\nend_probability = 0.3\n'
        'bots = ["tit-for-tat", "always-defect"]\n[[models]]\nname = "m1"\nmodel = "fake/one"\nreasoning = "low"\n'
    )
    (out / "notes.md").write_text("### Findings\n\n- **Bold** claim with [a link](https://example.com) and `code`.\n- Second <b>item</b>\n")
    config = config_from_dict(RAW)
    asyncio.run(run_tournament(config, out, live_factory=lambda s: FakeModelTransport(malformed_every=5), log=lambda *a: None))
    return out


def embedded(html: str) -> dict:
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert m, "the data block is in the page"
    return json.loads(m.group(1))


def test_site_embeds_every_match_and_the_same_numbers_as_the_report(run_dir, tmp_path):
    target = build_site(run_dir, tmp_path / "site", reps=50)
    html = target.read_text()
    data = embedded(html)
    matches = load_matches(run_dir / "matches.jsonl")

    assert data["run"]["matches"] == len(matches) == 2 * 4
    assert sorted(m["id"] for m in data["matches"]) == sorted(matches)
    first = matches[sorted(matches)[0]]
    encoded = next(m for m in data["matches"] if m["id"] == first.match_id)
    assert encoded["m"] == ["".join(first.moves_of(0)), "".join(first.moves_of(1))]
    assert encoded["s"] == list(first.scores)

    summaries = {p.player: p for p in summarize_players(list(matches.values()), reps=50)}
    for p in data["players"]:
        assert p["cooperation"]["v"] == round(summaries[p["name"]].cooperation.value, 4)
    m1 = next(p for p in data["players"] if p["name"] == "m1")
    assert m1["kind"] == "model" and m1["reasoning"] == "low" and m1["label"] == "fake/one"
    tft = next(p for p in data["players"] if p["name"] == "tit-for-tat")
    assert tft["kind"] == "bot" and tft["label"] == "Tit-for-Tat" and "copies" in tft["rule"]
    assert any(m["f"] for m in data["matches"]), "flags reach the page"
    assert (tmp_path / "site" / ".nojekyll").exists()


def test_featured_match_is_validated(run_dir):
    assert site_data(run_dir, reps=10)["featured"] == sorted(load_matches(run_dir / "matches.jsonl"))[0]
    some_id = sorted(load_matches(run_dir / "matches.jsonl"))[3]
    assert site_data(run_dir, reps=10, featured=some_id)["featured"] == some_id
    with pytest.raises(ValueError):
        site_data(run_dir, reps=10, featured="no-such-match")


def test_embedded_json_cannot_close_the_script_tag(run_dir, tmp_path):
    (run_dir / "notes.md").write_text("A note mentioning </script><script>alert(1)</script> literally.\n")
    html = build_site(run_dir, tmp_path / "site", reps=10).read_text()
    block = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert "</script" not in block
    assert "&lt;/script&gt;" in embedded(html)["notes_html"]


def test_render_markdown_subset():
    out = render_markdown(
        "### Title\n\nIntro line one\nline two.\n\n- **Bold** and *italic* with `x < y`\n  continued\n"
        "- [external](https://example.com) and [relative](runs/x.json)\n"
    )
    assert "<h3>Title</h3>" in out
    assert "<p>Intro line one line two.</p>" in out
    assert "<li><strong>Bold</strong> and <em>italic</em> with <code>x &lt; y</code> continued</li>" in out
    assert '<a href="https://example.com">external</a>' in out
    assert "relative" in out and "runs/x.json" not in out, "relative links become plain text on the site"


def test_site_includes_the_framing_comparison_when_asked():
    from pathlib import Path

    from tit_for_token.site import site_data

    root = Path(__file__).resolve().parents[1]
    data = site_data(root / "runs/m1-small-models", reps=50, compare=root / "runs/m3-named")
    f = data["framing"]
    assert f["framing"] == "named" and f["shared"] == 250
    assert sorted(r["name"] for r in f["rows"]) == ["deepseek-flash", "gemini-flash", "gpt-mini", "haiku"]
    gem = next(r for r in f["rows"] if r["name"] == "gemini-flash")
    assert gem["cooperation"]["a"] < gem["cooperation"]["b"] and gem["matches"] == 70
    assert site_data(root / "runs/m1-small-models", reps=50)["framing"] is None
