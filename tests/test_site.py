"""The archive app: records in, one HTML file out. The data it embeds must say what the records say, and nothing more."""
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from walletsim.site import build_data, build_site, write_site

ROOT = Path(__file__).resolve().parents[1]
WALLETS = ROOT / "wallets"


def _data_from(html: str) -> dict:
    return json.loads(re.search(r"var DATA = (\{.*\});\n", html).group(1).replace("<\\/", "</"))


def test_generated_test_designs_are_not_archive_items_unless_asked():
    ids = [w["id"] for w in build_data(WALLETS)["wallets"]]
    assert ids == ["ma-mavr-origami-wallet", "ma-one-piece-double-wallet", "ma-one-piece-wallet", "sr-whalet-sr202-2022"]
    d = build_data(WALLETS)
    assert d["hidden_designs"] and "slim-6card-design" not in ids
    assert "slim-6card-design" in [w["id"] for w in build_data(WALLETS, include_designs=True)["wallets"]]


def test_undated_wallets_stay_undated_and_unknown_fields_stay_empty():
    for w in build_data(WALLETS)["wallets"]:
        facts = {f["label"]: f for f in w["facts"]}
        if w["id"].startswith("ma-"):
            assert w["year"] is None and facts["Year"]["value"] is None        # no M.A+ record has a design year, so none is invented
            assert facts["Sheet thickness"]["source"] == "reported"            # a retailer's figure is shown as reported, not measured
        assert facts["Hide region"]["value"] is None                           # no region is recorded for any of them
        assert (facts["Tanning"]["value"] is None) == (w["id"] not in ("ma-mavr-origami-wallet", "sr-whalet-sr202-2022"))   # only these listings state a tanning
        assert w["status"] == "photos-only" and w["counts"]["measured"] == 0
        assert w["hero"] is None                                               # photographs are research documentation only: none is embedded


def test_a_dated_wallet_gets_its_year_and_the_note_that_qualifies_it():
    w = next(w for w in build_data(WALLETS)["wallets"] if w["id"] == "sr-whalet-sr202-2022")
    year = next(f for f in w["facts"] if f["label"] == "Year")
    assert w["year"] == 2022 and year["value"] == "2022" and "2010" in year["ref"]          # the reissue year, with the original's year in the note
    sheet = next(f for f in w["facts"] if f["label"] == "Sheet thickness")
    assert sheet["source"] == "assumed"                                                     # the maker gives no sheet thickness
    assert next(f for f in w["facts"] if f["label"] == "Species")["value"] == "horse (equine)"


def test_the_origami_pipeline_shows_what_the_listing_states_and_marks_the_rest():
    w = next(w for w in build_data(WALLETS)["wallets"] if w["id"] == "ma-mavr-origami-wallet")
    steps = {s["window"]: s for s in w["pipeline"]}
    assert steps["tanning"]["value"] == "vegetable" and steps["tanning"]["source"] == "reported"
    assert steps["beamhouse"]["value"] is None and steps["post_tanning"]["value"] is None
    assert [s["n"] for s in w["pipeline"]] == [1, 2, 3, 4]


def test_each_wallet_carries_its_stored_report_and_a_3d_sketch():
    for w in build_data(WALLETS)["wallets"]:
        b = w["behaviour"]
        assert b["has_run"] and b["rows"] and len(b["modes"]) == 14 and "<svg" in b["chart"]
        assert w["viewer"] and "WalletGeometry" in w["viewer"]["html"] and w["viewer"]["cfg"]["models"]


def test_the_site_is_one_file_with_its_data_and_no_unfilled_placeholders(tmp_path):
    html = build_site(WALLETS)
    assert "__DATA__" not in html and "{{GEOMETRY_JS}}" not in html and "var WalletGeometry" in html
    data = _data_from(html)
    assert [w["id"] for w in data["wallets"]] == ["ma-mavr-origami-wallet", "ma-one-piece-double-wallet", "ma-one-piece-wallet", "sr-whalet-sr202-2022"]
    assert "data:image" not in html                                            # nothing from the corpus photographs
    out = write_site(WALLETS, tmp_path / "site" / "index.html")
    assert out.read_text(encoding="utf-8") == html


