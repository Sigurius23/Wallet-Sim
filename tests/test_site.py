"""The archive app: records in, one HTML file out. The data it embeds must say what the records say, and nothing more."""
import json
import re
import shutil
from pathlib import Path

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
