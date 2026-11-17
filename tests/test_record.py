"""Wallet records and the per-wallet report: loading, provenance, mapping to the simulator, and the report on the first wallet."""
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from walletsim.fold_screen import outer_fibre_strain
from walletsim.record import PROVENANCE, RecordError, load_wallet
from walletsim.report import build_report, failure_modes, write_report

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / "wallets" / "slim-6card-design"
needs_ccx = pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")


def _copy(tmp_path, mutate=None):
    d = yaml.safe_load((FIRST / "wallet.yaml").read_text())
    if mutate:
        mutate(d)
    out = tmp_path / "w"
    out.mkdir()
    (out / "wallet.yaml").write_text(yaml.safe_dump(d))
    return out


def test_first_wallet_loads_and_says_it_is_a_design_with_nothing_measured():
    rec = load_wallet(FIRST)
    assert rec.id == "slim-6card-design" and rec.status == "design"
    counts = rec.provenance_counts()
    assert counts["measured"] == 0 and counts["design"] >= 3 and set(counts) == set(PROVENANCE)
    assert len(rec.not_measured()) == len(rec.inputs)                     # nothing measured yet, and the report must say so
    assert rec.wallet_type == "bifold" and rec.shell_t == pytest.approx(1.0) and rec.slot_t == pytest.approx(0.7)


def test_stack_at_the_spine_is_cards_plus_interior_leather():
    rec = load_wallet(FIRST)
    assert rec.stack_at_spine_mm == pytest.approx(6 * 0.76 + 9 * 0.7)         # 10.86 mm
    assert rec.contents().thickness_mm == pytest.approx(10.86)
    assert rec.plan().folds[0].stack_mm == pytest.approx(10.86)


def test_a_measured_closed_thickness_overrides_the_derivation_and_subtracts_two_shells(tmp_path):
    def m(d):
        d["construction"]["closed_thickness_mm"] = {"value": 11.0, "source": "measured"}
    rec = load_wallet(_copy(tmp_path, m))
    assert rec.stack_at_spine_mm == pytest.approx(11.0 - 2 * 1.0)
    assert rec.stack_source == "measured"
    assert any(i.source == "measured" for i in rec.inputs)


def test_a_recorded_stack_wins_over_everything(tmp_path):
    def m(d):
        d["construction"]["stack_at_spine_mm"] = {"value": 7.5, "source": "measured"}
    rec = load_wallet(_copy(tmp_path, m))
    assert rec.stack_at_spine_mm == pytest.approx(7.5) and rec.plan().folds[0].stack_mm == pytest.approx(7.5)


def test_numbers_without_provenance_or_with_an_unknown_one_are_rejected_with_every_problem_listed(tmp_path):
    def m(d):
        d["leather"][0]["thickness_mm"] = 1.0                                   # no source
        d["contents"]["cards"]["source"] = "guessed"                            # not a known source
        d["construction"]["type"] = "pentafold"
    with pytest.raises(RecordError) as e:
        load_wallet(_copy(tmp_path, m))
    msg = str(e.value)
    assert "thickness_mm needs" in msg and "unknown source 'guessed'" in msg and "pentafold" in msg


def test_a_missing_shell_or_file_is_an_error_not_a_default(tmp_path):
    with pytest.raises(RecordError):
        load_wallet(tmp_path / "nowhere")
    with pytest.raises(RecordError) as e:
        load_wallet(_copy(tmp_path, lambda d: d["leather"].pop(0)))
    assert "shell" in str(e.value)


def test_the_failure_mode_names_match_docs_failure_modes_md():
    rows = {int(m.group(1)): m.group(0) for m in re.finditer(r"^\| (\d+) \|.*$", (ROOT / "docs" / "FAILURE_MODES.md").read_text(), re.M)}
    from types import SimpleNamespace
    rec = load_wallet(FIRST)
    # a stub report is enough: only the names and the record-driven statuses matter here
    out = SimpleNamespace(error="", fold=SimpleNamespace(name="spine"), taut=None, loose=None, closed_form=None, radius_mm=5.4,
                          tension=lambda w="taut": None, grain=lambda w="taut": None)
    base = SimpleNamespace(outcomes=[out], worst=None)
    modes = failure_modes(SimpleNamespace(rec=rec, base=base))
    assert [m["id"] for m in modes] == list(range(1, 15))
    for m in modes:
        assert m["name"].lower() in rows[m["id"]].lower(), (m["id"], m["name"])
    status = {m["id"]: m["status"] for m in modes}
    assert status[4] == status[8] == "flagged"                                   # the stitch line crosses the spine fold
    assert status[5] == "not triggered" and status[6] == "unknown"               # not skived; edge treatment not recorded
    assert status[2] == status[3] == status[13] == "not modelled"


@pytest.mark.fem
@needs_ccx
def test_report_on_the_first_wallet_matches_the_closed_form_and_writes_what_it_says_it_writes(tmp_path):
    rec = load_wallet(FIRST)
    rep = build_report(rec, sensitivity=False)
    o = rep.base.outcomes[0]
    limit = outer_fibre_strain(1.0, 10.86 / 2)                                   # 8.4 %
    assert o.closed_form == pytest.approx(limit, rel=0.03)
    assert limit * 0.9 < o.tension("loose") < limit * 1.15 and o.tension("taut") < 0.11
    out = write_report(rep, tmp_path / "run")
    for name in ("report.md", "result.json", "inputs.yaml", "fold1_shape.png", "fold1_strain.png"):
        assert (out / name).exists() and (out / name).stat().st_size > 100
    res = json.loads((out / "result.json").read_text())
    assert res["id"] == rec.id and res["status"] == "design" and len(res["failure_modes"]) == 14
    md = (out / "report.md").read_text()
    assert "This record is a design, not a measured wallet" in md and "What to measure first" in md
    assert yaml.safe_load((out / "inputs.yaml").read_text())["id"] == rec.id    # the exact input is stored with the result
