"""Command line entry point:  walletsim screen | validate-fem | fit-law"""
from __future__ import annotations

import argparse
import csv
import sys

from . import __version__
from .damage import fit_law
from .fem.bending import BendingJob, FemUnavailable, run_bending
from .fold_screen import screen


def _screen(a: argparse.Namespace) -> int:
    print(screen(a.t, a.radius))
    return 0


def _validate_fem(a: argparse.Namespace) -> int:
    try:
        res = run_bending(BendingJob(thickness_mm=a.t, angle_deg=a.angle))
    except FemUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"strip bent {a.angle:g} deg, t={a.t:g} mm: inside radius {res.inside_radius_mm:.2f} mm")
    print(f"  analytic outer-fibre strain  {100 * res.analytic_strain:.2f} %")
    print(f"  CalculiX outer-fibre strain  {100 * res.fem_max_strain:.2f} %   ({100 * res.relative_error:+.1f} % vs analytic, "
          f"{res.runtime_s:.1f} s, {res.n_integration_points} integration points)")
    return 0 if abs(res.relative_error) < 0.05 else 1


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
    f = sub.add_parser("fit-law", help="fit a cycles-to-crack law to your flex-test data (csv: strain,cycles)")
    f.add_argument("csv")
    f.add_argument("--at", type=float, nargs="*", help="strains (fraction) to predict at")
    f.set_defaults(fn=_fit_law)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
