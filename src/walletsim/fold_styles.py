"""Fold styles: the layups a wallet's fold can have, run through the fold simulator side by side.

The question each style answers is *what happens at the fold*: how much strain the leather sees, how hard the fold resists
closing, and where along the strip the bending collects. Two load cases are reported because they answer different
questions and disagree about some styles:

free fold   the strip is folded 180 deg with nothing inside it. Moment-controlled: it shows where each construction bends.
wrap        the strip is folded around a rigid rounded stack (cards, bills). Radius-controlled: the inside radius is the
            stack's. Reported loose (the leather simply lies on the stack) and lightly taut (a small pull on the panel).

Only geometry and stiffness ratios enter. A stiffness is a number you supply (``E``); for a single leather the strain at a
given fold does not depend on it, but the closing moment does (it is proportional to E), and for lined or hinged
constructions the *ratio* of stiffnesses decides how the layers share the bend.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import math
from dataclasses import dataclass

import numpy as np

from .fem.fold import FoldJob, FoldResult, Layer, analytic_wrap, run_fold, uniform

ID1_CARD_MM = 0.76          # ISO/IEC 7810 ID-1 card thickness (nominal)
BIG = 200.0


def stack_inside_radius(n_cards: float, card_mm: float = ID1_CARD_MM) -> float:
    """Inside radius of a fold around a stack of ``n_cards`` whose end is taken as a half-round: half the stack thickness."""
    return n_cards * card_mm / 2


@dataclass(frozen=True)
class StyleParams:
    t: float = 1.2                      # shell leather thickness, mm (1.2 = the cited calfskin)
    E: float = 72.0                     # shell stiffness, MPa: tensile value for 1.2 mm calfskin (Mihai et al. 2022); YOURS differs
    nu: float = 0.3
    skive_ratio: float = 0.5            # thickness left at the fold, as a fraction of t (flesh side removed)
    skive_half_mm: float = 3.0          # skived zone: half width of the thinnest part ...
    taper_mm: float = 3.0               # ... and the length over which it returns to full thickness (also used by the hinge)
    lining_t: float = 0.5               # mm
    lining_e_ratio: float = 1.0         # lining stiffness / shell stiffness (an assumption you vary, not a leather property)
    hinge_half_mm: float = 4.0          # hinged: half width of the hinge zone
    hinge_t_ratio: float = 0.6          # hinge leather thickness / t
    hinge_e_ratio: float = 0.5          # hinge leather stiffness / shell stiffness (assumed)
    lip_ratio: float = 0.5              # turned edge: thickness of the folded-over lip / t (skived; the lip is the same leather)
    binding_ratio: float = 0.4          # bound edge: thickness of each binding layer / t (a strip folded over the edge, one layer per face)
    binding_e_ratio: float = 1.0        # bound edge: binding stiffness / shell stiffness (an assumption you vary)
    groove_half_mm: float = 1.0         # gusset pleat: half width of the thinnest part of the skived crease groove ...
    groove_taper_mm: float = 1.5        # ... and the length over which it returns to full thickness


def _skived_profile(p: StyleParams) -> tuple[tuple[float, float], ...]:
    ts = p.t * p.skive_ratio
    return ((-BIG, p.t), (-(p.skive_half_mm + p.taper_mm), p.t), (-p.skive_half_mm, ts), (0.0, ts))


def plain(p: StyleParams) -> tuple[Layer, ...]:
    return (uniform("shell", p.t, p.E, p.nu, nz=4),)


def skived(p: StyleParams) -> tuple[Layer, ...]:
    return (Layer("shell", _skived_profile(p), p.E, p.nu, 4),)


def lined(p: StyleParams) -> tuple[Layer, ...]:
    return (uniform("shell", p.t, p.E, p.nu, nz=4), uniform("lining", p.lining_t, p.E * p.lining_e_ratio, p.nu, nz=2))


def skived_lined(p: StyleParams) -> tuple[Layer, ...]:
    return (Layer("shell", _skived_profile(p), p.E, p.nu, 4), uniform("lining", p.lining_t, p.E * p.lining_e_ratio, p.nu, nz=2))


def hinged(p: StyleParams) -> tuple[Layer, ...]:
    th, eh = p.t * p.hinge_t_ratio, p.E * p.hinge_e_ratio
    prof = ((-BIG, p.t), (-(p.hinge_half_mm + p.taper_mm), p.t), (-p.hinge_half_mm, th), (0.0, th))
    return (Layer("shell", prof, p.E, p.nu, 4, zones=((-(p.hinge_half_mm + p.taper_mm / 2), 0.0, eh, p.nu),)),)


def turned_edge(p: StyleParams) -> tuple[Layer, ...]:
    """The hem of a turned edge seen where the spine fold crosses it: the shell plus the folded-over lip, the same leather skived
    to ``lip_ratio`` x t and glued flesh to flesh (perfect bond). Its grain face is the one against the stack."""
    return (uniform("shell", p.t, p.E, p.nu, nz=4), uniform("lip", p.t * p.lip_ratio, p.E, p.nu, nz=2))


def bound_edge(p: StyleParams) -> tuple[Layer, ...]:
    """The edge-binding zone seen where the spine fold crosses it: a strip folded over the edge leaves a layer on each face of the
    shell (perfect bond). Outer binding, shell, inner binding."""
    tb, eb = p.t * p.binding_ratio, p.E * p.binding_e_ratio
    return (uniform("binding out", tb, eb, p.nu, nz=2), uniform("shell", p.t, p.E, p.nu, nz=4), uniform("binding in", tb, eb, p.nu, nz=2))


STYLES = {
    "plain": (plain, "one layer, constant thickness"),
    "skived": (skived, "flesh side thinned over the fold, grain face flat"),
    "lined": (lined, "shell with a glued lining (perfect bond)"),
    "skived+lined": (skived_lined, "shell skived at the fold, glued lining"),
    "hinged": (hinged, "thinner, softer leather across the fold zone, bonded butt joint"),
    "turned edge": (turned_edge, "shell + folded-over lip of the same leather (the hem where the spine crosses a turned edge)"),
    "bound edge": (bound_edge, "shell with a binding strip folded over the edge: one layer on each face where the spine crosses it"),
}


@dataclass
class StyleResult:
    name: str
    free: FoldResult
    wrap_loose: FoldResult
    wrap_taut: FoldResult
    taut_closed_form: float             # kinematic tension-face strain (stack radius, taut leather, no solver)
    taut_closed_form_inner: float

    def centre_share(self, half_width_mm: float = 4.0) -> float:
        """Fraction of the 180 deg fold taken within +-half_width of the fold centre in the free fold."""
        return self.free.angle_share(-half_width_mm, 0.0)


def _closed_form_taut(res: FoldResult) -> tuple[float, float]:
    w = res._checked_window()
    vals = [analytic_wrap(res.job, u) for u in res.u[w]]
    return max(v["outer"] for v in vals), min(v["inner"] for v in vals)


def compare_styles(params: StyleParams | None = None, inside_radius_mm: float = 3.0, taut_n_per_mm: float = 0.1,
                   styles: list[str] | None = None, free_run_mm: float = 15.0, workers: int = 4) -> list[StyleResult]:
    p = params or StyleParams()
    names = styles or list(STYLES)
    unknown = [n for n in names if n not in STYLES]
    if unknown:
        raise KeyError(f"unknown style(s) {unknown}; known: {sorted(STYLES)}")
    jobs = []
    for n in names:
        layers = STYLES[n][0](p)
        # a tight stack makes a short bend: keep at least ~14 elements around it (never coarser than 0.5 mm)
        dx = min(0.5, max(0.08, FoldJob(layers, "wrap", inside_radius_mm=inside_radius_mm).arc_mm / 14))
        jobs += [FoldJob(layers, "free", run_mm=free_run_mm),
                 FoldJob(layers, "wrap", inside_radius_mm=inside_radius_mm, dx_mm=dx),
                 FoldJob(layers, "wrap", inside_radius_mm=inside_radius_mm, tension_n_per_mm=taut_n_per_mm, dx_mm=dx)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(run_fold, jobs))
    results = []
    for i, n in enumerate(names):
        free, loose, taut = out[3 * i: 3 * i + 3]
        co, ci = _closed_form_taut(taut)
        results.append(StyleResult(n, free, loose, taut, co, ci))
    return results


def damage_rate_vs_reference(strain: float, reference: float, exponents=(3.0, 12.0)) -> tuple[float, ...]:
    """Relative damage rate per fold, (strain / reference)^m. No leather-specific m is known, so a range is returned."""
    return tuple((strain / reference) ** m for m in exponents)


def format_report(results: list[StyleResult], params: StyleParams, inside_radius_mm: float, n_cards: float | None = None) -> str:
    """The comparison as plain text. Strains are engineering strains on the outer (tension) and inner (compression) faces of the
    whole layup; moments are per mm of wallet width (multiply by the width in mm)."""
    from .fold_screen import STRAIN_SCREEN
    stack = f"stack of {n_cards:g} cards" if n_cards else "stack"
    ref = next((r for r in results if r.name == "plain"), results[0])
    L = [f"fold styles: shell {params.t:g} mm, E = {params.E:g} MPa (supply your own: strain does not depend on it, moment does)",
         f"{stack} -> inside radius {inside_radius_mm:.2f} mm (R/t = {inside_radius_mm / params.t:.1f}). Layers perfectly bonded, isotropic neo-Hookean, plane strain.", ""]
    L += ["A. FREE FOLD, 180 deg, nothing inside: where does each construction bend?",
          f"  {'style':14s} {'closing moment':>15s} {'tension face':>13s} {'compression face':>17s} {'share of the fold in the central 8 mm':>40s}",
          f"  {'':14s} {'[N mm per mm]':>15s}"]
    for r in results:
        L.append(f"  {r.name:14s} {r.free.moment_n_mm:15.2f} {100 * r.free.peak_outer:12.1f}% {100 * r.free.peak_inner:16.1f}% {100 * r.centre_share():39.0f}%")
    L += ["  (a uniform strip shares the fold evenly: 8 mm of a 30 mm half-length is 27 %)", "",
          "B. WRAP around the stack: what does the leather see when the wallet is closed?",
          f"  {'style':14s} {'tension face: loose':>20s} {'taut':>6s} {'limit':>7s} {'compression face (taut)':>24s} {'stand-off, loose':>17s} {'closing moment (taut)':>22s}",
          f"  {'':14s} {'':>20s} {'':>6s} {'(no solver)':>7s} {'':>24s} {'[mm]':>17s} {'[N mm per mm]':>22s}"]
    for r in results:
        L.append(f"  {r.name:14s} {100 * r.wrap_loose.peak_outer:19.1f}% {100 * r.wrap_taut.peak_outer:5.1f}% {100 * r.taut_closed_form:6.1f}% "
                 f"{100 * r.wrap_taut.peak_inner:23.1f}% {r.wrap_loose.standoff_mm:17.2f} {r.wrap_taut.moment_n_mm:22.2f}")
    L += ["  loose = the leather lies on the stack with no pull; taut = a pull of 0.1 N per mm width on the panel; limit = the leather follows the",
          "  stack exactly (closed form, no solver). A real wallet is somewhere between loose and the limit; the pull from the closed panels is not known.", "",
          "C. DAMAGE RATE PER FOLD relative to " + ref.name + " (strain ratio ^ m, tension face). No leather-specific m is known, so both ends are shown:"]
    for r in results:
        w3, w12 = damage_rate_vs_reference(r.wrap_taut.peak_outer, ref.wrap_taut.peak_outer)
        f3, f12 = damage_rate_vs_reference(r.free.peak_outer, ref.free.peak_outer)
        L.append(f"  {r.name:14s} wrap: m=3 {w3:6.2f}x  m=12 {w12:8.3f}x      free fold: m=3 {f3:6.2f}x  m=12 {f12:8.3f}x")
    flagged = [r.name for r in results if max(r.wrap_taut.peak_outer, r.wrap_loose.peak_outer, r.free.peak_outer) >= STRAIN_SCREEN]
    L += ["", "NOTES"]
    if flagged:
        L.append(f"  - tension-face strain >= {100 * STRAIN_SCREEN:.0f} % (screening threshold, not a failure criterion; the neo-Hookean model is unvalidated there): "
                 + ", ".join(flagged))
    L += ["  - the ranking can flip between A and B: a skived or hinged fold concentrates the bend (higher strain in a free fold) but is thinner at the stack (lower strain around it).",
          "  - strains within one thickness of the fold centre or of the start of the bend are excluded (constraint effects).",
          "  - not modelled: permanent set, creep, finish-film cracking, glue-line shear, stitching, friction, and anything that changes with age."]
    return "\n".join(L)


# --------------------------------------------------------------------------------------------------------------------
# Gusset: the accordion pleat (two opposed folds)

PLEAT_LAYUPS = ("plain", "grooved", "grooved+lined")


def pleat_layers(p: StyleParams, layup: str) -> tuple[Layer, ...]:
    """Layup of the strip that forms a pleat, listed from the OUTER face of fold 1 (grain out). 'plain' is an unskived strip,
    'grooved' has the flesh side skived to skive_ratio x t over a crease groove, 'grooved+lined' adds a glued lining."""
    if layup not in PLEAT_LAYUPS:
        raise KeyError(f"unknown pleat layup {layup!r}; known: {PLEAT_LAYUPS}")
    ts = p.t * p.skive_ratio
    groove = ((-BIG, p.t), (-(p.groove_half_mm + p.groove_taper_mm), p.t), (-p.groove_half_mm, ts), (0.0, ts))
    shell = uniform("shell", p.t, p.E, p.nu, 4) if layup == "plain" else Layer("shell", groove, p.E, p.nu, 4)
    if layup == "grooved+lined":
        return (shell, uniform("lining", p.lining_t, p.E * p.lining_e_ratio, p.nu, nz=2))
    return (shell,)


@dataclass
class PleatResult:
    layup: str
    fold_deg: float
    fold1: FoldResult                   # grain out: the grain face is the tension face
    fold2: FoldResult                   # the mirror fold of the S: layers reversed, grain in: the grain face is the compression face

    @property
    def grain1(self) -> float:
        return self.fold1.peak_outer

    @property
    def flesh1(self) -> float:
        return self.fold1.peak_inner

    @property
    def grain2(self) -> float:
        return self.fold2.peak_inner

    @property
    def flesh2(self) -> float:
        return self.fold2.peak_outer

    def crease_radius_mm(self, over_mm: float = 1.0) -> float:
        """Radius of the neutral fibre at the fold centre, from the turning of the cross-section over the central ``over_mm``."""
        a = self.fold1.angle
        lo, hi = (float(v) for v in np.interp([-over_mm, 0.0], self.fold1.angle_u, a))
        return over_mm / (hi - lo) if hi > lo else math.inf

    def centre_share(self, half_width_mm: float = 3.0) -> float:
        return self.fold1.angle_share(-half_width_mm, 0.0)


def compare_pleats(params: StyleParams | None = None, angles=(180.0, 135.0, 90.0, 45.0), layups=PLEAT_LAYUPS,
                   free_run_mm: float = 15.0, dx_mm: float = 0.25, workers: int = 4) -> list[PleatResult]:
    """A pleat folded to each angle (180 = collapsed, smaller = more open), in both senses of the S."""
    p = params or StyleParams()
    jobs, keys = [], []
    for lay in layups:
        L = pleat_layers(p, lay)
        for a in angles:
            jobs.append(FoldJob(L, "free", fold_deg=a, run_mm=free_run_mm, dx_mm=dx_mm, flat_face="outer")); keys.append((lay, a, 1))
            jobs.append(FoldJob(tuple(reversed(L)), "free", fold_deg=a, run_mm=free_run_mm, dx_mm=dx_mm, flat_face="inner")); keys.append((lay, a, 2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = dict(zip(keys, pool.map(run_fold, jobs)))
    return [PleatResult(lay, a, out[(lay, a, 1)], out[(lay, a, 2)]) for lay in layups for a in angles]


def format_pleat_report(results: list[PleatResult], p: StyleParams) -> str:
    L = [f"gusset (accordion pleat): shell {p.t:g} mm, E = {p.E:g} MPa (supply your own: strain does not depend on it, moment does)",
         f"crease groove: flesh side skived to {p.skive_ratio:g} x t over {2 * p.groove_half_mm:g} mm with {p.groove_taper_mm:g} mm tapers (an assumption you vary). "
         "Free fold, 15 mm legs, plane strain, layers bonded.",
         "A pleat is two opposed folds (an S). Fold 1 has the grain outside (grain in tension); fold 2 is its mirror, grain inside (grain in compression).",
         "Fold angle 180 = pleat collapsed, smaller = opened. Moment is per mm of width: it is what the pleat pushes back with.",
         "'grain' = the grain face of the shell; 'back' = the opposite face of the whole layup (the flesh side of a single leather, the lining of a lined one).", ""]
    for lay in dict.fromkeys(r.layup for r in results):
        rows = [r for r in results if r.layup == lay]
        L += [f"layup: {lay}",
              f"  {'fold':>5s} {'opened':>7s} {'moment':>8s} {'crease':>9s} {'central':>8s} | {'fold 1 grain':>13s} {'fold 1 back':>13s} | {'fold 2 grain':>13s} {'fold 2 back':>13s} | {'legs':>5s}",
              f"  {'angle':>5s} {'by':>7s} {'N mm/mm':>8s} {'radius':>9s} {'6 mm':>8s} | {'(tension)':>13s} {'(compr.)':>13s} | {'(compr.)':>13s} {'(tension)':>13s} | {'clear':>5s}"]
        for r in rows:
            ok = "yes" if max(r.fold1.leg_overlap_mm, r.fold2.leg_overlap_mm) < 0.02 else "NO"
            L.append(f"  {r.fold_deg:5.0f} {100 * expansion_for_fold_angle(r.fold_deg):6.0f}% {r.fold1.moment_n_mm:8.2f} {r.crease_radius_mm():6.1f} mm {100 * r.centre_share():7.0f}% | "
                     f"{100 * r.grain1:12.1f}% {100 * r.flesh1:12.1f}% | {100 * r.grain2:12.1f}% {100 * r.flesh2:12.1f}% | {ok:>5s}")
        hi = max(rows, key=lambda r: r.fold_deg)
        mid = next((r for r in rows if r.fold_deg == 90.0), rows[-1])
        L += [f"  strain swing of the grain face between {hi.fold_deg:.0f} and {mid.fold_deg:.0f} deg: fold 1 {100 * (hi.grain1 - mid.grain1):.1f} points, "
              f"fold 2 {100 * abs(hi.grain2 - mid.grain2):.1f} points (per open/close cycle)", ""]
    L += ["KINDS OF GUSSET (all built from the two folds above)",
          f"  {'kind':38s} {'creases':>8s}  how it is simulated"]
    for name, n, _, _, how in GUSSET_KINDS:
        L.append(f"  {name:38s} {('n' if n is None else str(n)):>8s}  {how}")
    L += ["  'opened by' = how far the gusset has opened, as a fraction of its unfolded length: length x cos(fold angle / 2). For a zigzag of equal segments this is",
          "  independent of the number of creases, so more creases do NOT lower the strain per crease at a given opening; they put the same strain on more creases.", "",
          "NOTES",
          "  - crease radius = radius of the neutral fibre at the fold centre as the FEM found it. A pleat is normally pressed into a sharper crease, which this elastic model cannot do",
          "    (no permanent set), so real creases are tighter and more strained than the groove alone gives.",
          "  - 'legs clear' = the inner face stays on its own side of the symmetry plane; contact between the two legs and with the contents is not modelled.",
          "  - the strain swing, not the peak, is what repeats each time the pleat opens and closes. How often that happens per use is not known here.",
          "  - not modelled: permanent set, creep, finish cracking, glue-line shear, stitching of the pleat edges, friction, ageing."]
    return "\n".join(L)


# --------------------------------------------------------------------------------------------------------------------
# Turned edge: the 180 degree turn itself (closed form only)

@dataclass
class EdgeTurn:
    skive_ratio: float
    core_mm: float
    t_turn_mm: float                    # leather thickness at the turn
    inside_radius_mm: float             # half the core
    strain: float                       # kinematic tension-face strain if the leather follows the core exactly
    flags: list[str]
    max_thickness_for_20pct_mm: float   # thickness at the turn that would keep that kinematic strain at the screening threshold


def edge_turn_table(t: float = 1.2, skive_ratios=(1.0, 0.5, 0.35, 0.25), cores=(0.6, 0.3, 0.1)) -> list[EdgeTurn]:
    """Kinematic strain at the fold of a turned edge: the leather folded 180 deg around a core (adhesive, tape, the other leg)
    of thickness ``core``. Closed form only: the elastic FEM does not model the pressing and gluing that forces this fold,
    so it would show the leather bridging the core instead."""
    from .fold_screen import STRAIN_SCREEN, outer_fibre_strain, screen
    rows = []
    for sr in skive_ratios:
        for core in cores:
            ts, r = t * sr, core / 2
            rows.append(EdgeTurn(sr, core, ts, r, outer_fibre_strain(ts, r), screen(ts, r).flags,
                                 STRAIN_SCREEN * 2 * r / (1 - STRAIN_SCREEN)))
    return rows


def format_edge_turn_report(rows: list[EdgeTurn], t: float) -> str:
    lo, hi = min(r.strain for r in rows), max(r.strain for r in rows)
    L = [f"turned edge, the 180 deg turn: {t:g} mm leather folded around a core (glue line, tape, or the other leg); kinematic strain t_turn / (2R + t_turn), R = core / 2",
         "", f"  {'skive':>6s} {'leather at':>11s} {'core':>6s} {'R/t':>5s} {'tension face':>13s}   {'thickness that would give 20 %':>31s}",
         f"  {'ratio':>6s} {'the turn':>11s} {'[mm]':>6s} {'':>5s} {'(kinematic)':>13s}   {'at this core':>31s}"]
    for r in rows:
        L.append(f"  {r.skive_ratio:6.2f} {r.t_turn_mm:8.2f} mm {r.core_mm:6.2f} {r.inside_radius_mm / r.t_turn_mm:5.2f} {100 * r.strain:12.0f}% {r.max_thickness_for_20pct_mm:28.3f} mm")
    L += ["", "NOTES",
          f"  - every row is far above the 20 % screening threshold ({100 * lo:.0f} % to {100 * hi:.0f} %). Strains like these are not elastic, so a real turn must rely on",
          "    permanent deformation, thinning and the glue. This model has none of those (no permanent set), so it cannot say whether a given turn survives.",
          "  - what it does say is how much skiving buys: the kinematic strain falls as the leather at the turn gets thinner, and the last column is the thickness",
          "    that would bring a turn around that core down to the screening threshold.",
          "  - the hem as a double layer where the spine fold crosses it IS simulated: see the 'turned edge' row of `walletsim fold-styles`.",
          "  - an elastic FEM of this turn was tried and rejected: around a 0.3-0.6 mm core the leather bridges the gap (strain 10-22 % against 41-80 % kinematic),",
          "    because nothing in the model presses and glues it down."]
    return "\n".join(L)


# --------------------------------------------------------------------------------------------------------------------
# Box-shaped (flat-walled) spine: the stack has a flat end and the leather turns two corners

@dataclass
class BoxSpineResult:
    corner_radius_mm: float
    wall_half_mm: float
    loose: FoldResult
    taut: FoldResult
    closed_form: float                  # corner strain if the leather followed the corner exactly

    @property
    def is_round(self) -> bool:
        return self.wall_half_mm <= 1e-9


def compare_box_spines(params: StyleParams | None = None, style: str = "plain", half_thickness_mm: float = 1.9,
                       corner_radii=(1.9, 1.5, 1.0, 0.5), taut_n_per_mm: float = 0.1, workers: int = 4) -> list[BoxSpineResult]:
    """The same stack (half thickness ``half_thickness_mm``) with the end of the spine shaped from fully round (corner radius =
    half thickness) to nearly square (small corner radius, flat wall between the corners). Wrap load case, loose and taut."""
    p = params or StyleParams()
    if style not in STYLES:
        raise KeyError(f"unknown style {style!r}; known: {sorted(STYLES)}")
    layers = STYLES[style][0](p)
    radii = [min(r, half_thickness_mm) for r in corner_radii]
    jobs = []
    for rc in radii:
        wall = half_thickness_mm - rc
        probe = FoldJob(layers, "wrap", inside_radius_mm=rc, wall_half_mm=wall)
        dx = min(0.5, max(0.08, probe.bend_mm / 14))
        jobs += [FoldJob(layers, "wrap", inside_radius_mm=rc, wall_half_mm=wall, dx_mm=dx),
                 FoldJob(layers, "wrap", inside_radius_mm=rc, wall_half_mm=wall, dx_mm=dx, tension_n_per_mm=taut_n_per_mm)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(run_fold, jobs))
    res = []
    for i, rc in enumerate(radii):
        loose, taut = out[2 * i], out[2 * i + 1]
        res.append(BoxSpineResult(rc, half_thickness_mm - rc, loose, taut, _closed_form_taut(taut)[0]))
    return res


def format_box_report(results: list[BoxSpineResult], params: StyleParams, style: str, half_thickness_mm: float) -> str:
    L = [f"box-shaped spine: {style} layup, shell {params.t:g} mm, E = {params.E:g} MPa; stack half thickness {half_thickness_mm:g} mm "
         f"(= {2 * half_thickness_mm / 0.76:.1f} cards of 0.76 mm). Wrap load case, plane strain, layers bonded.",
         "The end of the stack goes from a half-round (corner radius = half thickness) to a flat wall with two corners of smaller radius.", "",
         f"  {'corner':>7s} {'flat wall':>10s} | {'tension face at the corner':^28s} | {'compression':>12s} {'stand-off':>10s}",
         f"  {'radius':>7s} {'height':>10s} | {'loose':>8s} {'taut':>8s} {'limit':>9s} | {'face (taut)':>12s} {'loose, mm':>10s}"]
    for r in results:
        tag = "round" if r.is_round else f"{2 * r.wall_half_mm:.1f} mm"
        L.append(f"  {r.corner_radius_mm:5.2f} mm {tag:>10s} | {100 * r.loose.peak_outer:7.1f}% {100 * r.taut.peak_outer:7.1f}% {100 * r.closed_form:8.1f}% | "
                 f"{100 * r.taut.peak_inner:11.1f}% {r.loose.standoff_mm:10.2f}")
    L += ["", "  limit = the leather follows the corner exactly (closed form, no solver).", "",
          "NOTES",
          "  - a square corner is not followed: the leather bridges it (stand-off), so the strain stays far below the limit. That is partly the model's elastic",
          "    leather; a real corner is pressed and set, and would be tighter.",
          "  - the flat wall is straight, so it carries no strain of its own; only the two corners do.",
          "  - no closing moment is reported: the solver measures it at the fold centre, which on a box is the middle of the flat wall and says nothing about the corners,",
          "    so it cannot be compared with the round spine's.",
          "  - the stack is a rigid, frictionless block; not modelled: permanent set, creep, finish cracking, stitching, friction, ageing."]
    return "\n".join(L)


# --------------------------------------------------------------------------------------------------------------------
# Gusset kinds and how much a pleat opens

def fold_angle_for_expansion(fraction: float) -> float:
    """Fold angle (deg) of every crease of an equal-segment zigzag gusset that has opened by ``fraction`` of its unfolded length:
    the extension is L * sin(beta / 2) with interior angle beta = 180 - fold angle, so fold angle = 2 * acos(fraction).
    It does not depend on the number of creases."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must be in [0, 1]")
    return math.degrees(2 * math.acos(fraction))


def expansion_for_fold_angle(fold_deg: float) -> float:
    return math.cos(math.radians(fold_deg) / 2)


GUSSET_KINDS = [
    # name, creases, grain-in-tension creases, grain-in-compression creases, how it is simulated
    ("V gusset (one fold)", 1, 1, 0, "one crease; fold 1 (grain out) or fold 2 (grain in) depending on which way it is folded"),
    ("S / Z accordion (two opposed folds)", 2, 1, 1, "fold 1 and fold 2 of `walletsim gusset`"),
    ("W / M accordion (three folds)", 3, 2, 1, "the same two folds, one of them twice: each crease behaves as in the S"),
    ("n-fold zigzag", None, None, None, "ceil(n/2) creases like fold 1 and floor(n/2) like fold 2"),
    ("round (U) gusset", 0, 0, 0, "no crease: the strip wraps the contents; use `fold-styles --radius` with half the depth"),
    ("box gusset / flat spine", 0, 0, 0, "two corners and a flat wall: `walletsim box-spine`"),
]
