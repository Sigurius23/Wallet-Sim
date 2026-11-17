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

import yaml
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


def _is_gusset(spec: dict) -> bool:
    """A fold is drawn as a bill-pocket gusset when the record says so (geometry: gusset) or, if it says nothing, when its name does."""
    g = spec.get("geometry")
    return g == "gusset" or (g is None and "gusset" in str(spec.get("name", "")).lower())


def _flap(rec: WalletRecord) -> dict:
    specs = _specs(rec)
    folds = rec.custom_folds
    gus_k = next((k for k, sp in enumerate(specs) if k > 0 and _is_gusset(sp)), None)
    main = folds[0]
    cl = (rec.raw.get("construction") or {}).get("closed_thickness_mm") or {}
    lo, hi = (main.low_mm, main.high_mm) if main.low_mm is not None else (main.stack_mm, main.stack_mm)
    sizes = _sizes(rec)
    hinge = {"id": "main", "name": _short(main.name), "closed": -180, "open": -20, "drv": "flap", "tag": "translate(-108%, -50%)"}
    m1 = {"id": "flap", "kind": "flap", "label": "Flap and spine", "controls": [{"id": "flap", "label": "Open the flap"}],
          "params": [{"id": "stack", "label": "Stack the hinge wraps", "min": lo, "max": hi, "step": 0.5, "value": main.stack_mm, "unit": "mm", "dec": 1}], "hinges": [hinge]}
    models = [m1]
    gus = folds[gus_k] if gus_k is not None else None
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
    dsrc = cl.get("source", "")
    who = {"reported": "the maker's or seller's", "measured": "the measured", "inferred": "an inferred"}.get(dsrc, "the recorded")
    not_drawn = [_short(f.name).lower() for k, f in enumerate(folds) if k > 0 and k != gus_k]
    omitted = (f" The record's other fold{'s' if len(not_drawn) > 1 else ''} ({', '.join(not_drawn)}) {'are' if len(not_drawn) > 1 else 'is'} not drawn: the sketch shows one hinge." if not_drawn else "")
    banner = (f"<strong>A structural sketch, not a scan.</strong> The only measurement behind it is {who} closed depth, {depth_txt}"
              f"{'' if dsrc == 'measured' else ', not checked'}. The hinge is the record's first fold, {_short(main.name).lower()}; the pockets, card slots and fittings are not drawn, "
              "and the grey block only stands for the pack the hinge wraps." + omitted
              + (" The size of the bill-pocket pleat is a drawn guess (no photograph has a scale)." if gus is not None else "")
              + " Panels can pass through each other and nothing here is a leather simulation.")
    shows = ["<em>Flap and spine:</em> the sheet seen along its length: a back panel, the hinge, and the flap that lies over the front, with a block for the pack it wraps."]
    if gus is not None:
        shows.append("<em>Bill-pocket gusset:</em> one side pleat of the large pocket seen across its width. The V closes flat when the pocket is empty.")
    shows.append("Each fold turns through a fixed length of sheet, so a fold that opens gets a larger radius.")
    real = ["Closed thickness at the fold edge-on with a ruler, and how much of it the hinge actually wraps.",
            "The sheet thickness, measured at several points: it sets every radius here."]
    if gus is not None:
        real.insert(1, "One gusset crease photographed edge-on, empty and loaded, with a ruler: its radius is assumed here and sets the tightest fold.")
    real.append("The flat pattern, to say which fold is which.")
    text = {"eyebrow": f"{E(str(rec.raw.get('maker', '')))} &middot; fold structure", "banner": banner, "shows": shows, "real": real}
    return {"cfg": cfg, "text": text, "n": 0}


def _v(x):
    """The value of a record leaf ({value, source, ref}) or the bare value."""
    return x["value"] if isinstance(x, dict) and "value" in x else x


