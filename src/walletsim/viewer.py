"""A 3D structural sketch of a wallet record's folds: one strip of leather, folded the way the record says, that opens and closes.

It is a **kinematic sketch**, not a simulation: each fold turns through a fixed length of sheet (so a fold that opens gets a larger radius), panels can pass through
each other, and the colour is the closed-form strain at each fold scaled with the fold angle. What it draws comes from the record:

* a record with ``stack_from_loops`` (a one-sheet accordion: spine, then tight hairpins with a leaf after each) gives the **chain** model; the number of leaves, the
  loop gap and its range, the sizes and the sheet thickness are read from the record;
* a record with ``stack_from_closed_thickness`` (a wallet known by its closed depth) gives the **flap** model (the main fold as a hinge over a block standing for the pack it
  wraps) and the **gusset** model (one side pleat of the bill pocket, seen across the width). The pleat's size is a drawn guess and says so.

The page loads Three.js from a CDN, so it needs a connection; the geometry lives in ``viewer_template.html``.
"""
from __future__ import annotations

import html
import json
import re
from importlib import resources
from pathlib import Path

from .record import CUSTOM, WalletRecord, load_wallet

E = html.escape
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
# Drawn guesses for the bill-pocket gusset: no photograph has a scale. They set only how big the pleat looks, never a strain.
GUSSET_GUESS = {"w": 60.0, "a": 18.0, "depth": 70.0, "maxPhi": 100.0}


class ViewerError(ValueError):
    pass


def _short(name: str) -> str:
    return name.split(" (")[0].strip().capitalize()


def _sizes(rec: WalletRecord) -> dict:
    """Closed footprint [cm] -> strip length L (the shorter side, along the sheet) and width W (the longer side), in mm."""
    out = {}
    for key, s in (rec.raw.get("sizes") or {}).items():
        fp = s.get("closed_footprint_cm")
        if not fp:
            continue
        w, l = float(fp[0]), float(fp[1])
        out[str(key)] = {"L": round(l * 10), "W": round(w * 10), "txt": f"{w:g} x {l:g} cm"}
    if not out:
        raise ViewerError("the record has no sizes with closed_footprint_cm; the viewer needs the closed footprint")
    return out


def _tags(k: int, sense: str) -> str:
    """Where fold k's label sits relative to the fold (k = 0 is the spine), so that neighbouring labels do not cover each other."""
    if k == 0:
        return "translate(-108%, -50%)"
    j = (k - 1) // 2                                        # which loop (or left fold) this is: 0 for the first, 1 for the second
    if sense == "out":                                      # the loops, at the right-hand end: first above, then below
        return "translate(10px, -120%)" if j % 2 == 0 else "translate(10px, 10%)"
    return f"translate(-50%, {120 + 125 * j}%)"             # the left folds, below the spine end, stepping down


def _specs(rec: WalletRecord) -> list[dict]:
    return (rec.raw.get("construction") or {}).get("folds_modelled") or []


def _item(rec: WalletRecord) -> str:
    for v in (rec.raw.get("photos") or {}).values():
        m = re.search(r"items/([^/]+)/", str(v))
        if m:
            return m.group(1)
    return ""


