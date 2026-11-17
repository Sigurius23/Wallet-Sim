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
from dataclasses import dataclass

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


STYLES = {
    "plain": (plain, "one layer, constant thickness"),
    "skived": (skived, "flesh side thinned over the fold, grain face flat"),
    "lined": (lined, "shell with a glued lining (perfect bond)"),
    "skived+lined": (skived_lined, "shell skived at the fold, glued lining"),
    "hinged": (hinged, "thinner, softer leather across the fold zone, bonded butt joint"),
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
