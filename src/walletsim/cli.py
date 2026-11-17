"""Command line entry point:  walletsim screen | validate-fem | sweep | fold-styles | gusset | edge-turn | fit-law"""
from __future__ import annotations

import argparse
import csv
import sys

import numpy as np

from . import __version__
from .damage import fit_law
from .fem.bending import BendingJob, FemUnavailable, job_for_inside_radius, run_bending
from .fold_screen import screen
from .materials import Value


def _screen(a: argparse.Namespace) -> int:
    print(screen(a.t, a.radius))
    return 0


def _validate_fem(a: argparse.Namespace) -> int:
    try:
        res = run_bending(BendingJob(thickness_mm=a.t, angle_deg=a.angle, poisson=0.0))
    except FemUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"strip bent {a.angle:g} deg, t={a.t:g} mm, Poisson 0 (closed form assumes none): inside radius {res.inside_radius_mm:.2f} mm")
    print(f"  outer-fibre strain  closed form {100 * res.analytic_strain:.2f} %   CalculiX {100 * res.fem_max_strain:.2f} %  "
          f"({100 * res.relative_error:+.1f} %)")
    print(f"  bending moment      beam theory {res.analytic_moment_n_mm:.3f} N mm   CalculiX {res.fem_moment_n_mm:.3f} N mm  "
          f"(ratio {res.moment_ratio:.3f})   [{res.runtime_s:.1f} s]")
    ok = abs(res.relative_error) < 0.03 and abs(res.moment_ratio - 1) < 0.02
    return 0 if ok else 1


def _sweep(a: argparse.Namespace) -> int:
    print(f"fold around inside radius {a.inside_radius:g} mm, {a.angle:g} deg, E={a.E:g} MPa, Poisson {a.poisson:g}, neo-Hookean")
    spread = Value(a.E, "assumed", cv=a.cv).sample(a.samples, seed=0) if a.samples and a.cv else None
    print("  t [mm]  closed-form strain  FEM strain   moment [N mm]  (beam)   moment ratio to t=first"
          + ("   moment P5 / P50 / P95 [N mm]" if spread is not None else ""))
    base = None
    for t in a.t:
        try:
            r = run_bending(job_for_inside_radius(t, a.inside_radius, a.angle, youngs_modulus_mpa=a.E, poisson=a.poisson))
        except FemUnavailable as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        base = base or r.fem_moment_n_mm
        print(f"  {t:5.2f}   {100 * r.analytic_strain:14.1f} %   {100 * r.fem_max_strain:8.1f} %   {r.fem_moment_n_mm:12.2f}  "
              f"({r.analytic_moment_n_mm:6.2f})   x{r.fem_moment_n_mm / base:.1f}", end="")
        if spread is not None:
            lo, mid, hi = (r.fem_moment_n_mm * np.percentile(spread, q) / a.E for q in (5, 50, 95))
            print(f"   {lo:6.2f} / {mid:6.2f} / {hi:6.2f}")
        else:
            print()
    print("moment scales linearly with E for this (small-stress) case; strain does not depend on E.")
    if spread is not None:
        print(f"spread: lognormal stiffness, cv={a.cv:g}, {a.samples} samples. For reference: 0.29 is the stiffness cv measured on 9 calfskin "
              "specimens (Mihai et al. 2022); 0.31 (aldehyde) and 0.44 (chrome) are tensile-STRENGTH cvs, a different quantity. "
              "The stiffness spread of YOUR leather is not measured yet.")
    return 0


def _fold_styles(a: argparse.Namespace) -> int:
    from .fem.fold import FemUnavailable as _NoFem
    from .fold_styles import STYLES, StyleParams, compare_styles, format_report, stack_inside_radius
    radius = a.radius if a.radius is not None else stack_inside_radius(a.cards)
    p = StyleParams(t=a.t, E=a.E, nu=a.poisson, skive_ratio=a.skive_ratio, lining_t=a.lining_t,
                    lining_e_ratio=a.lining_e_ratio, hinge_e_ratio=a.hinge_e_ratio, hinge_t_ratio=a.hinge_t_ratio)
    try:
        res = compare_styles(p, radius, taut_n_per_mm=a.taut, styles=a.styles)
    except (FemUnavailable, _NoFem) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {str(exc).strip().splitlines()[0]}", file=sys.stderr)
        return 1
    print(format_report(res, p, radius, None if a.radius is not None else a.cards))
    return 0


def _style_params(a: argparse.Namespace):
    from .fold_styles import StyleParams
    return StyleParams(t=a.t, E=a.E, nu=a.poisson, skive_ratio=a.skive_ratio, lining_t=a.lining_t,
                       lining_e_ratio=a.lining_e_ratio, groove_half_mm=a.groove_width / 2, groove_taper_mm=a.groove_taper)


def _gusset(a: argparse.Namespace) -> int:
    from .fem.fold import FemUnavailable as _NoFem
    from .fold_styles import compare_pleats, format_pleat_report
    p = _style_params(a)
    try:
        res = compare_pleats(p, angles=tuple(a.angles), layups=tuple(a.layups))
    except (FemUnavailable, _NoFem) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {str(exc).strip().splitlines()[0]}", file=sys.stderr)
        return 1
    print(format_pleat_report(res, p))
    return 0


def _edge_turn(a: argparse.Namespace) -> int:
    from .fold_styles import edge_turn_table, format_edge_turn_report
    print(format_edge_turn_report(edge_turn_table(a.t, tuple(a.skive_ratios), tuple(a.cores)), a.t))
    return 0


