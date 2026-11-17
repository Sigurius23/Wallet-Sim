"""Wallet records: read a ``wallet.yaml``, check that every simulation input says where it came from, and map it onto the simulator.

The record format is described in ``docs/DATA_MODEL.md``. Provenance values (the ``source`` of every number that feeds a simulation):

``measured``   you measured it on the object
``inferred``   read from photos or drawings, not measured
``design``     what a design file or pattern specifies; the physical object may differ
``literature`` from a cited publication or standard
``assumed``    a stand-in; any result that depends on it says so

Nothing here guesses: a missing required value is an error, not a default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .fold_styles import STYLES, StyleParams
from .wallet_types import WALLET_TYPES, Contents, Fold, WalletPlan, plan_for

CUSTOM = "custom"        # a wallet whose folds are listed one by one in construction.folds_modelled (origami and other one-sheet constructions)

PROVENANCE = ("measured", "inferred", "design", "literature", "assumed")


class RecordError(ValueError):
    """The record is missing something the simulator needs, or a value has no provenance."""


@dataclass(frozen=True)
class Input:
    name: str
    value: object
    unit: str
    source: str
    ref: str = ""
    feeds: str = ""                     # what in the simulation it changes


@dataclass(frozen=True)
class CustomFold:
    name: str
    stack_mm: float
    low_mm: float | None
    high_mm: float | None
    source: str
    sense: str
    cycles_per_use: float = 1.0
    ref: str = ""


@dataclass
class WalletRecord:
    path: Path
    raw: dict
    id: str
    name: str
    status: str
    inputs: list[Input]
    shell_t: float
    slot_t: float
    youngs_modulus_mpa: float
    youngs_cv: float | None
    poisson: float
    cards: float
    card_mm: float
    extra_mm: float
    interior_layers: float
    stack_override: float | None        # measured or recorded stack at the spine, if any
    stack_source: str
    wallet_type: str
    type_args: dict
    spine: str
    corner_mm: float | None
    layup: str
    seams: list[dict] = field(default_factory=list)
    folds: list[dict] = field(default_factory=list)
    custom_folds: list[CustomFold] = field(default_factory=list)
    closed_thickness_known: float | None = None     # custom wallets: the closed thickness if recorded

    @property
    def interior_leather_mm(self) -> float:
        return self.interior_layers * self.slot_t

    @property
    def stack_at_spine_mm(self) -> float:
        if self.wallet_type == CUSTOM:
            spine = next((f for f in self.custom_folds if f.name.lower().startswith("spine")), self.custom_folds[0])
            return spine.stack_mm
        if self.stack_override is not None:
            return self.stack_override
        return self.cards * self.card_mm + self.extra_mm + self.interior_layers * self.slot_t

    def contents(self) -> Contents:
        """Contents as the wallet-type model wants them: the stack the spine wraps (cards plus interior leather, or the recorded stack)."""
        if self.stack_override is not None:
            return Contents(cards=0, extra_mm=self.stack_override)
        return Contents(cards=self.cards, card_mm=self.card_mm, extra_mm=self.extra_mm + self.interior_layers * self.slot_t)

    def style_params(self) -> StyleParams:
        return StyleParams(t=self.shell_t, E=self.youngs_modulus_mpa, nu=self.poisson, lining_t=self.slot_t)

    def plan(self, contents: Contents | None = None) -> WalletPlan:
        if self.wallet_type == CUSTOM:
            folds = tuple(Fold(f.name, f.stack_mm, f.sense, f.cycles_per_use) for f in self.custom_folds)
            closed = self.closed_thickness_known if self.closed_thickness_known is not None else float("nan")
            return WalletPlan("custom", len(folds) + 1, folds, closed, "folds listed in the record: " + ", ".join(f.name for f in self.custom_folds))
        return plan_for(self.wallet_type, contents or self.contents(), self.shell_t, **self.type_args)

    def provenance_counts(self) -> dict[str, int]:
        out = {k: 0 for k in PROVENANCE}
        for i in self.inputs:
            out[i.source] += 1
        return out

    def not_measured(self) -> list[Input]:
        return [i for i in self.inputs if i.source != "measured"]


def _leaf(d: dict, path: str, errors: list[str], unit: str = "", optional: bool = False):
    """A number with provenance: a mapping with 'value' and a known 'source'. Returns (value, source, ref) or None."""
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            if not optional:
                errors.append(f"missing {path}")
            return None
        cur = cur[k]
    if not isinstance(cur, dict) or "value" not in cur or "source" not in cur:
        errors.append(f"{path} needs {{value, source}} (a number must say where it came from)")
        return None
    if cur["source"] not in PROVENANCE:
        errors.append(f"{path}: unknown source {cur['source']!r}; use one of {PROVENANCE}")
        return None
    return cur["value"], cur["source"], str(cur.get("ref", cur.get("note", "")))


def load_wallet(path: str | Path) -> WalletRecord:
    p = Path(path)
    yml = p / "wallet.yaml" if p.is_dir() else p
    if not yml.exists():
        raise RecordError(f"no wallet.yaml at {yml}")
    raw = yaml.safe_load(yml.read_text())
    if not isinstance(raw, dict):
        raise RecordError(f"{yml} is not a mapping")
    errors: list[str] = []
    for key in ("id", "name", "leather", "contents", "construction"):
        if key not in raw:
            errors.append(f"missing {key}")
    leather = {l.get("id"): l for l in raw.get("leather", []) if isinstance(l, dict)}
    if "shell" not in leather:
        errors.append("leather needs an entry with id: shell")
    shell = leather.get("shell", {})
    slot = leather.get("slot", {})
    inputs: list[Input] = []

    def need(d: dict, path: str, name: str, unit: str, feeds: str, optional: bool = False):
        got = _leaf(d, path, errors, unit, optional)
        if got is None:
            return None
        v, src, ref = got
        inputs.append(Input(name, v, unit, src, ref, feeds))
        return v

    shell_t = need(shell, "thickness_mm", "shell thickness", "mm", "strain at the fold (t / (2R + t)) and stiffness")
    slot_t = need(slot, "thickness_mm", "slot-leather thickness", "mm", "the stack the spine wraps", optional=True) or 0.0
    E = need(shell, "material.youngs_modulus_mpa", "shell stiffness E", "MPa", "closing moment (not strain)")
    nu = need(shell, "material.poisson", "Poisson's ratio", "-", "small effect on moment", optional=True)
    cv = None
    try:
        cv = shell["material"]["youngs_modulus_mpa"].get("cv")
    except (KeyError, TypeError, AttributeError):
        pass
    cons = raw.get("construction", {})
    is_custom = cons.get("type") == CUSTOM
    cards = need(raw, "contents.cards", "cards", "", "the stack the spine wraps", optional=is_custom)
    card_mm = need(raw, "contents.card_mm", "card thickness", "mm", "the stack the spine wraps", optional=is_custom)
    extra = need(raw, "contents.extra_mm", "other contents", "mm", "the stack the spine wraps", optional=True) or 0.0
    layers = need(cons, "interior_leather_layers", "interior leather layers at the spine", "", "the stack the spine wraps", optional=True) or 0
    override = None
    stack_source = "assumed"
    stack_leaf = _leaf(cons, "stack_at_spine_mm", [], optional=True)
    closed_leaf = _leaf(cons, "closed_thickness_mm", [], optional=True)
    if stack_leaf is not None:
        override, stack_source, ref = stack_leaf[0], stack_leaf[1], stack_leaf[2]
        inputs.append(Input("stack at the spine", override, "mm", stack_source, ref, "the inside radius of the spine fold (the biggest lever)"))
    elif closed_leaf is not None and shell_t:
        override = float(closed_leaf[0]) - 2 * float(shell_t)          # a bifold: two shell thicknesses at the spine
        stack_source = closed_leaf[1]
        inputs.append(Input("closed thickness at the spine", closed_leaf[0], "mm", closed_leaf[1], closed_leaf[2],
                            "the inside radius of the spine fold (stack = closed thickness - 2 x shell)"))
    wtype = cons.get("type")
    if wtype not in WALLET_TYPES and wtype != CUSTOM:
        errors.append(f"construction.type must be one of {sorted(WALLET_TYPES) + [CUSTOM]}, got {wtype!r}")
    custom: list[CustomFold] = []
    closed_known = None
    if wtype == CUSTOM:
        specs = cons.get("folds_modelled") or []
        if not specs:
            errors.append("construction.type custom needs construction.folds_modelled: a list of {name, stack_mm, sense}")
        for k, fs in enumerate(specs):
            nm = fs.get("name", f"fold {k + 1}")
            got = _leaf(fs, "stack_mm", errors)
            if got is None:
                continue
            sense = fs.get("sense", "out")
            if sense not in ("out", "in"):
                errors.append(f"{nm}: sense must be out or in")
            leaf = fs["stack_mm"]
            lo, hi = leaf.get("low"), leaf.get("high")
            if (lo is None) != (hi is None) or (lo is not None and not lo <= got[0] <= hi):
                errors.append(f"{nm}: give both low and high with low <= value <= high, or neither")
            custom.append(CustomFold(nm, float(got[0]), lo, hi, got[1], sense, float(fs.get("cycles_per_use", 1.0)), got[2]))
            inputs.append(Input(f"{nm}: stack it wraps", got[0], "mm", got[1], got[2], "the inside radius of this fold"))
        cl = _leaf(cons, "closed_thickness_mm", [], optional=True)
        if cl is not None:
            closed_known = float(cl[0])
            inputs.append(Input("closed thickness", cl[0], "mm", cl[1], cl[2], "report only"))
    spine = "round"
    sp = cons.get("spine", "round")
    if isinstance(sp, dict):
        spine = sp.get("value", "round")
        inputs.append(Input("spine shape", spine, "", sp.get("source", "assumed"), str(sp.get("ref", "")), "round or box-shaped end of the stack"))
    else:
        spine = sp
    if spine not in ("round", "box"):
        errors.append("construction.spine must be round or box")
    layup = cons.get("layup", "plain")
    if layup not in STYLES:
        errors.append(f"construction.layup must be one of {sorted(STYLES)}, got {layup!r}")
    if errors:
        raise RecordError(f"{yml}:\n  - " + "\n  - ".join(errors))
    type_args = {k: cons[k] for k in ("panels", "split") if k in cons}
    return WalletRecord(path=yml.parent, raw=raw, id=raw["id"], name=raw["name"], status=raw.get("status", "design"), inputs=inputs,
                        shell_t=float(shell_t), slot_t=float(slot_t), youngs_modulus_mpa=float(E), youngs_cv=cv,
                        poisson=float(nu if nu is not None else 0.3), cards=float(cards or 0), card_mm=float(card_mm or 0.76), extra_mm=float(extra),
                        interior_layers=float(layers), stack_override=override, stack_source=stack_source, wallet_type=wtype,
                        type_args=type_args, spine=spine, corner_mm=cons.get("corner_mm"), layup=layup,
                        seams=list(raw.get("seams", [])), folds=list(raw.get("folds", [])), custom_folds=custom,
                        closed_thickness_known=closed_known)


# What to measure first, and how. Ordered by how much it moves the spine result (see the sensitivity table in the report).
MEASURE_FIRST = [
    ("stack at the spine", "Measure the closed wallet's thickness at the spine with calipers (and its shell thickness); put it in `construction.closed_thickness_mm`. "
                           "It sets the fold radius, which sets the strain."),
    ("spine fold radius", "Photograph the closed spine edge-on against a ruler. The radius and the gap between leather and contents show how tightly the leather really sits on the stack (loose or taut)."),
    ("shell thickness", "Calipers at 3 or more points along the shell, away from edges."),
    ("shell stiffness E", "A cantilever bend test on a strip, or any measurement of this leather; it sets the closing moment (not the strain)."),
    ("edge treatment and stitching", "Record the edge finish (painted, burnished, turned, bound) and whether stitching crosses the spine."),
    ("wear history", "If it has been used: photographs of the spine and the pocket mouths, and roughly how long and how it was carried."),
]


MEASURE_FIRST_CUSTOM = [
    ("closed thickness and the layers at the spine", "Calipers across the closed wallet at the spine, and count the layers edge-on. It sets the spine's inside radius."),
    ("the loops' inside radius", "Photograph each hairpin fold edge-on next to a ruler (or measure the gap with a caliper). The tight loops are the folds the model can only screen, and their radius decides everything."),
    ("sheet thickness", "Calipers at 3 or more points along the sheet, away from the edges and folds; the retailer says 1 mm."),
    ("how the folds are made", "Ask the maker whether the leather is skived or dampened at the folds, and what the thread ties do; both are unknown now."),
    ("stiffness and ageing", "A bend test on an offcut or a worn sample gives the closing moment; fold-and-measure strips give permanent set."),
    ("wear history", "If a used one is available: photographs of the loops and the spine, and how long and how it was carried."),
]
