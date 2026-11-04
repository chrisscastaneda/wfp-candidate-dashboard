"""Store, publish and manual entries, using a temporary data directory."""
import csv

import pytest

from elex import config, publish, store
from elex.model import OK, Choice, Contest, SourceResult
from elex.states import manual


@pytest.fixture
def tmp_results(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "LATEST", tmp_path / "latest")
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(config, "MANUAL_FILE", tmp_path / "manual_entries.csv")
    return tmp_path


def _result(votes):
    c = Contest(source="x", contest_id="1", state="CA", title="T", office_type="state_house", district="1",
                choices=[Choice("A", votes), Choice("B", 5)])
    return SourceResult("x", OK, [c], fetched_at="2026-11-03T00:00:00+00:00")


def test_history_written_only_on_change(tmp_results):
    for run_id, votes in (("r1", 1), ("r2", 1), ("r3", 9)):
        record, changed = store.merge(store.load("x"), _result(votes))
        store.save("x", record, changed, run_id)
    assert sorted(p.stem for p in (tmp_results / "history" / "x").iterdir()) == ["r1", "r3"]


def test_blocked_pull_keeps_previous_contests(tmp_results):
    record, changed = store.merge(None, _result(3))
    store.save("x", record, changed, "r1")
    record, changed = store.merge(store.load("x"), SourceResult("x", "blocked", message="403"))
    assert not changed and record["status"] == "blocked" and len(record["contests"]) == 1


def test_publish_leading_and_statuses():
    c = Contest(source="x", contest_id="1", state="CA", title="T", office_type="state_house", district="1",
                choices=[Choice("A", 10), Choice("B", 5)])
    rows = [{"state": "CA", "name": "A", "office": "o", "status": "auto", "source": "x", "contest_id": "1",
             "choice_id": "A", "choice": "A", "note": ""}]
    e = [{"id": 7, "key": "CA|A|o", "name": "A"}]
    out = publish.build(e, rows, {"x": {"contests": [c], "status": "ok"}}, "r")
    assert out["results"]["7"]["status"] == "counting" and out["results"]["7"]["wfp_leading"] is True


def test_publish_source_link():
    rows = [{"state": "GA", "name": "A", "office": "o", "status": "auto", "source": "ga", "contest_id": "1",
             "choice_id": "A", "choice": "A", "note": ""}]
    e = [{"id": 7, "key": "GA|A|o", "name": "A"}]

    def link(source, url=None):
        c = Contest(source=source, contest_id="1", state="GA", title="T", office_type="state_house", url=url,
                    choices=[Choice("A", 10)])
        r = publish.build(e, [dict(rows[0], source=source)], {source: {"contests": [c], "status": "ok"}}, "r")
        return r["results"]["7"]["source_name"], r["results"]["7"]["source_url"]

    assert link("ga") == ("Georgia Secretary of State", "https://results.sos.ga.gov/results/public/Georgia")
    # A contest's own page wins; hand entries are named by host.
    assert link("manual", "https://www.nj.gov/state/x.shtml") == ("nj.gov", "https://www.nj.gov/state/x.shtml")


def test_manual_template_keeps_entered_rows(tmp_results, monkeypatch):
    rows = [{"id": 1, "name": "Rashida Tlaib", "office": "U.S. House of Representatives, District 12",
             "office_category": "Federal House", "state_code": "MI", "nov3_ballot": "expected",
             "official_source_url": "https://example"}]
    monkeypatch.setattr(manual.endorsements, "load", lambda: rows)
    added, ids = manual.write_template(covered_states=set())
    assert ids == ["mi.us-house.12"]
    entries = manual.read_rows()
    entries[0]["votes"] = "100"
    entries.append({**entries[0], "choice": "Opponent", "votes": "50", "note": ""})
    with config.MANUAL_FILE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=manual.COLUMNS)
        w.writeheader()
        w.writerows(entries)
    assert manual.write_template(covered_states=set())[0] == 0
    contests = manual.parse(manual.read_rows())
    assert [(ch.name, ch.votes) for ch in contests[0].choices] == [("Rashida Tlaib", 100), ("Opponent", 50)]
    assert contests[0].office_type == "federal_house" and contests[0].district == "12"
