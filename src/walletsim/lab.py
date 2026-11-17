"""The simulator's tools, stored: results the archive app shows in its Lab and on each wallet's Behaviour tab.

The app is one static file, so it cannot run CalculiX. Instead these commands run here and write their results to disk; ``build-site`` embeds them.

* ``run_lab``  runs the generic tools exactly as a person would at the command line (``screen``, ``validate-fem``, ``sweep``, ``fold-styles``, ``gusset``, ``box-spine``,
  ``edge-turn``, ``wallet-types``) and stores each command, its verbatim output, how long it took and the walletsim version, in ``lab/results.json``.
* ``wallet_styles`` runs the fold-style comparison for one wallet at its own sheet thickness and the inside radius of its main fold, and stores the rows in
  ``wallets/<id>/sim/styles.json``.

Nothing here is estimated: a stored result is what the command printed, or the numbers the solver returned, and the app labels it with the command that made it.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from . import __version__

LAB_COMMANDS = [
    {"id": "screen", "title": "Strain screen", "args": ["screen", "--t", "1.0", "--radius", "2.0"], "what": "The level-0 closed form, eps = t / (2R + t), with screening flags. No solver."},
    {"id": "validate", "title": "FEM backend check", "args": ["validate-fem"], "what": "A strip bent 180 degrees in CalculiX against the closed form: the check that the solver can be trusted for this."},
    {"id": "sweep", "title": "Thickness sweep", "args": ["sweep"], "what": "How strain and bending moment change with leather thickness at a fixed fold radius."},
    {"id": "styles", "title": "Fold styles", "args": ["fold-styles"], "what": "Plain, skived, lined, skived + lined, hinged, turned-edge and bound-edge folds, free and wrapped around a 5-card stack."},
    {"id": "gusset", "title": "Gussets", "args": ["gusset"], "what": "V, S and W pleats at several openings: the strain follows the fold angle."},
    {"id": "box", "title": "Box spine", "args": ["box-spine"], "what": "A box-shaped spine with a flat wall, compared with the round spine."},
    {"id": "edge", "title": "Turned edge", "args": ["edge-turn"], "what": "The 180 degree turn of a turned edge for several skive depths (closed form)."},
    {"id": "types", "title": "Wallet types", "args": ["wallet-types"], "what": "Bifold, trifold and z-fold at the same contents: the stack each fold wraps and which fold wears first."},
]


def run_lab(out: str | Path = "lab/results.json", only: list[str] | None = None) -> Path:
    results = []
    for c in LAB_COMMANDS:
        if only and c["id"] not in only:
            continue
        t0 = time.time()
        proc = subprocess.run([sys.executable, "-m", "walletsim.cli", *c["args"]], capture_output=True, text=True, timeout=900)
        results.append({**c, "command": "walletsim " + " ".join(c["args"]), "seconds": round(time.time() - t0, 1), "returncode": proc.returncode,
                        "output": (proc.stdout if proc.returncode == 0 else proc.stdout + proc.stderr).rstrip()})
        print(f"{c['id']:9s} {results[-1]['seconds']:6.1f} s  rc={proc.returncode}")
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"walletsim": __version__, "results": results}, indent=1), encoding="utf-8")
    return path


def wallet_styles(wallet_dir: str | Path, taut_n_per_mm: float = 0.1) -> Path:
    """The fold-style comparison for one wallet, at its sheet thickness and the inside radius of its first (main) fold."""
    from .fold_styles import StyleParams, compare_styles
    from .record import load_wallet
    rec = load_wallet(wallet_dir)
    if rec.wallet_type != "custom":
        raise ValueError("only custom (one-sheet) records are supported so far")
    main = rec.custom_folds[0]
    radius = main.stack_mm / 2
    p = StyleParams(t=float(rec.shell_t), E=float(rec.youngs_modulus_mpa))
    res = compare_styles(p, radius, taut_n_per_mm=taut_n_per_mm)
    ref = next(r for r in res if r.name == "plain")
    rows = [{"style": r.name, "free_tension": r.free.peak_outer, "free_compression": r.free.peak_inner, "wrap_loose": r.wrap_loose.peak_outer, "wrap_taut": r.wrap_taut.peak_outer,
             "limit": r.taut_closed_form, "standoff_mm": r.wrap_loose.standoff_mm, "moment_taut": r.wrap_taut.moment_n_mm, "moment_free": r.free.moment_n_mm,
             "centre_share": r.centre_share(), "vs_plain_taut": r.wrap_taut.peak_outer / ref.wrap_taut.peak_outer if ref.wrap_taut.peak_outer else None} for r in res]
    path = Path(wallet_dir) / "sim" / "styles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"walletsim": __version__, "fold": main.name, "stack_mm": main.stack_mm, "inside_radius_mm": radius, "t_mm": float(rec.shell_t),
                                "E_mpa": float(rec.youngs_modulus_mpa), "taut_n_per_mm": taut_n_per_mm, "source": main.source, "rows": rows}, indent=1), encoding="utf-8")
    return path
