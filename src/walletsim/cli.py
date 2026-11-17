"""Command line entry point:  walletsim screen | validate-fem | sweep | fold-styles | gusset | box-spine | wallet-types | wallet-report | wallet-page | wallet-viewer | build-site | lab-run | wallet-styles | edge-turn | fit-law"""
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
    from .fold_styles import StyleParams, compare_styles, format_report, stack_inside_radius
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
    from .fold_styles import compare_pleats, fold_angle_for_expansion, format_pleat_report
    p = _style_params(a)
    angles = tuple(fold_angle_for_expansion(f) for f in a.expansion) if a.expansion else tuple(a.angles)
    try:
        res = compare_pleats(p, angles=angles, layups=tuple(a.layups))
    except (FemUnavailable, _NoFem) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {str(exc).strip().splitlines()[0]}", file=sys.stderr)
        return 1
    print(format_pleat_report(res, p))
    return 0


def _box_spine(a: argparse.Namespace) -> int:
    from .fem.fold import FemUnavailable as _NoFem
    from .fold_styles import compare_box_spines, format_box_report, stack_inside_radius
    p = _style_params(a)
    half = a.half_thickness if a.half_thickness is not None else stack_inside_radius(a.cards)
    try:
        res = compare_box_spines(p, a.style, half, tuple(a.corners), a.taut)
    except (FemUnavailable, _NoFem) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {str(exc).strip().splitlines()[0]}", file=sys.stderr)
        return 1
    print(format_box_report(res, p, a.style, half))
    return 0


def _parse_type(token: str) -> tuple[str, dict]:
    """'bifold', 'trifold', 'trifold:0.3' (share of the contents in the inner fold), 'z-fold', 'z-fold:5' (panels)."""
    name, _, arg = token.partition(":")
    if name == "z-fold" and arg:
        return name, {"panels": int(arg)}
    if name == "trifold" and arg:
        return name, {"split": float(arg)}
    if arg:
        raise ValueError(f"{name!r} takes no argument")
    return name, {}


def _wallet_types(a: argparse.Namespace) -> int:
    from .fem.fold import FemUnavailable as _NoFem
    from .wallet_types import ALIASES, WALLET_TYPES, Contents, evaluate_wallet, format_wallet_report, panel_thickness, plan_for
    if a.list:
        print("wallet fold types:", ", ".join(WALLET_TYPES))
        print("  bifold                 two panels, one spine around all the contents")
        print("  trifold[:share]        letter fold; share = part of the contents in the inner fold (default 0.5)")
        print("  z-fold[:panels]        accordion of n panels (default 3), folds alternate grain out / in")
        print("the same fold, different panels or contents:")
        for k, v in ALIASES.items():
            print(f"  {k:28s} -> {v}")
        return 0
    p = _style_params(a)
    c = Contents(cards=a.cards, extra_mm=a.extra_mm, slot_leather_mm=a.slot_leather)
    try:
        types = [_parse_type(t) for t in a.types]
        cycles = dict(kv.split("=") for kv in a.cycles) if a.cycles else None
        cyc = {k: float(v) for k, v in cycles.items()} if cycles else None
        t_panel = panel_thickness(p, a.layup)
        res = []
        for name, kw in types:
            plan = plan_for(name, c, t_panel, **kw)
            sub = {k: v for k, v in (cyc or {}).items() if k in {f.name for f in plan.folds}}
            res.append(evaluate_wallet(plan, p, a.layup, a.spine, a.corner, a.taut, cycles=sub or None))
    except (FemUnavailable, _NoFem) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {str(exc).strip().splitlines()[0]}", file=sys.stderr)
        return 1
    print(format_wallet_report(res, c, p))
    return 0


def _wallet_report(a: argparse.Namespace) -> int:
    from .fem.fold import FemUnavailable as _NoFem
    from .record import RecordError, load_wallet
    from .report import build_report, write_report
    try:
        rec = load_wallet(a.wallet)
        rep = build_report(rec, a.taut, sensitivity=not a.no_sensitivity)
        out = write_report(rep, a.out, figures=not a.no_figures)
    except RecordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (FemUnavailable, _NoFem) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{rec.name}: {rec.provenance_counts()} (inputs by source), stack at the spine {rec.stack_at_spine_mm:.2f} mm")
    for o in rep.base.outcomes:
        if o.taut is not None:
            print(f"  {o.fold.name}: tension-face strain {100 * o.tension('loose'):.1f} % loose, {100 * o.tension('taut'):.1f} % taut (limit {100 * o.closed_form:.1f} %), R/t {o.radius_mm / rec.shell_t:.1f}")
    print(f"report written to {out}/report.md")
    return 0


