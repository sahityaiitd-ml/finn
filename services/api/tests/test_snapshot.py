import json
from pathlib import Path

SNAP = Path(__file__).resolve().parents[3] / "data" / "demo" / "snapshot"


def test_snapshot_files_exist_and_hold_the_demo():
    filings = json.loads((SNAP / "filings.json").read_text())
    guidance = json.loads((SNAP / "guidance.json").read_text())
    matches = json.loads((SNAP / "promise_matches.json").read_text())
    assert len(filings) >= 50 and {"id", "symbol", "headline", "published_at"} <= set(filings[0])
    assert len(guidance) == len(matches) > 0
    ids = {g["id"] for g in guidance}
    assert all(m["guidance_id"] in ids for m in matches)  # every status points at a promise
    assert all(g["quote"] and g["page"] >= 1 for g in guidance)  # every promise cites a page


def test_every_snapshot_status_is_one_of_the_six():
    ok = {"Delivered", "Missed", "Partly", "Vague", "Not yet due", "No comparable actual"}
    assert {m["status"] for m in json.loads((SNAP / "promise_matches.json").read_text())} <= ok
