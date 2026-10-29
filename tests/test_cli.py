import asyncio

from conftest import FakeModelTransport

from tit_for_token.cli import main
from tit_for_token.config import config_from_dict
from tit_for_token.runner import run_tournament

TOML = """
name = "cli-test"
seed = 3
matches_per_pairing = 2
end_probability = 0.3
bots = ["tit-for-tat", "always-defect"]
[[models]]
name = "m1"
model = "fake/one"
"""


def test_check_and_report_on_a_recorded_run(tmp_path, capsys):
    config_path = tmp_path / "cfg.toml"
    config_path.write_text(TOML)
    out = tmp_path / "run"
    out.mkdir()
    (out / "config.toml").write_text(TOML)
    import tomllib
    config = config_from_dict(tomllib.loads(TOML))
    asyncio.run(run_tournament(config, out, live_factory=lambda s: FakeModelTransport(), log=lambda *a: None))

    assert main(["check", str(out)]) == 0
    assert "reproduces matches.jsonl exactly" in capsys.readouterr().out

    assert main(["report", str(out), "--reps", "20"]) == 0
    text = capsys.readouterr().out
    assert "| m1 |" in text and "tit-for-tat" in text

    # Replay through the CLI into another directory also completes without a key or network.
    assert main(["run", str(config_path), "--out", str(tmp_path / "again"), "--replay", "--recording", str(out / "calls.jsonl")]) == 0
    assert (tmp_path / "again" / "matches.jsonl").read_bytes() == (out / "matches.jsonl").read_bytes()