def test_a_hero_photograph_is_embedded_only_when_the_record_names_one(tmp_path):
    root = tmp_path / "wallets"
    shutil.copytree(WALLETS / "ma-one-piece-wallet", root / "w", ignore=shutil.ignore_patterns("sim", "viewer.html"))
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
    (root / "w" / "hero.png").write_bytes(png)
    d = yaml.safe_load((root / "w" / "wallet.yaml").read_text())
    d["archive"]["hero_image"] = "hero.png"
    (root / "w" / "wallet.yaml").write_text(yaml.safe_dump(d))
    w = build_data(root)["wallets"][0]
    assert w["hero"].startswith("data:image/png;base64,")
    assert w["behaviour"]["has_run"] is False                                  # no stored run in this copy: the app says so instead of showing numbers


# ---- the lab, the what-if and the animals
def test_the_cow_pig_horse_and_sheep_are_the_cc0_models_and_decode_to_whole_triangles():
    import base64
    a = build_data(WALLETS)["animals"]
    assert a["license"].startswith("CC0") and a["author"] == "Quaternius"
    assert set(a["models"]) == {"bovine", "porcine", "equine", "ovine"}                 # no goat: no free goat model was found
    for key, m in a["models"].items():
        floats = len(base64.b64decode(m["positions"])) // 4
        assert floats == 9 * m["triangles"] and m["triangles"] > 300
        x0, x1, y0, y1, z0, z1 = m["bbox"]
        assert x1 - x0 == pytest.approx(2.6) and y0 == pytest.approx(0.0)                # body length 2.6, feet on the ground


def test_each_wallet_carries_what_the_thickness_slider_needs_and_its_style_comparison():
    d = {w["id"]: w for w in build_data(WALLETS)["wallets"]}
    kinds = {i: [f["kind"] for f in w["swap"]["folds"]] for i, w in d.items()}
    assert kinds["ma-mavr-origami-wallet"] == ["closed", "fixed"] and kinds["ma-one-piece-wallet"][0] == "loops"
    assert d["ma-mavr-origami-wallet"]["swap"]["folds"][0]["depth"] == 18.0
    for w in d.values():
        s = w["styles"]
        assert s and len(s["rows"]) == 7 and {r["style"] for r in s["rows"]} >= {"plain", "skived", "hinged"}
        assert next(r for r in s["rows"] if r["style"] == "plain")["vs_plain_taut"] == pytest.approx(1.0)


def test_the_lab_stores_each_tools_command_and_verbatim_output():
    lab = build_data(WALLETS)["lab"]
    ids = [r["id"] for r in lab["results"]]
    assert ids == ["screen", "validate", "sweep", "styles", "gusset", "box", "edge", "types"]
    assert all(r["returncode"] == 0 and r["command"].startswith("walletsim ") and r["output"] for r in lab["results"])


def test_lab_run_stores_a_command_and_its_output(tmp_path):
    from walletsim.lab import run_lab
    out = run_lab(tmp_path / "lab.json", only=["screen"])
    r = json.loads(out.read_text())["results"][0]
    assert r["command"] == "walletsim screen --t 1.0 --radius 2.0" and "outer-fibre strain" in r["output"]


@pytest.mark.fem
@pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")
def test_wallet_styles_runs_the_comparison_at_the_wallets_own_radius(tmp_path):
    from walletsim.lab import wallet_styles
    w = tmp_path / "w"
    shutil.copytree(WALLETS / "sr-whalet-sr202-2022", w, ignore=shutil.ignore_patterns("sim", "viewer.html"))
    s = json.loads(wallet_styles(w).read_text())
    assert s["inside_radius_mm"] == pytest.approx(4.0) and [r["style"] for r in s["rows"]][:2] == ["plain", "skived"]
    plain = s["rows"][0]
    assert plain["wrap_taut"] == pytest.approx(0.118, abs=0.01) and plain["limit"] == pytest.approx(1 / 9, abs=0.002)   # matches the wallet report's 11.8 % and 11.1 %
