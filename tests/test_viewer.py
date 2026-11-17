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


def test_a_flap_record_without_a_gusset_gets_one_model_and_says_which_folds_it_leaves_out(tmp_path):
    whalet = tmp_path / "w"                                                                 # the record alone: without its assembly.yaml the viewer falls back to the flap sketch
    shutil.copytree(ROOT / "wallets" / "sr-whalet-sr202-2022", whalet, ignore=shutil.ignore_patterns("sim", "assembly.yaml", "viewer.html"))
    cfg = _cfg(build_viewer(whalet))
    assert [m["kind"] for m in cfg["models"]] == ["flap"]                                  # only a fold marked or named as a gusset gets the gusset model
    p = cfg["models"][0]["params"][0]
    assert (p["min"], p["value"], p["max"]) == (4.0, 8.0, 8.0)
    html = build_viewer(whalet)
    assert "left end fold" in html and "not drawn" in html and "photograph 01" not in html     # nothing borrowed from another wallet's record


# ---- the functional twin (the geometry library runs in node; skipped where node is not installed)
import subprocess

import pytest

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _twin_build(params: dict, flap: float = 0.0) -> dict:
    from walletsim.viewer import config
    whalet = ROOT / "wallets" / "sr-whalet-sr202-2022"
    _, cfg, _ = config(whalet)
    js = (ROOT / "src" / "walletsim" / "geometry.js").read_text()
    prog = js + f"""
    var CFG = {json.dumps(cfg)}, m = CFG.models[0], p = {{}};
    m.params.forEach(function (q) {{ p[q.id] = q.value; }}); Object.assign(p, {json.dumps(params)});
    var r = WalletGeometry.build(CFG, m, CFG.size, p, {{flap: {flap}}});
    console.log(JSON.stringify({{twin: r.twin, plates: r.plates.length, boxes: r.boxes.length, text: r.text}}));
    """
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@needs_node
def test_an_empty_twin_is_six_layers_and_the_closed_depth_follows_the_sheet_thickness():
    r = _twin_build({})
    assert r["plates"] == 6 and r["boxes"] == 0                                   # back panel, flap and four walls
    assert r["twin"]["depth"] == pytest.approx(6 * 1.0 + 4 * 0.2 + 0.3)           # 6 layers x t + 4 empty gaps + the flap clearance
    assert _twin_build({"t": 1.5})["twin"]["depth"] == pytest.approx(6 * 1.5 + 4 * 0.2 + 0.3)
    assert r["twin"]["fitT"] == pytest.approx((10 - 4 * 0.2 - 0.3) / 6)           # the thickness that reproduces the maker's 10 mm when empty


@needs_node
def test_cards_open_their_pocket_and_the_hinge_radius_follows_the_stack():
    empty, loaded = _twin_build({}), _twin_build({"n_front_pocket": 4})
    added = 4 * 0.76 + 0.3 - 0.2                                                  # the cards plus the stretch allowance, less the empty gap they replace
    assert loaded["twin"]["depth"] - empty["twin"]["depth"] == pytest.approx(added)
    assert loaded["twin"]["rIn"] == pytest.approx(loaded["twin"]["stack"] / 2) and loaded["boxes"] == 4
    assert "holds 7 cards" in _twin_build({"n_front_pocket": 7})["text"]           # beyond the maker's 4-5 per slot is flagged, not refused


def test_the_twin_is_the_default_viewer_when_a_wallet_has_an_assembly_file():
    cfg = _cfg(build_viewer(ROOT / "wallets" / "sr-whalet-sr202-2022"))
    assert [m["kind"] for m in cfg["models"]] == ["twin"] and cfg["twin"]["closedDepth"] == 10.0
    assert [p["id"] for p in cfg["models"][0]["params"]][:2] == ["t", "n_back_pocket"]