def _chain(rec: WalletRecord) -> dict:
    spec = next(s for s in _specs(rec) if "stack_from_loops" in s)
    n = int(round(float(spec["stack_from_loops"]["leaves"]["value"])))
    folds = rec.custom_folds
    if len(folds) != n + 1:
        raise ViewerError(f"a chain of {n} leaves has {n + 1} folds (the spine and {n} hairpins); the record lists {len(folds)}")
    senses = [f.sense for f in folds]
    want = ["out"] + ["out" if k % 2 == 0 else "in" for k in range(n)]
    if senses != want:
        raise ViewerError(f"the one-sheet accordion turns {want} (spine, then loops out and left folds in, alternating); the record has {senses}")
    loop = folds[1]
    lo, hi = (loop.low_mm, loop.high_mm) if loop.low_mm is not None else (loop.stack_mm, loop.stack_mm)
    hinges = []
    for k, f in enumerate(folds):
        sgn = -1 if f.sense == "out" else 1
        hinges.append({"id": "spine" if k == 0 else f"h{k}", "name": _short(f.name), "closed": 180 * sgn, "open": (15 if k == 0 else 135) * sgn,
                       "drv": "book" if k == 0 else "pockets", "tag": _tags(k, f.sense)})
    model = {"id": "chain", "kind": "chain", "label": "Wallet",
             "controls": [{"id": "book", "label": "Open the wallet"}, {"id": "pockets", "label": "Open the pockets"}],
             "params": [{"id": "rIn", "label": "Hairpin radius, inside", "min": lo / 2, "max": hi / 2, "step": 0.05, "value": loop.stack_mm / 2, "unit": "mm", "dec": 2}],
             "hinges": hinges}
    sizes = _sizes(rec)
    cfg = {"T": float(rec.shell_t), "leaves": n, "models": [model], "sizes": sizes, "size": next(iter(sizes)),
           "edgeLabel": "Edge-on, like the photo", "words": WORDS}
    seq = ["bottom panel", "spine", "top panel"] + [x for k in range(n) for x in (hinges[k + 1]["name"].lower(), f"leaf {chr(65 + k)}")]
    spine = folds[0]
    lw = WORDS.get(n, str(n))
    text = {
        "eyebrow": f"{E(str(rec.raw.get('maker', '')))} &middot; fold structure",
        "banner": (f"<strong>A structural sketch, not a scan.</strong> The photographs show a spine wrapping {lw} inner leaves and {lw} tight hairpin folds, but not the flat cut "
                   f"pattern. This folds one {rec.shell_t:g} mm strip with that structure, widened to the wallet's width. It has no pockets, flap or silver cross, panels can pass "
                   "through each other, and nothing here is a leather simulation."),
        "shows": [f"One strip: {', '.join(seq)}. That gives {lw} inner leaves and {lw} tight hairpins, as in the edge-on photographs.",
                  "Each fold turns through a fixed length of sheet, so a fold that opens gets a larger radius.",
                  "The layers sit one gap apart, so the hairpin radius also sets the stack the spine wraps."],
        "real": ["The flat pattern, or photographs of the wallet unfolded flat.", "A measured closed thickness and each hairpin's radius.",
                 f"The report derives the spine from the hairpins in the same way: {spine.stack_mm:g} mm at the recorded radius, and "
                 f"{spine.low_mm:g} to {spine.high_mm:g} mm across the range it allows."],
    }
    return {"cfg": cfg, "text": text, "n": n}


def _flap(rec: WalletRecord) -> dict:
    folds = rec.custom_folds
    main = folds[0]
    cl = (rec.raw.get("construction") or {}).get("closed_thickness_mm") or {}
    lo, hi = (main.low_mm, main.high_mm) if main.low_mm is not None else (main.stack_mm, main.stack_mm)
    sizes = _sizes(rec)
    hinge = {"id": "main", "name": _short(main.name), "closed": -180, "open": -20, "drv": "flap", "tag": "translate(-108%, -50%)"}
    m1 = {"id": "flap", "kind": "flap", "label": "Flap and spine", "controls": [{"id": "flap", "label": "Open the flap"}],
          "params": [{"id": "stack", "label": "Stack the hinge wraps", "min": lo, "max": hi, "step": 0.5, "value": main.stack_mm, "unit": "mm", "dec": 1}], "hinges": [hinge]}
    models = [m1]
    gus = next((f for f in folds[1:]), None)
    if gus is not None:
        glo, ghi = (gus.low_mm, gus.high_mm) if gus.low_mm is not None else (gus.stack_mm, gus.stack_mm)
        models.append({"id": "gusset", "kind": "gusset", "label": "Bill-pocket gusset", "controls": [{"id": "gusset", "label": "Open the bill pocket"}],
                       "params": [{"id": "rIn", "label": "Crease radius, inside", "min": glo / 2, "max": ghi / 2, "step": 0.05, "value": gus.stack_mm / 2, "unit": "mm", "dec": 2}],
                       "hinges": [{"id": "crease", "name": "Crease (the one in the report)", "closed": 0, "open": 0, "drv": "gusset", "tag": "translate(16px, -50%)"},
                                  {"id": "edgeF", "name": "Front edge", "closed": 0, "open": 0, "drv": "gusset", "tag": "translate(-105%, -140%)"},
                                  {"id": "edgeB", "name": "Back edge", "closed": 0, "open": 0, "drv": "gusset", "tag": "translate(-105%, 120%)"}]})
    cfg = {"T": float(rec.shell_t), "leaves": 0, "models": models, "sizes": sizes, "size": next(iter(sizes)), "edgeLabel": "Side view", "words": WORDS,
           "gusset": GUSSET_GUESS}
    depth = cl.get("value")
    depth_txt = f"{float(depth):g} mm" if depth else "an unrecorded depth"
    text = {
        "eyebrow": f"{E(str(rec.raw.get('maker', '')))} &middot; fold structure",
        "banner": (f"<strong>A structural sketch, not a scan.</strong> The only measurement behind it is the seller's closed depth, {depth_txt}, measured by hand laid flat. "
                   "I read the main fold as the flap's hinge from photographs 01 and 03; the pockets, card slits, cross and back crease are not drawn, and the grey block only stands for the pack "
                   "the hinge wraps. The size of the bill-pocket pleat is a drawn guess (no photograph has a scale). Panels can pass through each other and nothing here is a leather simulation."),
        "shows": ["<em>Flap and spine:</em> the sheet seen along its length: a back panel, the main fold, and the flap that lies over the front, with a block for the pack it wraps.",
                  "<em>Bill-pocket gusset:</em> one side pleat of the large pocket seen across its width, as opened by hand in photograph 03. The V closes flat when the pocket is empty.",
                  "Each fold turns through a fixed length of sheet, so a fold that opens gets a larger radius."],
        "real": ["Closed thickness at the spine edge-on with a ruler, and how much of it the main fold actually wraps.",
                 "One gusset crease photographed edge-on, empty and loaded, with a ruler: its radius is assumed here and sets the tightest fold.",
                 "The flat pattern, to say which fold the flap really is."],
    }
    return {"cfg": cfg, "text": text, "n": 0}


