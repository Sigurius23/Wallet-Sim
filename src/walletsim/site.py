"""The archive app: one self-contained HTML file that browses every wallet record in ``wallets/``.

``walletsim build-site`` reads each ``wallets/<id>/wallet.yaml`` (and its latest stored report run and 3D sketch) and writes ``site/index.html``: nothing to host but the file.
Everything on the screen comes from the records. Where a record does not say (a year, a hide region, a process step), the app says "not recorded" instead of filling the gap, and
every figure carries the provenance the record gave it (measured, reported, inferred, design, literature, assumed). Photographs are shown only when a record names a hero image
that its rights note allows; otherwise the app draws the wallet's cross-section from the record's fold structure.

The behaviour of the app is in ``site_template.html``; this module only turns records into the JSON the app reads.
"""
from __future__ import annotations

import base64
import json
import re
from importlib import resources
from pathlib import Path

from . import __version__ as _version  # noqa: F401  (kept so the site can state which walletsim built it)
from .page import chart_rows, finding_text, latest_run, _chart
from .leather_cards import LeatherCard, PROPERTIES, coverage, load_cards
from .record import WalletRecord, load_wallet, measure_first
from .species import classify, species_of
from .viewer import ViewerError, build_viewer, config as viewer_config

STATUS_LABEL = {
    "design": "Design file",
    "photos-only": "Photos and text only",
    "measured": "Measured",
}
STATUS_NOTE = {
    "design": "Generated from a design file. Nothing about a physical wallet is measured.",
    "photos-only": "Built from a retailer's or reseller's text and product photographs. Nothing has been measured on a physical wallet.",
    "measured": "Measured on a physical wallet.",
}
WINDOWS = [("beamhouse", "Raw hide"), ("tanning", "Tanning"), ("post_tanning", "Post-tanning"), ("finishing", "Finishing")]


def _leaf(x) -> dict:
    """A record value as {value, source, ref}: a leaf with provenance, a bare value, or 'unknown' / missing."""
    if isinstance(x, dict) and "value" in x:
        v = x.get("value")
        return {"value": None if v in (None, "unknown") else v, "source": x.get("source", ""), "ref": x.get("ref", "") or x.get("note", "")}
    if x in (None, "unknown"):
        return {"value": None, "source": "", "ref": ""}
    return {"value": x, "source": "", "ref": ""}