def _wallet_page(a: argparse.Namespace) -> int:
    from .page import write_page
    try:
        out = write_page(a.run, a.wallet, a.out)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"page written to {out} ({out.stat().st_size / 1e6:.2f} MB)")
    return 0


def _wallet_viewer(a: argparse.Namespace) -> int:
    from .viewer import ViewerError, write_viewer
    try:
        out = write_viewer(a.wallet, a.out)
    except (FileNotFoundError, ValueError, KeyError, ViewerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"3D viewer written to {out} ({out.stat().st_size / 1e3:.0f} kB; it loads Three.js from a CDN)")
    return 0


def _build_site(a: argparse.Namespace) -> int:
    from .site import write_site
    try:
        out = write_site(a.wallets, a.out, a.include_designs)
    except (FileNotFoundError, ValueError, KeyError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"archive app written to {out} ({out.stat().st_size / 1e6:.2f} MB; one file, the 3D sketches load Three.js from a CDN)")
    return 0


def _lab_run(a: argparse.Namespace) -> int:
    from .lab import run_lab
    path = run_lab(a.out, a.only)
    print(f"lab results written to {path}")
    return 0


def _wallet_styles(a: argparse.Namespace) -> int:
    from .fem.fold import FemUnavailable as _NoFem
    from .lab import wallet_styles
    for w in a.wallets:
        try:
            path = wallet_styles(w)
        except (FemUnavailable, _NoFem, ValueError, FileNotFoundError, KeyError) as exc:
            print(f"error: {w}: {exc}", file=sys.stderr)
            return 1
        print(f"styles written to {path}")
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
    fs.add_argument("--styles", nargs="+", default=None, help="subset of: plain skived lined skived+lined hinged 'turned edge' 'bound edge'")
    fs.set_defaults(fn=_fold_styles)
    gu = sub.add_parser("gusset", help="accordion pleat: two opposed folds at several opening angles, with and without a skived crease groove")
    gu.add_argument("--t", type=float, default=1.2)
    gu.add_argument("--E", type=float, default=72.0)
    gu.add_argument("--poisson", type=float, default=0.3)
    gu.add_argument("--angles", type=float, nargs="+", default=[180, 135, 90, 45], help="fold angles; 180 = collapsed")
    gu.add_argument("--expansion", type=float, nargs="+", default=None, help="instead of --angles: how far the gusset has opened, as a fraction of its unfolded length (0 = collapsed, 1 = flat)")
    gu.add_argument("--layups", nargs="+", default=["plain", "grooved", "grooved+lined"], help="plain grooved grooved+lined")
    gu.add_argument("--skive-ratio", type=float, default=0.5, help="thickness left in the groove / t")
    gu.add_argument("--groove-width", type=float, default=2.0, help="width of the thinnest part of the groove, mm")
    gu.add_argument("--groove-taper", type=float, default=1.5, help="length over which the groove returns to full thickness, mm")
    gu.add_argument("--lining-t", type=float, default=0.5)
    gu.add_argument("--lining-e-ratio", type=float, default=1.0)
    gu.set_defaults(fn=_gusset)
    bs = sub.add_parser("box-spine", help="spine with a flat end wall and two corners, against a round spine, for the same stack")
    bs.add_argument("--t", type=float, default=1.2)
    bs.add_argument("--E", type=float, default=72.0)
    bs.add_argument("--poisson", type=float, default=0.3)
    g2 = bs.add_mutually_exclusive_group()
    g2.add_argument("--cards", type=float, default=5.0, help="cards in the stack (0.76 mm each)")
    g2.add_argument("--half-thickness", type=float, default=None, help="half the stack thickness, mm (overrides --cards)")
    bs.add_argument("--corners", type=float, nargs="+", default=[1.9, 1.5, 1.0, 0.5], help="corner radii, mm; the largest allowed is the half thickness (= round)")
    bs.add_argument("--style", default="plain", help="layup: plain skived lined skived+lined hinged")
    bs.add_argument("--taut", type=float, default=0.1)
    bs.add_argument("--skive-ratio", type=float, default=0.5)
    bs.add_argument("--lining-t", type=float, default=0.5)
    bs.add_argument("--lining-e-ratio", type=float, default=1.0)
    bs.add_argument("--groove-width", type=float, default=2.0)
    bs.add_argument("--groove-taper", type=float, default=1.5)
    bs.set_defaults(fn=_box_spine)
    wt = sub.add_parser("wallet-types", help="overall wallet fold types (bifold, trifold, z-fold): the stack each fold wraps, which fold wears first")
    wt.add_argument("--list", action="store_true", help="list the types and what is the same fold")
    wt.add_argument("--types", nargs="+", default=["bifold", "trifold", "z-fold:3", "z-fold:4"], help="bifold trifold[:share] z-fold[:panels]")
    wt.add_argument("--cards", type=float, default=8.0)
    wt.add_argument("--extra-mm", type=float, default=0.0, help="other contents (notes, receipts, a passport), total thickness in mm")
    wt.add_argument("--slot-leather", type=float, default=0.0, help="mm of pocket leather per card (an assumption; 0 ignores it)")
    wt.add_argument("--layup", default="plain", help="plain skived lined skived+lined hinged 'turned edge' 'bound edge'")
    wt.add_argument("--spine", choices=["round", "box"], default="round")
    wt.add_argument("--corner", type=float, default=None, help="box spine: corner radius, mm (default 1.0)")
    wt.add_argument("--taut", type=float, default=0.1)
    wt.add_argument("--cycles", nargs="*", default=None, help="cycles per use for a fold, e.g. 'spine=2' (default 1 each)")
    wt.add_argument("--t", type=float, default=1.2)
    wt.add_argument("--E", type=float, default=72.0)
    wt.add_argument("--poisson", type=float, default=0.3)
    wt.add_argument("--skive-ratio", type=float, default=0.5)
    wt.add_argument("--lining-t", type=float, default=0.5)
    wt.add_argument("--lining-e-ratio", type=float, default=1.0)
    wt.add_argument("--groove-width", type=float, default=2.0)
    wt.add_argument("--groove-taper", type=float, default=1.5)
    wt.set_defaults(fn=_wallet_types)
    wr = sub.add_parser("wallet-report", help="run a wallet record (wallets/<id>) through the simulator and write its report, figures and inputs")
    wr.add_argument("wallet", help="a wallets/<id> folder or a wallet.yaml")
    wr.add_argument("--out", default=None, help="output folder (default: <wallet>/sim/run-<hash>)")
    wr.add_argument("--taut", type=float, default=0.1)
    wr.add_argument("--no-sensitivity", action="store_true", help="skip the stack-size scenarios (faster)")
    wr.add_argument("--no-figures", action="store_true")
    wr.set_defaults(fn=_wallet_report)
    wp = sub.add_parser("wallet-page", help="build a self-contained HTML page from a wallet's latest report run")
    wp.add_argument("wallet", nargs="?", default=None, help="a wallets/<id> folder (uses its latest run)")
    wp.add_argument("--run", default=None, help="a specific sim/run-<hash> folder")
    wp.add_argument("--out", default=None)
    wp.set_defaults(fn=_wallet_page)
    wv = sub.add_parser("wallet-viewer", help="build a 3D structural sketch of a one-sheet wallet record's folds (opens and closes)")
    wv.add_argument("wallet", help="a wallets/<id> folder")
    wv.add_argument("--out", default=None, help="default: wallets/<id>/viewer.html")
    wv.set_defaults(fn=_wallet_viewer)
    bs = sub.add_parser("build-site", help="build the archive app (one HTML file) from every record in wallets/")
    bs.add_argument("--wallets", default="wallets", help="the folder of wallet records")
    bs.add_argument("--out", default="site/index.html")
    bs.add_argument("--include-designs", action="store_true", help="also list generated test designs (status design)")
    bs.set_defaults(fn=_build_site)
    lr = sub.add_parser("lab-run", help="run the generic simulator tools and store their output for the archive app's Lab (about 2 minutes)")
    lr.add_argument("--out", default="lab/results.json")
    lr.add_argument("--only", nargs="+", default=None, help="a subset of tool ids, e.g. screen styles")
    lr.set_defaults(fn=_lab_run)
    ws = sub.add_parser("wallet-styles", help="run the fold-style comparison for wallets at their own thickness and main-fold radius")
    ws.add_argument("wallets", nargs="+", help="wallets/<id> folders")
    ws.set_defaults(fn=_wallet_styles)
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
