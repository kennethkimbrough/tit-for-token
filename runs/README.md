Committed tournament runs, one directory per run:

- `config.toml`: the configuration the run was made with
- `calls.jsonl`: the recording of every model call, the source of truth
- `matches.jsonl`: every match, one per line, sorted
- `run.json`: counts, spending, and per-model call statistics
- `report.md`: the report, as produced by `python -m tit_for_token report <dir>`

CI replays each run from its recording on every push and fails if the matches differ.