def _fmt(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _corpus(rec: WalletRecord) -> dict | None:
    for path in (rec.raw.get("photos") or {}).values():
        m = re.match(r"corpus:([^@]+)@([0-9a-f]+)/.*?/items/([^/]+)/", str(path))
        if m:
            return {"repo": m.group(1), "commit": m.group(2), "item": m.group(3)}
    return None


def _photos(rec: WalletRecord) -> list[dict]:
    out = []
    for role, path in (rec.raw.get("photos") or {}).items():
        out.append({"role": str(role).replace("_", " "), "path": str(path).split("/")[-1], "full": str(path)})
    return out


def _hero(rec: WalletRecord, wdir: Path) -> str | None:
    """A hero photograph as a data URI, only if the record names one. Records whose photographs are research documentation name none."""
    hero = (rec.raw.get("archive") or {}).get("hero_image")
    if not hero:
        return None
    p = wdir / str(hero)
    if not p.exists():
        return None
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(p.suffix.lower().lstrip("."), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def _sizes_text(rec: WalletRecord) -> tuple[str | None, str]:
    sizes = rec.raw.get("sizes") or {}
    parts, src = [], ""
    for k, s in sizes.items():
        fp = s.get("closed_footprint_cm")
        if fp:
            parts.append(f"{k} {float(fp[0]):g} x {float(fp[1]):g} cm")
            src = src or s.get("source", "")
    return (" · ".join(parts) or None), src


def _facts(rec: WalletRecord, behaviour: dict | None) -> list[dict]:
    raw = rec.raw
    arch = raw.get("archive") or {}
    shell = next((l for l in raw.get("leather", []) if l.get("id") == "shell"), (raw.get("leather") or [{}])[0])
    facts: list[dict] = []

    def add(label, value, source="", ref=""):
        facts.append({"label": label, "value": value if value is None or isinstance(value, str) else _fmt(value), "source": source, "ref": ref})

    add("Designer", raw.get("maker"))
    add("Series", arch.get("series"))
    year = arch.get("year")
    add("Year", None if year in (None, "unknown") else str(year), ref=(arch.get("year_note") or "") if year else "No design date is recorded.")
    sizes, ssrc = _sizes_text(rec)
    add("Closed size", sizes, ssrc)
    th = _leaf(shell.get("thickness_mm"))
    add("Sheet thickness", None if th["value"] is None else f"{_fmt(th['value'])} mm", th["source"], th["ref"])
    sp = _leaf(shell.get("species"))
    add("Species", sp["value"], sp["source"], sp["ref"])
    win = shell.get("windows") or {}
    tn, fn = _leaf(win.get("tanning")), _leaf(win.get("finishing"))
    add("Tanning", tn["value"], tn["source"], tn["ref"])
    add("Finishing", fn["value"], fn["source"], fn["ref"])
    hr = _leaf(shell.get("hide_region"))
    add("Hide region", hr["value"], hr["source"], hr["ref"])
    cl = _leaf((raw.get("construction") or {}).get("closed_thickness_mm"))
    if cl["value"] is not None:
        add("Closed depth", f"{_fmt(cl['value'])} mm", cl["source"], cl["ref"])
    n = len(rec.custom_folds) if rec.wallet_type == "custom" else len(rec.plan().folds)
    add("Folds modelled", str(n))
    if behaviour and behaviour.get("rows"):
        top = max(behaviour["rows"], key=lambda r: r["rec"])
        add("Highest fold strain", f"{round(100 * top['rec'] + 1e-9):d} % at {top['name'].lower()}", "model",
            "Closed form at the recorded stack; the range across the stacks tried is on the Behaviour tab.")
    usage = raw.get("usage") or {}
    add("Condition", usage.get("condition") if usage.get("used") else "Not recorded as used", "reported" if usage.get("used") else "")
    return facts


def _components(rec: WalletRecord) -> list[dict]:
    out = []
    for l in rec.raw.get("leather", []):
        win = l.get("windows") or {}
        out.append({
            "id": l.get("id"), "role": l.get("role") or l.get("id"),
            "species": _leaf(l.get("species")), "region": _leaf(l.get("hide_region")), "thickness": _leaf(l.get("thickness_mm")),
            "edge": _leaf(l.get("edge")), "windows": {k: _leaf(win.get(k)) for k, _ in WINDOWS},
        })
    return out


def _pipeline(rec: WalletRecord) -> list[dict]:
    """The treatment pipeline: the record's ordered process steps, or, when there are none, the four windows of the first leather with what the record says for each."""
    steps = rec.raw.get("process_steps") or []
    if steps:
        return [{"n": s.get("order", i + 1), "label": s.get("name", ""), "window": s.get("window", ""), "value": None, "source": s.get("source", ""), "ref": ""}
                for i, s in enumerate(steps)]
    first = (rec.raw.get("leather") or [{}])[0].get("windows") or {}
    return [{"n": i + 1, "label": lab, "window": key, **{k: v for k, v in _leaf(first.get(key)).items()}} for i, (key, lab) in enumerate(WINDOWS)]


def _behaviour(rec: WalletRecord, wdir: Path) -> dict:
    """What the latest stored report run says, or what is missing."""
    try:
        run = latest_run(wdir)
    except FileNotFoundError:
        return {"has_run": False, "command": f"walletsim wallet-report wallets/{rec.id}"}
    d = json.loads((run / "result.json").read_text())
    rows = chart_rows(d)
    return {
        "has_run": True, "run": run.name, "meta": d["meta"], "rows": rows, "chart": _chart(rows), "finding": finding_text(rows),
        "folds": d["folds"], "modes": d["failure_modes"], "inputs": d["inputs"],
        "counts": rec.provenance_counts(),
        "measure": [{"name": a, "how": b} for a, b in measure_first(rec)],
    }


def card_view(c: LeatherCard) -> dict:
    """A card as the app shows it: one row per property that has a value, each with its source, plus what the card must not be used for."""
    rows = []
    for key, label in PROPERTIES:
        v = c.props.get(key)
        if c.has(key) and isinstance(v, dict) and "value" in v:
            text = f"{v['value']:g}" + (f" (low {v['low']:g}, high {v['high']:g})" if v.get("low") is not None else "") + (f", spread {100 * v['cv']:.0f} %" if v.get("cv") else "")
            rows.append({"label": label, "text": text, "source": v["source"], "ref": v.get("ref", "")})
        elif c.partial(key):
            rows.append({"label": label, "text": "not measured; only tested " + c.partial(key), "source": "", "ref": ""})
    return {"id": c.id, "name": c.name, "species": c.species, "group": c.group, "tanning": c.tanning, "test": c.test, "cite": c.cite, "rows": rows, "not_this": c.not_this}


def _hide(rec: WalletRecord, cards: list[LeatherCard]) -> dict:
    sp = species_of(rec.raw)
    cls = classify(sp)
    return {"species": sp, "group": cls.group, "name": cls.name, "class": cls.hide_class, "why": cls.why, "anatomy": cls.anatomy_file,
            "cards": [c.id for c in cards if cls.group and c.group == cls.group]}


def _fold_models(rec: WalletRecord) -> dict | None:
    """How each fold's stack depends on the sheet thickness, so the app can recompute the closed-form strain live when a viewer moves the thickness slider.

    fixed: the stack is a number; closed: stack = closed depth - shells x t; loops: stack = leaves x t + (leaves + 1) x gap, the gap being another fold's stack."""
    if rec.wallet_type != "custom":
        return None
    cons = rec.raw.get("construction") or {}
    cl = _leaf(cons.get("closed_thickness_mm"))
    out = []
    for sp, f in zip(cons.get("folds_modelled") or [], rec.custom_folds):
        d = {"name": f.name, "sense": f.sense, "source": f.source}
        if "stack_from_closed_thickness" in sp:
            s = sp["stack_from_closed_thickness"]
            d.update(kind="closed", depth=cl["value"], shells=s.get("shells", 2), low=s.get("low"))
        elif "stack_from_loops" in sp:
            s = sp["stack_from_loops"]
            d.update(kind="loops", leaves=_leaf(s["leaves"])["value"], gap_from=s["gap_from"])
        else:
            d.update(kind="fixed", stack=f.stack_mm, low=f.low_mm, high=f.high_mm)
        out.append(d)
    return {"t": float(rec.shell_t), "folds": out}


def _styles(wdir: Path) -> dict | None:
    p = wdir / "sim" / "styles.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def wallet_entry(wdir: Path, cards: list[LeatherCard] | None = None) -> dict:
    rec = load_wallet(wdir)
    arch = rec.raw.get("archive") or {}
    behaviour = _behaviour(rec, wdir)
    try:
        vrec, vcfg, _ = viewer_config(wdir)
        viewer = {"cfg": vcfg, "html": build_viewer(wdir, embed=True)}
    except ViewerError:
        viewer = None
    year = arch.get("year")
    return {
        "id": rec.id, "name": rec.name, "designer": rec.raw.get("maker") or "Unknown designer", "series": arch.get("series") or "",
        "year": int(year) if isinstance(year, int) or (isinstance(year, str) and year.isdigit()) else None,
        "status": rec.status, "status_label": STATUS_LABEL.get(rec.status, rec.status), "status_note": STATUS_NOTE.get(rec.status, ""),
        "usage": rec.raw.get("usage") or {}, "bio_ref": arch.get("bio_ref"), "rights": arch.get("rights") or {}, "rights_note": rec.raw.get("rights_note", ""),
        "hero": _hero(rec, wdir), "facts": _facts(rec, behaviour), "components": _components(rec), "pipeline": _pipeline(rec),
        "photos": _photos(rec), "corpus": _corpus(rec), "behaviour": behaviour, "viewer": viewer, "swap": _fold_models(rec), "styles": _styles(wdir), "hide": _hide(rec, cards or []),
        "counts": rec.provenance_counts(),
    }


def build_data(wallets_root: str | Path = "wallets", include_designs: bool = False) -> dict:
    root = Path(wallets_root)
    entries, skipped = [], []
    cards = load_cards(root.parent / "cards")
    for wdir in sorted(p for p in root.iterdir() if (p / "wallet.yaml").exists() and not p.name.startswith("_")):
        rec = load_wallet(wdir)
        if rec.status == "design" and not include_designs:                # generated test designs are not archive items
            skipped.append(rec.name)
            continue
        entries.append(wallet_entry(wdir, cards))
    lab_path = root.parent / "lab" / "results.json"
    lab = json.loads(lab_path.read_text(encoding="utf-8")) if lab_path.exists() else None
    from .materials import calfskin_upper_literature
    card = calfskin_upper_literature()
    mat = [{"name": card.name, "species": card.species, "tanning": card.tanning, "E": card.states["new"].youngs_modulus_mpa.value if hasattr(card.states["new"], "youngs_modulus_mpa") else 72.0,
            "source": "literature"}]
    animals = json.loads(resources.files("walletsim").joinpath("assets/animals.json").read_text(encoding="utf-8"))
    return {"version": _version, "wallets": entries, "hidden_designs": skipped, "lab": lab, "materials": mat, "animals": animals,
            "cards": [card_view(c) for c in cards], "coverage": coverage(cards)}


def build_site(wallets_root: str | Path = "wallets", include_designs: bool = False) -> str:
    data = build_data(wallets_root, include_designs)
    tpl = resources.files("walletsim").joinpath("site_template.html").read_text(encoding="utf-8")
    geometry = resources.files("walletsim").joinpath("geometry.js").read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return tpl.replace("{{GEOMETRY_JS}}", geometry).replace("__DATA__", blob)


def write_site(wallets_root: str | Path = "wallets", out: str | Path = "site/index.html", include_designs: bool = False) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_site(wallets_root, include_designs), encoding="utf-8")
    return path