def _twin(rec: WalletRecord, asm: dict) -> dict:
    """The functional twin: real-size layers read from assembly.yaml (a reconstruction, with provenance on each number), pockets that fill with cards, the flap hinge."""
    if asm.get("kind") != "twin":
        raise ViewerError("assembly.yaml must have kind: twin")
    L, W = float(_v(asm["back"]["length_mm"])), float(_v(asm["back"]["width_mm"]))
    card, note = asm["card"], asm["note"]
    pockets = []
    for pk in asm["pockets"]:
        key = re.sub(r"[^a-z0-9]+", "_", pk["id"].lower()).strip("_")
        pockets.append({"id": pk["id"], "key": key, "cap": pk.get("cards_capacity"), "role": pk.get("role", "")})
    if len(pockets) != len(asm["walls"]):
        raise ViewerError(f"assembly.yaml: {len(asm['walls'])} walls need {len(asm['walls'])} pockets, got {len(pockets)}")
    walls = [{"id": w["id"], "top": float(w["top_mm"]), "left": float(w["left_inset_mm"]), "right": float(w["right_inset_mm"]),
              "radii": [float(r) for r in w["end_radii_mm"]], "notch": ({"d": float(w["notch"]["depth_mm"]), "h": float(w["notch"]["half_width_mm"])} if w.get("notch") else None)}
             for w in asm["walls"]]
    cl = ((rec.raw.get("construction") or {}).get("closed_thickness_mm") or {})
    st = asm["stud"]
    A = {"L": L, "W": W, "walls": walls, "pockets": pockets, "bills_pocket": asm.get("bills_pocket"),
         "flapLen": float(_v(asm["flap"]["length_mm"])), "flapR": float(_v(asm["flap"]["corner_radius_mm"])), "flapGap": float(_v(asm["flap"]["clearance_mm"])),
         "card": {"l": float(card["length_mm"]), "w": float(card["width_mm"]), "t": float(card["thickness_mm"])}, "note_t": float(note["thickness_mm"]),
         "gapEmpty": float(_v(asm["gap_empty_mm"])), "slack": float(_v(asm["slack_mm"])), "closedDepth": float(_v(cl["value"])) if cl.get("value") else None,
         "stud": {"x": float(_v(st["x_from_free_end_mm"])), "z": float(_v(st["z_from_left_mm"])), "d": float(_v(st["diameter_mm"])), "h": float(_v(st["height_mm"]))}}
    lo, hi = (float(x) for x in asm.get("thickness_range_mm", [rec.shell_t, rec.shell_t]))
    params = [{"id": "t", "label": "Sheet thickness", "min": lo, "max": hi, "step": 0.05, "value": float(rec.shell_t), "unit": "mm", "dec": 2}]
    for pk in pockets:
        cap = pk["cap"]
        params.append({"id": "n_" + pk["key"], "label": f"Cards in the {pk['id']}", "min": 0, "max": 8, "step": 1, "value": 0, "unit": "cards", "dec": 0})
    params.append({"id": "notes", "label": f"Folded banknotes in the {asm.get('bills_pocket', 'bills pocket')}", "min": 0, "max": 20, "step": 1, "value": 0, "unit": "notes", "dec": 0})
    model = {"id": "twin", "kind": "twin", "label": "Wallet", "controls": [{"id": "flap", "label": "Open the flap"}], "params": params,
             "hinges": [{"id": "hinge", "name": "Flap hinge", "closed": 180, "open": 15, "drv": "flap", "tag": "translate(10px, -130%)"}]}
    size = {"L": round(L), "W": round(W), "txt": f"{W:g} x {L:g} mm"}
    cfg = {"T": float(rec.shell_t), "leaves": 0, "models": [model], "sizes": {"closed": size}, "size": "closed", "edgeLabel": "Side view", "words": WORDS, "twin": A}
    depth = f"{A['closedDepth']:g} mm" if A["closedDepth"] else "not recorded"
    text = {
        "eyebrow": f"{E(str(rec.raw.get('maker', '')))} &middot; functional twin",
        "banner": (f"<strong>A reconstruction at the maker's stated size ({W:g} x {L:g} mm, closed depth {depth}), not a scan and not a flat pattern.</strong> The back panel, flap and four layered pockets are drawn at real size from "
                   "a product photograph; how the layers join, and the sheet thickness, are not known and are marked as assumed. Contents change the stack and so the hinge radius. "
                   "Panels are rigid between the folds, the leather is not simulated, and the strain is the closed form scaled with the fold angle."),
        "shows": ["Open the flap, and fill the pockets with ISO cards or folded banknotes: the layers move apart, the closed depth changes and the flap hinge's radius and strain follow.",
                  "Compare the closed depth with the maker's figure: the page states which sheet thickness would reproduce it with the contents you chose.",
                  "Each layer's size comes from the open-wallet photograph, scaled so the body width is the maker's 85 mm (about 3 mm of reading error)."],
        "real": ["The flat pattern (the maker has the laser-cutting file) to replace the photograph reading.", "The sheet thickness, and the closed depth empty and loaded.",
                 "Which three slots the maker means: the photograph shows four layers behind the front panel."],
    }
    return {"cfg": cfg, "text": text, "n": 0}


def config(wallet_dir: str | Path) -> tuple[WalletRecord, dict, dict]:
    """The record, the viewer's configuration (what the geometry library draws) and its page text, all read from the record."""
    rec = load_wallet(wallet_dir)
    if rec.wallet_type != CUSTOM:
        raise ViewerError("only custom (one-sheet) records have a 3D sketch so far; bifold, trifold and z-fold have the fold simulator's plots")
    specs = _specs(rec)
    asm_path = rec.path / "assembly.yaml"
    if asm_path.exists():
        built = _twin(rec, yaml.safe_load(asm_path.read_text()))
    elif any("stack_from_loops" in s for s in specs):
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
