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
    out = SimpleNamespace(error="", note="", bridges=False, fold=SimpleNamespace(name="spine"), taut=None, loose=None, closed_form=None, radius_mm=5.4,
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


# ---- the M.A+ One Piece record (a custom wallet listing its own folds) -----------------------------------------------

MA = ROOT / "wallets" / "ma-one-piece-wallet"


def test_ma_record_is_photos_only_with_nothing_measured_and_lists_its_folds():
    rec = load_wallet(MA)
    assert rec.status == "photos-only" and rec.wallet_type == "custom"
    assert rec.provenance_counts()["measured"] == 0
    assert [f.name.split(" ")[0] + " " + f.sense for f in rec.custom_folds] == ["spine out", "loop out", "left in", "loop out"]
    plan = rec.plan()
    assert [f.sense for f in plan.folds] == ["out", "out", "in", "out"] and plan.closed_thickness_mm != plan.closed_thickness_mm   # NaN: not recorded
    assert rec.stack_at_spine_mm == pytest.approx(7.0)                       # the 'spine' fold's stack, derived from the loops
    assert rec.custom_folds[0].low_mm == pytest.approx(5.0) and rec.custom_folds[0].high_mm == pytest.approx(19.0)


def test_a_custom_record_must_list_its_folds_with_valid_senses_and_ranges(tmp_path):
    def none(d):
        d["construction"].pop("folds_modelled")
    with pytest.raises(RecordError) as e:
        load_wallet(_copy_ma(tmp_path / "a", none))
    assert "folds_modelled" in str(e.value)

    def bad(d):
        d["construction"]["folds_modelled"][0]["sense"] = "sideways"
        d["construction"]["folds_modelled"][1]["stack_mm"]["low"] = 5.0         # low above the value
    with pytest.raises(RecordError) as e:
        load_wallet(_copy_ma(tmp_path / "b", bad))
    assert "sense must be out or in" in str(e.value) and "low <= value <= high" in str(e.value)


def _copy_ma(dest, mutate):
    d = yaml.safe_load((MA / "wallet.yaml").read_text())
    mutate(d)
    dest.mkdir(parents=True)
    (dest / "wallet.yaml").write_text(yaml.safe_dump(d))
    return dest


@pytest.mark.fem
@needs_ccx
def test_ma_report_ranks_the_tight_loops_by_the_closed_form_because_the_elastic_model_bridges_them(tmp_path):
    rep = build_report(load_wallet(MA), sensitivity=False)
    spine, loop1, left, loop2 = rep.base.outcomes
    assert spine.tension("taut") is not None and not spine.bridges
    assert loop1.bridges and left.bridges and loop2.bridges                   # R/t = 0.5: the leather stands off the stack by more than the radius
    assert loop1.screen_strain == pytest.approx(loop1.closed_form) == pytest.approx(0.5, abs=1e-6)
    assert rep.base.worst.fold.name != "spine"                                  # a tight hairpin, not the spine, is the worst fold
    status = {m["id"]: m["status"] for m in rep.modes}
    assert status[4] == "flagged" and status[5] == "unknown" and status[2] == "not modelled"
    out = write_report(rep, tmp_path / "r")
    md = (out / "report.md").read_text()
    assert "retailer's text and product photographs" in md and "bridges" in md and "no pockets recorded" in md
    assert all((out / f"fold{k}_shape.png").exists() for k in (1, 2, 3, 4))


def test_json_sweep_rows_keep_the_name_of_the_fold_they_belong_to():
    """Regression: a dict merge once overwrote each sweep row's fold name with the variant name ('spine @ high')."""
    from types import SimpleNamespace
    from walletsim.report import _json
    from walletsim.wallet_types import Fold, FoldOutcome
    o = FoldOutcome(Fold("spine @ high", 9.1, "out"), 4.55, 0.0, None, None, 0.099, note="stub")
    rep = SimpleNamespace(rec=SimpleNamespace(id="x", status="photos-only", inputs=[], stack_at_spine_mm=3.0), base=SimpleNamespace(outcomes=[o]),
                          scenarios=[], sweeps=[{"fold": "spine", "label": "high", "stack_mm": 9.1, "outcome": o}], meta={}, modes=[],
                          elasticity_stack=0.0, elasticity_thickness=0.0)
    row = _json(rep)["sweeps"][0]
    assert row["fold"] == "spine" and row["end"] == "high" and row["stack_mm"] == 9.1


def test_the_spine_stack_is_derived_from_the_loop_gap_and_follows_its_range(tmp_path):
    rec = load_wallet(MA)
    spine, loop1 = rec.custom_folds[0], rec.custom_folds[1]
    n, t = 3, rec.shell_t
    assert spine.stack_mm == pytest.approx(n * t + (n + 1) * loop1.stack_mm)          # 3 x 1.0 + 4 x 1.0
    assert spine.low_mm == pytest.approx(n * t + (n + 1) * loop1.low_mm)              # 5.0
    assert spine.high_mm == pytest.approx(n * t + (n + 1) * loop1.high_mm)            # 19.0
    assert spine.source == "assumed" and "derived" in spine.ref                       # it inherits the loop's weakest provenance
    assert any(i.name == "inner leaves" and i.source == "inferred" for i in rec.inputs)

    def wider_loops(d):
        for f in d["construction"]["folds_modelled"][1:]:
            f["stack_mm"].update(value=2.0, low=1.0, high=5.0)
    rec2 = load_wallet(_copy_ma(tmp_path / "w", wider_loops))
    assert rec2.stack_at_spine_mm == pytest.approx(3 * 1.0 + 4 * 2.0)                 # the spine moves when the loops do


def test_a_derived_spine_must_name_a_loop_that_exists(tmp_path):
    def broken(d):
        d["construction"]["folds_modelled"][0]["stack_from_loops"]["gap_from"] = "no such fold"
    with pytest.raises(RecordError) as e:
        load_wallet(_copy_ma(tmp_path / "x", broken))
    assert "gap_from" in str(e.value)


# ---- the one-piece double wallet (map02) and the origami known by its closed thickness (map04)
MA2 = ROOT / "wallets" / "ma-one-piece-double-wallet"
ORIGAMI = ROOT / "wallets" / "ma-mavr-origami-wallet"


def _copy_from(src, dest, mutate):
    d = yaml.safe_load((src / "wallet.yaml").read_text())
    mutate(d)
    dest.mkdir(parents=True)
    (dest / "wallet.yaml").write_text(yaml.safe_dump(d))
    return dest


def test_the_double_wallet_has_four_leaves_five_folds_and_alternating_grain():
    rec = load_wallet(MA2)
    assert rec.status == "photos-only" and rec.provenance_counts()["measured"] == 0
    assert [f.sense for f in rec.custom_folds] == ["out", "out", "in", "out", "in"]
    spine, loop1 = rec.custom_folds[0], rec.custom_folds[1]
    assert spine.stack_mm == pytest.approx(4 * rec.shell_t + 5 * loop1.stack_mm)      # 4 x 1.0 + 5 x 1.0
    assert spine.low_mm == pytest.approx(6.5) and spine.high_mm == pytest.approx(24.0)
    assert load_wallet(MA).stack_at_spine_mm < rec.stack_at_spine_mm                  # one more leaf, more stack at the spine


def test_a_stack_derived_from_the_closed_thickness_is_inferred_and_subtracts_the_shells():
    rec = load_wallet(ORIGAMI)
    main = rec.custom_folds[0]
    assert main.stack_mm == pytest.approx(18.0 - 2 * 1.0)
    assert main.low_mm == pytest.approx(10.0) and main.high_mm == pytest.approx(16.0)  # the upper bound is the closed pack itself
    assert main.source == "inferred" and "derived" in main.ref                          # derived from a reported number, never itself 'reported'
    assert any(i.source == "reported" and "closed thickness" in i.name for i in rec.inputs)


def test_a_closed_thickness_derivation_needs_a_closed_thickness(tmp_path):
    def drop(d):
        d["construction"].pop("closed_thickness_mm")
    with pytest.raises(RecordError) as e:
        load_wallet(_copy_from(ORIGAMI, tmp_path / "w", drop))
    assert "closed_thickness_mm" in str(e.value)


def test_reported_is_a_provenance_and_is_not_counted_as_measured():
    assert "reported" in PROVENANCE
    assert load_wallet(ORIGAMI).provenance_counts()["reported"] >= 3
    assert load_wallet(ORIGAMI).provenance_counts()["measured"] == 0


def test_unknown_seams_make_the_stitch_modes_unknown_not_not_triggered():
    from types import SimpleNamespace
    rec = load_wallet(ORIGAMI)
    assert rec.seams[0]["crosses_fold"] == "unknown"
    out = SimpleNamespace(error="", note="", bridges=False, fold=SimpleNamespace(name="main fold"), taut=None, loose=None, closed_form=None, radius_mm=8.0,
                          tension=lambda w="taut": None, grain=lambda w="taut": None)
    modes = {m["id"]: m for m in failure_modes(SimpleNamespace(rec=rec, base=SimpleNamespace(outcomes=[out], worst=None)))}
    assert modes[4]["status"] == "unknown" and "not recorded" in modes[4]["text"]
    assert modes[8]["status"] == "unknown"


def test_each_kind_of_record_gets_its_own_measurement_list():
    from walletsim.record import MEASURE_FIRST, MEASURE_FIRST_CUSTOM, MEASURE_FIRST_POCKETED, measure_first
    assert measure_first(load_wallet(FIRST)) is MEASURE_FIRST
    assert measure_first(load_wallet(MA)) is MEASURE_FIRST_CUSTOM and measure_first(load_wallet(MA2)) is MEASURE_FIRST_CUSTOM
    pocketed = measure_first(load_wallet(ORIGAMI))
    assert pocketed is MEASURE_FIRST_POCKETED and not any("loop" in a.lower() for a, _ in pocketed)   # no loops in this wallet


@pytest.mark.fem
@needs_ccx
def test_a_wallet_page_is_one_self_contained_file_with_every_fold_and_its_banner(tmp_path):
    from walletsim.page import build_page, write_page
    wdir = tmp_path / "wallet"
    shutil.copytree(ORIGAMI, wdir, ignore=shutil.ignore_patterns("sim"))              # the page reads the record two folders above the run
    run = write_report(build_report(load_wallet(wdir), sensitivity=False), wdir / "sim" / "run-test")
    html = build_page(run)
    assert html.count("<script src") == 0 and "http://" not in html.replace("http://www.w3.org", "")   # nothing is fetched except the web font
    assert "Main fold" in html and "Bill-pocket" in html and "Nothing is measured here" in html
    assert "It has been used." in html and "..</p>" not in html                                      # the usage sentence ends once
    out = write_page(run_dir=run)
    assert Path(out).read_text() == html


WHALET = ROOT / "wallets" / "sr-whalet-sr202-2022"


def test_the_whalet_derives_both_end_folds_from_the_makers_depth_and_marks_them_assumed():
    rec = load_wallet(WHALET)
    assert rec.status == "photos-only" and rec.provenance_counts()["measured"] == 0
    assert [f.name.split(" ")[0] for f in rec.custom_folds] == ["flap", "left"]
    for f in rec.custom_folds:
        assert f.stack_mm == pytest.approx(10.0 - 2 * 1.0) and (f.low_mm, f.high_mm) == (4.0, 8.0)
        assert f.source == "assumed"                       # the maker's 10 mm is reported, but the sheet it subtracts is an assumption
    assert rec.raw["archive"]["year"] == 2022 and "2010" in rec.raw["archive"]["year_note"]
