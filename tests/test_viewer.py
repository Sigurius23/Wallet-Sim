"""The 3D structural sketch: its configuration is read from the wallet record, so it cannot disagree with the report about leaves, radii or sizes."""
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from walletsim.record import load_wallet
from walletsim.viewer import ViewerError, build_viewer

ROOT = Path(__file__).resolve().parents[1]
MA, MA2, ORIGAMI, FIRST = (ROOT / "wallets" / w for w in ("ma-one-piece-wallet", "ma-one-piece-double-wallet", "ma-mavr-origami-wallet", "slim-6card-design"))


def _cfg(html: str) -> dict:
    return json.loads(re.search(r"var CFG = (\{.*\});\n", html).group(1))


@pytest.mark.parametrize("wallet,n", [(MA, 3), (MA2, 4)])
def test_a_chain_viewer_has_the_records_leaves_hairpins_and_sizes(wallet, n):
    rec = load_wallet(wallet)
    cfg = _cfg(build_viewer(wallet))
    m = cfg["models"][0]
    assert cfg["leaves"] == n and len(m["hinges"]) == n + 1                               # the spine and one hairpin per leaf
    signs = [1 if h["closed"] > 0 else -1 for h in m["hinges"]]
    assert signs == [-1] + [-1 if k % 2 == 0 else 1 for k in range(n)]                    # spine and loops grain out, left folds grain in
    assert [h["name"] for h in m["hinges"]][:2] == ["Spine", "Loop 1"]
    p = m["params"][0]
    loop = rec.custom_folds[1]
    assert (p["min"], p["value"], p["max"]) == (loop.low_mm / 2, loop.stack_mm / 2, loop.high_mm / 2)   # the slider spans the record's range for the loop gap
    assert cfg["T"] == rec.shell_t
    for key, s in rec.raw["sizes"].items():
        w, l = s["closed_footprint_cm"]
        assert cfg["sizes"][key]["W"] == round(w * 10) and cfg["sizes"][key]["L"] == round(l * 10)


@pytest.mark.parametrize("wallet", [MA, MA2])
def test_the_viewers_spine_formula_is_the_records_derived_stack(wallet):
    """The viewer's spine neutral radius is (leaves + 1) x (inside radius + t/2); the record derives leaves x t + (leaves + 1) x gap. They must agree."""
    rec = load_wallet(wallet)
    cfg = _cfg(build_viewer(wallet))
    n, t, rin = cfg["leaves"], cfg["T"], cfg["models"][0]["params"][0]["value"]
    assert 2 * (n + 1) * (rin + t / 2) - t == pytest.approx(rec.custom_folds[0].stack_mm)


def test_the_flap_viewer_reads_the_closed_depth_and_has_a_gusset_with_the_records_range():
    rec = load_wallet(ORIGAMI)
    cfg = _cfg(build_viewer(ORIGAMI))
    flap, gus = cfg["models"]
    p = flap["params"][0]
    assert (p["min"], p["value"], p["max"]) == (10.0, 16.0, 16.0)                          # the stack derived from the 18 mm depth, with its assumed lower bound
    assert gus["kind"] == "gusset" and (gus["params"][0]["min"], gus["params"][0]["max"]) == (0.25, 2.0)
    assert cfg["sizes"]["one size"]["L"] == 95 and cfg["sizes"]["one size"]["W"] == 145
    assert "18 mm" in build_viewer(ORIGAMI) and "drawn guess" in build_viewer(ORIGAMI)    # the page says what is invented


def test_the_page_has_no_unfilled_placeholders_and_names_its_source():
    for w in (MA, MA2, ORIGAMI):
        html = build_viewer(w)
        assert "{{" not in html and "__CFG__" not in html
        assert "Wallet-corpus-" in html and "not a scan" in html


def test_only_one_sheet_records_with_a_known_structure_get_a_viewer(tmp_path):
    with pytest.raises(ViewerError):
        build_viewer(FIRST)                                                                 # a bifold design: the fold simulator's plots are its picture

    d = yaml.safe_load((MA / "wallet.yaml").read_text())
    d["construction"]["folds_modelled"][2]["sense"] = "out"                                 # a left fold that turns the wrong way breaks the accordion
    out = tmp_path / "w"
    out.mkdir()
    (out / "wallet.yaml").write_text(yaml.safe_dump(d))
    with pytest.raises(ViewerError) as e:
        build_viewer(out)
    assert "alternating" in str(e.value)

    d = yaml.safe_load((MA / "wallet.yaml").read_text())
    d["construction"]["folds_modelled"].pop(3)
    out2 = tmp_path / "w2"
    out2.mkdir()
    (out2 / "wallet.yaml").write_text(yaml.safe_dump(d))
    with pytest.raises(ViewerError) as e:
        build_viewer(out2)
    assert "folds" in str(e.value)


def test_a_flap_record_without_a_gusset_gets_one_model_and_says_which_folds_it_leaves_out():
    whalet = ROOT / "wallets" / "sr-whalet-sr202-2022"
    cfg = _cfg(build_viewer(whalet))
    assert [m["kind"] for m in cfg["models"]] == ["flap"]                                  # only a fold marked or named as a gusset gets the gusset model
    p = cfg["models"][0]["params"][0]
    assert (p["min"], p["value"], p["max"]) == (4.0, 8.0, 8.0)
    html = build_viewer(whalet)
    assert "left end fold" in html and "not drawn" in html and "photograph 01" not in html     # nothing borrowed from another wallet's record