def _fit_law(a: argparse.Namespace) -> int:
    with open(a.csv, newline="") as f:
        rows = [(float(r["strain"]), float(r["cycles"])) for r in csv.DictReader(f)]
    law = fit_law([r[0] for r in rows], [r[1] for r in rows], source=a.csv)
    print(f"N_crack = {law.coefficient:.4g} * strain^(-{law.exponent:.2f})   R^2 = {law.r_squared:.3f}   "
          f"({law.n_points} points, strain {law.strain_min:g}..{law.strain_max:g})")
    for eps in a.at or []:
        r = law.cycles_to_crack(eps)
        print(f"  strain {eps:g}: {r['cycles']:.3g} cycles  [{r['note']}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="walletsim", description="Leather wallet simulation toolkit")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="level-0 outer-fibre strain for a fold")
    s.add_argument("--t", type=float, required=True, help="leather thickness, mm")
    s.add_argument("--radius", type=float, required=True, help="inside bend radius, mm")
    s.set_defaults(fn=_screen)
    v = sub.add_parser("validate-fem", help="run the CalculiX bending benchmark and compare with theory")
    v.add_argument("--t", type=float, default=1.0)
    v.add_argument("--angle", type=float, default=180.0)
    v.set_defaults(fn=_validate_fem)
    w = sub.add_parser("sweep", help="how strain and bending moment change with leather thickness at a fixed fold radius")
    w.add_argument("--inside-radius", type=float, default=3.0, help="inside bend radius, mm (what the contents impose)")
    w.add_argument("--t", type=float, nargs="+", default=[0.6, 1.0, 1.4, 2.0], help="thicknesses, mm")
    w.add_argument("--E", type=float, default=72.0, help="Young's modulus, MPa (default: 72, the tensile value measured for 1.2 mm calfskin, Mihai et al. 2022; supply your leather's own)")
    w.add_argument("--poisson", type=float, default=0.3)
    w.add_argument("--angle", type=float, default=180.0)
    w.add_argument("--cv", type=float, default=None, help="coefficient of variation of stiffness within the leather, e.g. 0.4")
    w.add_argument("--samples", type=int, default=0, help="number of stiffness samples for the spread (needs --cv)")
    w.set_defaults(fn=_sweep)
    fs = sub.add_parser("fold-styles", help="compare fold constructions (plain, skived, lined, hinged) in a free fold and around a card stack")
    fs.add_argument("--t", type=float, default=1.2, help="shell leather thickness, mm")
    fs.add_argument("--E", type=float, default=72.0, help="shell Young's modulus, MPa (strain does not depend on it, moment does)")
    fs.add_argument("--poisson", type=float, default=0.3)
    g = fs.add_mutually_exclusive_group()
    g.add_argument("--cards", type=float, default=5.0, help="cards in the stack the spine folds around (0.76 mm each, half-round end)")
    g.add_argument("--radius", type=float, default=None, help="inside radius of the fold, mm (overrides --cards)")
    fs.add_argument("--taut", type=float, default=0.1, help="pull on the panel for the 'taut' wrap, N per mm of width")
    fs.add_argument("--skive-ratio", type=float, default=0.5, help="skived thickness at the fold / t")
    fs.add_argument("--lining-t", type=float, default=0.5)
    fs.add_argument("--lining-e-ratio", type=float, default=1.0, help="lining stiffness / shell stiffness (an assumption you vary)")
    fs.add_argument("--hinge-t-ratio", type=float, default=0.6)
    fs.add_argument("--hinge-e-ratio", type=float, default=0.5)
    fs.add_argument("--styles", nargs="+", default=None, help="subset of: plain skived lined skived+lined hinged 'turned edge'")
    fs.set_defaults(fn=_fold_styles)
    gu = sub.add_parser("gusset", help="accordion pleat: two opposed folds at several opening angles, with and without a skived crease groove")
    gu.add_argument("--t", type=float, default=1.2)
    gu.add_argument("--E", type=float, default=72.0)
    gu.add_argument("--poisson", type=float, default=0.3)
    gu.add_argument("--angles", type=float, nargs="+", default=[180, 135, 90, 45], help="fold angles; 180 = collapsed")
    gu.add_argument("--layups", nargs="+", default=["plain", "grooved", "grooved+lined"], help="plain grooved grooved+lined")
    gu.add_argument("--skive-ratio", type=float, default=0.5, help="thickness left in the groove / t")
    gu.add_argument("--groove-width", type=float, default=2.0, help="width of the thinnest part of the groove, mm")
    gu.add_argument("--groove-taper", type=float, default=1.5, help="length over which the groove returns to full thickness, mm")
    gu.add_argument("--lining-t", type=float, default=0.5)
    gu.add_argument("--lining-e-ratio", type=float, default=1.0)
    gu.set_defaults(fn=_gusset)
    et = sub.add_parser("edge-turn", help="turned edge: kinematic strain of the 180 deg turn for several skive depths and core thicknesses")
    et.add_argument("--t", type=float, default=1.2)
    et.add_argument("--skive-ratios", type=float, nargs="+", default=[1.0, 0.5, 0.35, 0.25])
    et.add_argument("--cores", type=float, nargs="+", default=[0.6, 0.3, 0.1], help="thickness of what the leather is folded around, mm")
    et.set_defaults(fn=_edge_turn)
    f = sub.add_parser("fit-law", help="fit a cycles-to-crack law to your flex-test data (csv: strain,cycles)")
    f.add_argument("csv")
    f.add_argument("--at", type=float, nargs="*", help="strains (fraction) to predict at")
    f.set_defaults(fn=_fit_law)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