def config(wallet_dir: str | Path) -> tuple[WalletRecord, dict, dict]:
    """The record, the viewer's configuration (what the geometry library draws) and its page text, all read from the record."""
    rec = load_wallet(wallet_dir)
    if rec.wallet_type != CUSTOM:
        raise ViewerError("only custom (one-sheet) records have a 3D sketch so far; bifold, trifold and z-fold have the fold simulator's plots")
    specs = _specs(rec)
    if any("stack_from_loops" in s for s in specs):
        built = _chain(rec)
    elif any("stack_from_closed_thickness" in s for s in specs):
        built = _flap(rec)
    else:
        raise ViewerError("the record has neither stack_from_loops nor stack_from_closed_thickness, so there is no structure to draw")
    return rec, {**built["cfg"], "id": rec.id}, built["text"]


def build_viewer(wallet_dir: str | Path, embed: bool = False) -> str:
    """The standalone page. With embed=True the page hides its own title block and reports its height to the page that frames it (the archive app)."""
    rec, cfg, tx = config(wallet_dir)
    cfg = {**cfg, "embed": bool(embed)}
    sz = cfg["sizes"]
    item = _item(rec)
    foot = ("Source: retailer or reseller text and product photographs in the Wallet-corpus- archive"
            + (f" (item {item.split('_')[0]})" if item else "")
            + ". The photographs are research documentation only and are not shown here. Sizes "
            + ", ".join(f"{k}: {v['txt']}" for k, v in sz.items()) + " are read as the closed footprint. Strain is the closed form t / (2R + t), where t is the sheet thickness and R the inside radius.")
    tpl = resources.files("walletsim").joinpath("viewer_template.html").read_text(encoding="utf-8")
    geometry = resources.files("walletsim").joinpath("geometry.js").read_text(encoding="utf-8")
    cfg_json = json.dumps(cfg, separators=(",", ":")).replace("</", "<\\/")
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
    return (tpl.replace("{{TITLE}}", E(f"{rec.name} 3D")).replace("{{EYEBROW}}", tx["eyebrow"]).replace("{{H1}}", E(f"{rec.name} in 3D"))
               .replace("{{BANNER}}", tx["banner"]).replace("{{SHOWS}}", li(tx["shows"])).replace("{{REAL}}", li(tx["real"])).replace("{{FOOT}}", E(foot))
               .replace("{{GEOMETRY_JS}}", geometry).replace("__CFG__", cfg_json))


def write_viewer(wallet_dir: str | Path, out: str | Path | None = None) -> Path:
    path = Path(out) if out else Path(wallet_dir) / "viewer.html"
    path.write_text(build_viewer(wallet_dir), encoding="utf-8")
    return path
