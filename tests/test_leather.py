"""Hide classes, leather cards and their coverage, the strip test, and the refusal to simulate plated hides."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from walletsim.leather_cards import CardError, coverage, load_card, load_cards
from walletsim.materials import bending_modulus_mpa, fit_thickness_exponent, flexural_rigidity_n_m
from walletsim.record import load_wallet
from walletsim.report import NotApplicable, build_report
from walletsim.species import classify

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("text,group,cls", [
    ("bovine (calf)", "bovine", "sheet"), ("horse (equine)", "equine", "sheet"), ("porcine (pig)", "porcine", "sheet"), ("Nile perch", "fish", "sheet"),
    ("merino lamb", "ovine", "sheet"), ("goat", "caprine", "sheet"), ("alligator", "crocodilian", "composite"), ("python", "reptile-snake", "composite"),
    ("stingray", "stingray", "composite"), ("ostrich", "ostrich", "caution"), ("unknown", None, "unknown"), (None, None, "unknown"), ("a mystery hide", None, "unknown"),
])
def test_species_text_maps_to_one_hide_group_and_class(text, group, cls):
    c = classify(text)
    assert (c.group, c.hide_class) == (group, cls)


def test_bovine_is_not_mistaken_for_ovine():
    assert classify("bovine").group == "bovine" and classify("ovine").group == "ovine"          # 'bovine' contains the letters 'ovin'


def test_the_shipped_cards_load_with_a_source_on_every_value():
    cards = load_cards(ROOT / "cards")
    assert {c.id for c in cards} == {"calfskin-upper-mihai2022", "nile-tilapia-oliveira2022", "rabbit-oliveira2022"}
    calf = next(c for c in cards if c.group == "bovine")
    assert calf.props["youngs_modulus_mpa"]["value"] == 72 and calf.props["youngs_modulus_mpa"]["cv"] == 0.29
    fish = next(c for c in cards if c.group == "fish")
    assert fish.props["elongation_at_break_pct"]["value"] == pytest.approx(78.97) and any("Nile PERCH" in x for x in fish.not_this)   # tilapia is not perch


def test_a_card_value_without_a_source_or_a_reference_is_refused(tmp_path):
    d = yaml.safe_load((ROOT / "cards" / "calfskin-upper-mihai2022.yaml").read_text())
    d["thickness_mm"]["ref"] = ""
    (tmp_path / "c.yaml").write_text(yaml.safe_dump(d))
    with pytest.raises(CardError) as e:
        load_card(tmp_path / "c.yaml")
    assert "ref" in str(e.value)
    d["thickness_mm"].update(ref="x", source="invented")
    (tmp_path / "c.yaml").write_text(yaml.safe_dump(d))
    with pytest.raises(CardError):
        load_card(tmp_path / "c.yaml")


def test_coverage_counts_only_what_a_card_holds_and_marks_one_direction_tests():
    cov = coverage(load_cards(ROOT / "cards"))
    rows = {r["group"]: r for r in cov["rows"]}
    assert rows["bovine"]["cells"]["youngs_modulus_mpa"]["cards"] == ["calfskin-upper-mihai2022"] and rows["bovine"]["cells"]["bending_modulus_mpa"]["cards"] == []
    assert rows["fish"]["cells"]["tear_strength_n_mm"]["cards"] == ["nile-tilapia-oliveira2022"]
    assert rows["fish"]["cells"]["direction"]["partial"] == ["nile-tilapia-oliveira2022"]      # tested longitudinally only: no ratio
    assert rows["porcine"]["n_cards"] == 0 and all(not c["cards"] for c in rows["porcine"]["cells"].values())
    assert (cov["sheet_cells_filled"], cov["sheet_cells_total"]) == (10, 90)
    assert rows["crocodilian"]["hide_class"] == "composite"


def test_cantilever_strip_gives_the_flexural_rigidity_and_bending_modulus():
    B = flexural_rigidity_n_m(60, 1.0)                                       # L = 60 mm -> c = 30 mm; m = 1 kg/m2
    assert B == pytest.approx(1.0 * 9.80665 * 0.03 ** 3)
    assert bending_modulus_mpa(B, 1.0) == pytest.approx(12 * B / 1e-9 / 1e6)
    with pytest.raises(ValueError):
        flexural_rigidity_n_m(0, 1.0)


def test_thickness_exponent_recovers_three_for_a_plate_and_refuses_a_narrow_range():
    t = [0.8, 1.0, 1.4, 2.0]
    n, r2 = fit_thickness_exponent(t, [2e-4 * x ** 3 for x in t])
    assert n == pytest.approx(3.0) and r2 == pytest.approx(1.0)
    n2, _ = fit_thickness_exponent(t, [2e-4 * x ** 2 for x in t])
    assert n2 == pytest.approx(2.0)
    with pytest.raises(ValueError):
        fit_thickness_exponent([1.0, 1.05, 1.1], [1, 1.1, 1.2])
    with pytest.raises(ValueError):
        fit_thickness_exponent([1.0, 2.0], [1, 8])


def _alligator_copy(tmp_path):
    w = tmp_path / "w"
    shutil.copytree(ROOT / "wallets" / "ma-one-piece-wallet", w, ignore=shutil.ignore_patterns("sim", "viewer.html"))
    d = yaml.safe_load((w / "wallet.yaml").read_text())
    next(l for l in d["leather"] if l["id"] == "shell")["species"]["value"] = "alligator"
    (w / "wallet.yaml").write_text(yaml.safe_dump(d))
    return w


def test_a_plated_hide_is_refused_by_the_report_and_the_command(tmp_path):
    w = _alligator_copy(tmp_path)
    with pytest.raises(NotApplicable) as e:
        build_report(load_wallet(w), sensitivity=False)
    assert "composite" in str(e.value) and "not run" in str(e.value)
    proc = subprocess.run([sys.executable, "-m", "walletsim.cli", "wallet-report", str(w)], capture_output=True, text=True)
    assert proc.returncode == 3 and "not applicable" in proc.stderr and not (w / "sim").exists()   # no report, no figures
