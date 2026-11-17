"""Per-wallet report: run a wallet record through the simulator and say what came out, how sure we are, and what is not modelled.

``build_report`` evaluates the record's folds (wrap model, loose and taut), repeats them for a few stack sizes to show how much the answer depends on the
number that is least certain, and goes through the 14 failure modes of ``docs/FAILURE_MODES.md``, marking each computed, flagged, not triggered or not
modelled. ``write_report`` saves the inputs, the numbers, a markdown report and two figures under ``wallets/<id>/sim/run-<hash>/`` so the run can be
reproduced from what is stored.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import __version__
from .fold_screen import STRAIN_SCREEN, outer_fibre_strain, screen
from .record import WalletRecord, measure_first
from .wallet_types import Contents, Fold, FoldOutcome, WalletPlan, WalletResult, evaluate_wallet


@dataclass
class Scenario:
    label: str
    stack_mm: float
    result: WalletResult


@dataclass
class Report:
    rec: WalletRecord
    base: WalletResult
    scenarios: list[Scenario]
    elasticity_stack: float             # d ln(strain) / d ln(stack), closed form
    elasticity_thickness: float
    modes: list[dict]
    meta: dict = field(default_factory=dict)
    sweeps: list[dict] = field(default_factory=list)      # custom wallets: each fold at the low / recorded / high end of its stack


def _ccx_version() -> str:
    exe = shutil.which("ccx")
    if not exe:
        return "not installed"
    out = " ".join(subprocess.run([exe, "-v"], capture_output=True, text=True).stdout.split())
    return "CalculiX ccx " + out.split("Version")[-1].strip() if "Version" in out else out[:40]


def input_hash(rec: WalletRecord, taut: float) -> str:
    h = hashlib.sha256()
    h.update((rec.path / "wallet.yaml").read_bytes())
    h.update(f"{__version__}|{taut}".encode())
    return h.hexdigest()[:8]


def _elasticities(rec: WalletRecord) -> tuple[float, float]:
    """Closed-form sensitivity of the textbook strain t/(2R+t), R = stack/2, to the stack and to the shell thickness."""
    def eps(stack, t):
        return outer_fibre_strain(t, stack / 2)
    s, t = rec.stack_at_spine_mm, rec.shell_t
    d = 0.05
    es = (np.log(eps(s * (1 + d), t)) - np.log(eps(s * (1 - d), t))) / (np.log(1 + d) - np.log(1 - d))
    et = (np.log(eps(s, t * (1 + d))) - np.log(eps(s, t * (1 - d)))) / (np.log(1 + d) - np.log(1 - d))
    return float(es), float(et)


def build_report(rec: WalletRecord, taut_n_per_mm: float = 0.1, sensitivity: bool = True) -> Report:
    params = rec.style_params()
    base = evaluate_wallet(rec.plan(), params, rec.layup, rec.spine, rec.corner_mm, taut_n_per_mm)
    scenarios: list[Scenario] = []
    if sensitivity and rec.wallet_type != "custom":
        s0 = rec.stack_at_spine_mm
        cases = [("stack -30 %", 0.7 * s0), ("stack +30 %", 1.3 * s0)]
        if rec.stack_override is None and rec.interior_leather_mm > 0:
            cases.insert(0, ("cards and other contents only (no interior leather)", rec.cards * rec.card_mm + rec.extra_mm))
        for label, stack in cases:
            plan = rec.plan(Contents(cards=0, extra_mm=stack))
            scenarios.append(Scenario(label, stack, evaluate_wallet(plan, params, rec.layup, rec.spine, rec.corner_mm, taut_n_per_mm)))
    sweeps = _fold_sweeps(rec, params, taut_n_per_mm) if (sensitivity and rec.wallet_type == "custom") else []
    es, et = _elasticities(rec)
    rep = Report(rec, base, scenarios, es, et, [], {"walletsim": __version__, "ccx": _ccx_version(), "taut_n_per_mm": taut_n_per_mm,
                                                    "hash": input_hash(rec, taut_n_per_mm)}, sweeps)
    rep.modes = failure_modes(rep)
    return rep


def _fold_sweeps(rec: WalletRecord, params, taut: float) -> list[dict]:
    """Custom wallets: every fold with a recorded range, evaluated at the low, recorded and high stack (one wallet evaluation, folds run in parallel)."""
    folds, tags = [], []
    for f in rec.custom_folds:
        if f.low_mm is None:
            continue
        for label, stack in (("low", f.low_mm), ("high", f.high_mm)):
            if abs(stack - f.stack_mm) < 1e-9:
                continue                                        # the recorded value is already in the base results
            folds.append(Fold(f"{f.name} @ {label}", stack, f.sense, f.cycles_per_use))
            tags.append((f.name, label, stack))
    out = []
    if folds:
        res = evaluate_wallet(WalletPlan("sweep", 0, tuple(folds), float("nan"), ""), params, rec.layup, "round", None, taut)
        out = [{"fold": n, "label": lab, "stack_mm": st, "outcome": o} for (n, lab, st), o in zip(tags, res.outcomes)]
    return out


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f} %"


def failure_modes(rep: Report) -> list[dict]:
    """The 14 failure modes of docs/FAILURE_MODES.md, as they stand for this wallet."""
    rec, base = rep.rec, rep.base
    spine = base.outcomes[0]
    crossing = [s for s in rec.seams if s.get("crosses_fold") and s.get("crosses_fold") != "unknown"]
    seams_unknown = any(s.get("crosses_fold") == "unknown" for s in rec.seams)
    skiv = [f.get("skived", {}).get("value") if isinstance(f.get("skived"), dict) else None for f in rec.folds]
    skived = any(v is True for v in skiv)
    skive_unknown = (not skived) and (not skiv or any(v in (None, "unknown") for v in skiv))
    edge = None
    for l in rec.raw.get("leather", []):
        if l.get("id") == "shell":
            edge = (l.get("edge") or {}).get("value")
    worst = base.worst
    modes = []

    def add(i, name, status, text):
        modes.append({"id": i, "name": name, "status": status, "text": text})

    if worst is None:
        add(1, "Grain crack at the hinge", "not run", "the fold could not be run: " + (spine.error or "see the log"))
    elif worst.taut is None:
        add(1, "Grain crack at the hinge", "computed (closed form only)",
            f"{worst.fold.name}: kinematic tension-face strain {_pct(worst.closed_form)} at an inside radius of {worst.radius_mm:.2f} mm (R/t = {worst.radius_mm / rec.shell_t:.2f}); {worst.note}. "
            "The grain relies on the finish and the leather's own extensibility; permanent set and cycles need fold-and-measure data.")
    else:
        sc = screen(rec.shell_t, worst.radius_mm)
        flags = "; ".join(sc.flags) if sc.flags else "within the screening rules"
        add(1, "Grain crack at the hinge", "computed",
            f"{worst.fold.name}: tension-face strain {_pct(worst.tension('loose'))} loose to {_pct(worst.tension('taut'))} taut "
            f"(closed-form limit {_pct(worst.closed_form)}), inside radius {worst.radius_mm:.2f} mm, R/t = {worst.radius_mm / rec.shell_t:.1f}"
            + ("; the model's leather bridges this stack, so the closed form is the number to read" if worst.bridges else "") + f"; {flags}. "
            "Cycles to crack need flex-test data.")
    add(2, "Permanent set", "not modelled", "needs a cyclic viscoplastic model and fold-and-measure data; it is the usual first visible sign of a worn hinge")
    cmp_ = (f"; at {worst.fold.name} the compression face is {_pct(worst.taut.peak_inner)} and the grain is {'in tension, not compression' if worst.fold.sense == 'out' else 'on the compression face'}"
            if worst and worst.taut else "")
    add(3, "Finish crazing or delamination", "not modelled",
        "a film-on-substrate model quoted in prior-research/reference/durability.md section 2b has a stiff finish buckling at 2-12 % compressive strain" + cmp_)
    if crossing:
        add(4, "Stress at stitch holes", "flagged", f"stitching ({', '.join(s['id'] for s in crossing)}) crosses or pins the fold(s): {', '.join(crossing[0]['crosses_fold'])}. "
            "Holes in a bend remove part of the section there. No local model yet")
    elif seams_unknown:
        names = ", ".join(str(s.get("id")) for s in rec.seams if s.get("crosses_fold") == "unknown")
        add(4, "Stress at stitch holes", "unknown", f"the record lists {names}, but whether it crosses or pins a fold is not recorded")
    else:
        add(4, "Stress at stitch holes", "not triggered", "no recorded stitch line crosses a fold")
    if skived:
        add(5, "Skive-line or thickness step", "flagged", "the fold is skived: a thickness step at the skive line")
    elif skive_unknown:
        add(5, "Skive-line or thickness step", "unknown", "whether the folds are skived is not recorded; a skive line is a stiffness step where cracks start")
    else:
        add(5, "Skive-line or thickness step", "not triggered", "the record says the folds are not skived; interior pieces step in height away from the fold, not across it")
    if edge in ("painted",):
        add(6, "Edge paint chipping", "flagged", "painted edge at a fold")
    elif edge in (None, "unknown"):
        add(6, "Edge paint chipping", "unknown", "the edge treatment is not recorded; record it (painted edges chip where they flex)")
    else:
        add(6, "Edge paint chipping", "not triggered", f"edge treatment: {edge}")
    pockets = rec.raw.get("pockets", [])
    add(7, "Pocket-mouth and corner abrasion", "not modelled",
        (f"{len(pockets)} pocket(s) recorded" if pockets else "no pockets recorded (the photographs show some; they are not described yet)")
        + "; needs the card-pull scenario (roadmap phase 4) and wear photos to calibrate")
    add(8, "Perforation tear line", "flagged" if crossing else ("unknown" if seams_unknown else "not triggered"),
        ((f"{sum(int(s.get('holes', {}).get('value', 0)) for s in crossing)} stitch holes in a line that crosses the fold" if sum(int(s.get('holes', {}).get('value', 0)) for s in crossing)
          else "holes through the fold(s) (their number is not recorded)") if crossing else "no recorded row of holes crosses a fold"))
    add(9, "Layer delamination", "not modelled", "layers are treated as perfectly bonded; the record does not say what is glued")
    add(10, "Cold embrittlement", "not modelled", "needs a cold flex test; no built-in factor")
    add(11, "Wet and salt flex", "not modelled", "needs a wet flex test")
    add(12, "Over-drying", "not modelled", "needs a measured material state (stiffness and strain to crack at a stated humidity)")
    add(13, "Long-term chemical ageing", "not modelled", "ageing enters only through measured aged states; none recorded")
    add(14, "Colour, patina, water spotting", "not modelled", "appearance only")
    return modes


# --------------------------------------------------------------------------------------------------------------------
# Figures

def _stack_polygon(job):
    R, hw = job.inside_radius_mm, job.wall_half_mm
    pts = [(-job.run_mm - 3.0, hw + R)]
    pts += [(0.0, hw + R)]
    th = np.linspace(0, job.half_angle, 40)
    pts += [(R * np.sin(a), hw + R * np.cos(a)) for a in th]
    pts += [(R, 0.0)]
    top = np.array(pts)
    mirror = top[::-1] * np.array([1, -1])
    return np.vstack([top, mirror])


def plot_fold(outcome: FoldOutcome, path: Path, title: str = "") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    r = outcome.taut or outcome.loose
    if r is None:
        return
    job = r.job
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.fill(*_stack_polygon(job).T, color="#d9d9d9", zorder=1, label="contents (rigid stack)")
    for sgn in (1, -1):
        o, i = r.outer_xz * [1, sgn], r.inner_xz * [1, sgn]
        ax.fill(np.r_[o[:, 0], i[::-1, 0]], np.r_[o[:, 1], i[::-1, 1]], color="#b08968", alpha=0.55, zorder=2, lw=0)
    seg = np.stack([r.outer_xz[:-1], r.outer_xz[1:]], axis=1)
    strain = r.outer_strain
    win = r.window()
    norm = plt.Normalize(0, max(0.05, float(np.nanmax(strain[win])) if win.any() else 0.2))
    for sgn in (1, -1):
        sg = seg * [1, sgn]
        lc = LineCollection(sg[win], cmap="inferno", norm=norm, linewidths=4, zorder=3)
        lc.set_array(strain[win])
        ax.add_collection(lc)
        ax.add_collection(LineCollection(sg[~win], colors="#999999", linewidths=2, zorder=3))
    cb = fig.colorbar(lc, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("tension-face strain (taut)")
    cb.ax.yaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    ax.set_aspect("equal")
    ax.autoscale()
    ax.set_xlabel("mm")
    ax.set_ylabel("mm")
    ax.set_title(title or f"{outcome.fold.name}\nclosed fold around {outcome.fold.stack_mm:.1f} mm (symmetric half mirrored)", fontsize=9, loc="left")
    if outcome.bridges:
        lo, hi = ax.get_ylim()
        ax.set_ylim(lo, hi + 0.3 * (hi - lo))
        ax.text(0.5, 0.97, f"THE MODEL'S LEATHER BRIDGES THIS STACK (stand-off {outcome.loose.standoff_mm:.1f} mm > radius {outcome.radius_mm:.1f} mm).\n"
                f"A real fold turns tighter, so read the closed form ({100 * outcome.closed_form:.0f} %), not the colours.",
                transform=ax.transAxes, ha="center", va="top", fontsize=7.5, color="#a1341d", bbox=dict(fc="white", ec="#a1341d", lw=0.8, alpha=0.9))
    ax.text(0.01, 0.01, "grey = excluded near the constraints. Lift-off before the bend is the model's result with little pull on the panel; check it with an edge-on photo.\n"
            "model: plane strain, isotropic, perfectly bonded", transform=ax.transAxes, fontsize=6.5, color="#555", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_strain(outcome: FoldOutcome, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for label, res, style in (("tension face, taut", outcome.taut, "-"), ("tension face, loose", outcome.loose, "--")):
        if res is not None:
            ax.plot(res.u, 100 * res.outer_strain, style, color="#a1341d", label=label)
    if outcome.taut is not None:
        ax.plot(outcome.taut.u, 100 * outcome.taut.inner_strain, "-", color="#1d5ba1", label="compression face, taut")
        w = outcome.taut.window()
        ax.axvspan(outcome.taut.u[~w].min() if (~w).any() else 0, outcome.taut.u[w].min() if w.any() else 0, color="#cccccc", alpha=0.5, lw=0)
    if outcome.closed_form is not None:
        ax.axhline(100 * outcome.closed_form, color="#555", ls=":", label="closed-form limit (taut)")
    ax.axhline(100 * STRAIN_SCREEN, color="#888", lw=0.8, ls="-.", label="20 % screening threshold")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("position along the strip from the fold centre (mm; negative = toward the panel)")
    ax.set_ylabel("engineering strain (%)")
    ax.set_title(f"{outcome.fold.name}: strain along the strip", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# --------------------------------------------------------------------------------------------------------------------
# Writing

def _row(o: FoldOutcome, t: float) -> str:
    if o.taut is None and o.note:
        return (f"| {o.fold.name} | {o.fold.sense} | {o.fold.stack_mm:.2f} | {o.radius_mm:.2f} ({o.radius_mm / t:.2f}) | closed form only: **{_pct(o.closed_form)}** (not run: {o.note.split(':')[0]}) | | {_pct(o.closed_form)} | |")
    mark = " (bridges)" if o.bridges else ""
    return (f"| {o.fold.name} | {o.fold.sense} | {o.fold.stack_mm:.2f} | {o.radius_mm:.2f} ({o.radius_mm / t:.1f}) | {_pct(o.tension('loose'))}{mark} | "
            f"{_pct(o.tension('taut'))}{mark} | {_pct(o.closed_form)} | {_pct(o.grain('taut'))} |")


BANNERS = {
    "design": "> **This record is a design, not a measured wallet.** Numbers tagged `design` are what the pattern asks for and `assumed` are stand-ins; "
              "the physical wallet will differ. Read the results as what the model says *for this specification*, and replace the inputs as they are measured.",
    "photos-only": "> **This record comes from a retailer's text and product photographs, not from a wallet in hand.** Nothing is measured. Every radius and stack is an inference "
                   "or an assumption, shown with its range. The results say what the model gives for those inputs, not what this wallet does.",
}


def format_markdown(rep: Report, figures: dict[str, list[str]] | None = None) -> str:
    rec, base = rep.rec, rep.base
    t = rec.shell_t
    custom = rec.wallet_type == "custom"
    counts = rec.provenance_counts()
    L = [f"# {rec.name}: simulation report", ""]
    if rec.status in BANNERS:
        L += [BANNERS[rec.status], ""]
    what = (f"custom, {len(rec.custom_folds)} folds listed in the record, {rec.layup} layup" if custom else f"{rec.wallet_type}, {rec.spine} spine, {rec.layup} layup, {rec.cards:g} cards")
    L += [f"- wallet: `{rec.id}` ({what}); status: {rec.status}",
          *([f"- usage: used. {rec.raw['usage'].get('condition', '')}"] if isinstance(rec.raw.get("usage"), dict) and rec.raw["usage"].get("used") else []),
          "- inputs by source: " + ", ".join(f"{n} {k}" for k, n in counts.items() if n) + f" (of {len(rec.inputs)})",
          f"- model: walletsim {rep.meta['walletsim']}, {rep.meta['ccx']}, plane-strain neo-Hookean fold, pull for 'taut' {rep.meta['taut_n_per_mm']} N per mm; run `{rep.meta['hash']}`", ""]
    L += ["## Inputs and where each came from", "", "| input | value | source | what it changes | note |", "|---|---|---|---|---|"]
    for i in rec.inputs:
        L.append(f"| {i.name} | {i.value} {i.unit} | **{i.source}** | {i.feeds} | {i.ref[:110]} |")
    if custom:
        closed = base.plan.closed_thickness_mm
        L += ["", "Folds modelled (stack = what each fold wraps in the closed wallet; the range is what the sweep below covers). Closed thickness: "
              + ("not recorded" if closed != closed else f"{closed:.1f} mm") + ".", "",
              "| fold | grain | stack [mm] | range [mm] | source |", "|---|---|---|---|---|"]
        for f in rec.custom_folds:
            rng = f"{f.low_mm:g} to {f.high_mm:g}" if f.low_mm is not None else "none given"
            L.append(f"| {f.name} | {f.sense} | {f.stack_mm:g} | {rng} | **{f.source}** |")
        L.append("")
    else:
        L += ["", f"Stack the spine wraps: **{rec.stack_at_spine_mm:.2f} mm** (" + (f"recorded, source {rec.stack_source}" if rec.stack_override is not None else
              f"{rec.cards:g} cards x {rec.card_mm:g} mm + {rec.interior_layers:g} interior leather layers x {rec.slot_t:g} mm" + (f" + {rec.extra_mm:g} mm other" if rec.extra_mm else "") +
              ", derived, source assumed") + f"). Closed wallet at the spine: {base.plan.closed_thickness_mm:.1f} mm.", ""]
    L += ["## The fold(s)", "", "| fold | grain | stack [mm] | inside radius [mm] (R/t) | tension face, loose | taut | closed-form limit | grain face (taut) |", "|---|---|---|---|---|---|---|---|"]
    for o in base.outcomes:
        if o.taut is not None or o.note:
            L.append(_row(o, t))
        else:
            L.append(f"| {o.fold.name} | {o.fold.sense} | {o.fold.stack_mm:.2f} | | not run: {o.error[:80]} | | | |")
    L += ["", "loose = the leather lies on the stack with no pull; taut = a pull of "
          f"{rep.meta['taut_n_per_mm']} N per mm on the panel; limit = the leather follows the stack exactly (closed form). A real wallet is somewhere between loose and the limit; "
          "an edge-on photo of the closed spine would show which.", "",
          "In the figure the strip lifts off the stack before the bend. That is the model's result for leather with little or no pull on the panel; whether a real closed wallet "
          "does this is exactly what that edge-on photo would show.", ""]
    if any(o.bridges for o in base.outcomes):
        L += ["**bridges** = with no pull the elastic model's leather stands further off the stack than the stack's radius, so it does not follow the stack: the FEM then understates the strain "
              "of leather that is pulled onto it (by a thread tie, by pressing or by the closed panels). Those folds are ranked by the closed form, shown next to the FEM numbers.", ""]
    if any(o.note for o in base.outcomes):
        L += ["A fold marked *closed form only* has an inside radius below half a leather thickness. The elastic model shows leather like that bridging the gap instead of turning "
              "round it (tried at R/t 0.13 to 0.25 in the edge-turn trial: 10 to 22 % against 41 to 80 % kinematic), so no FEM number is given. Strains like these are not elastic: such a fold works by "
              "permanent set, thinning and the thread ties, and this model has none of those, so it cannot say whether the fold survives.", ""]
    for fig in (figures or {}).get("fold", []):
        L.append(f"![fold]({fig})")
    for fig in (figures or {}).get("strain", []):
        L.append(f"![strain]({fig})")
    if rep.sweeps:
        L += ["", "## How sure are we? Each fold across the range of its stack", "",
              "The stacks are inferences or assumptions, so each fold is run at the low, recorded and high end of its range.", "",
              "| fold | end of range | stack [mm] | inside radius (R/t) | tension face, loose | taut | closed form |", "|---|---|---|---|---|---|---|"]
        rows = []
        for f in rec.custom_folds:
            if f.low_mm is None:
                continue
            rec_o = next((o for o in base.outcomes if o.fold.name == f.name), None)
            rows += [sw for sw in rep.sweeps if sw["fold"] == f.name and sw["label"] == "low"]
            if rec_o is not None:
                rows.append({"fold": f.name, "label": "recorded", "stack_mm": f.stack_mm, "outcome": rec_o})
            rows += [sw for sw in rep.sweeps if sw["fold"] == f.name and sw["label"] == "high"]
        for sw in rows:
            o = sw["outcome"]
            if o.taut is not None:
                mark = " (bridges)" if o.bridges else ""
                L.append(f"| {sw['fold']} | {sw['label']} | {sw['stack_mm']:g} | {o.radius_mm:.2f} ({o.radius_mm / t:.2f}) | {_pct(o.tension('loose'))}{mark} | {_pct(o.tension('taut'))}{mark} | {_pct(o.closed_form)} |")
            else:
                L.append(f"| {sw['fold']} | {sw['label']} | {sw['stack_mm']:g} | {o.radius_mm:.2f} ({o.radius_mm / t:.2f}) | closed form only | | {_pct(o.closed_form)} |")
    if rep.scenarios:
        L += ["", "## How sure are we? The stack is the least certain number", "",
              f"A 10 % larger stack lowers the textbook strain by about {abs(rep.elasticity_stack) * 10:.0f} %, and a 10 % thicker shell raises it by about "
              f"{abs(rep.elasticity_thickness) * 10:.0f} % (closed form). The stack is the number the design pins down least, and it is the one a caliper can settle.", "",
              "| scenario | stack [mm] | R/t | tension face, loose | taut | limit |", "|---|---|---|---|---|---|"]
        for label, res in [("as recorded", base)] + [(s.label, s.result) for s in rep.scenarios]:
            o = res.outcomes[0]
            if o.taut is None:
                L.append(f"| {label} | {o.fold.stack_mm:.2f} | | not run | | |")
                continue
            L.append(f"| {label} | {o.fold.stack_mm:.2f} | {o.radius_mm / t:.1f} | {_pct(o.tension('loose'))} | {_pct(o.tension('taut'))} | {_pct(o.closed_form)} |")
    L += ["", "## Failure modes, in the order of `docs/FAILURE_MODES.md`", "", "| # | mode | status | for this wallet |", "|---|---|---|---|"]
    for m in rep.modes:
        L.append(f"| {m['id']} | {m['name']} | **{m['status']}** | {m['text']} |")
    L += ["", "## What to measure first", ""]
    for n, (name, how) in enumerate(measure_first(rec), 1):
        L.append(f"{n}. **{name}**: {how}")
    L += ["", "## Reproduce", "", f"`walletsim wallet-report wallets/{rec.id}` with walletsim {rep.meta['walletsim']}. The exact `wallet.yaml` used is stored next to this report as `inputs.yaml`; "
          "every number above comes from `result.json`.", ""]
    return "\n".join(L)


def _json(rep: Report) -> dict:
    def fo(o: FoldOutcome):
        return {"fold": o.fold.name, "sense": o.fold.sense, "stack_mm": o.fold.stack_mm, "inside_radius_mm": o.radius_mm,
                "tension_loose": o.tension("loose"), "tension_taut": o.tension("taut"), "closed_form": o.closed_form,
                "grain_taut": o.grain("taut"), "note": o.note, "moment_taut_n_mm_per_mm": None if o.taut is None else o.taut.moment_n_mm,
                "standoff_loose_mm": None if o.loose is None else o.loose.standoff_mm, "error": o.error}
    return {"id": rep.rec.id, "status": rep.rec.status, "meta": rep.meta,
            "inputs": [{"name": i.name, "value": i.value, "unit": i.unit, "source": i.source, "ref": i.ref} for i in rep.rec.inputs],
            "stack_at_spine_mm": rep.rec.stack_at_spine_mm, "folds": [fo(o) for o in rep.base.outcomes],
            "scenarios": [{"label": s.label, "stack_mm": s.stack_mm, "folds": [fo(o) for o in s.result.outcomes]} for s in rep.scenarios],
            "sweeps": [{**fo(sw["outcome"]), "fold": sw["fold"], "end": sw["label"], "stack_mm": sw["stack_mm"]} for sw in rep.sweeps],
            "elasticity_stack": rep.elasticity_stack, "elasticity_thickness": rep.elasticity_thickness, "failure_modes": rep.modes}


def write_report(rep: Report, outdir: str | Path | None = None, figures: bool = True) -> Path:
    out = Path(outdir) if outdir else rep.rec.path / "sim" / f"run-{rep.meta['hash']}"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(rep.rec.path / "wallet.yaml", out / "inputs.yaml")
    figs: dict[str, list[str]] = {"fold": [], "strain": []}
    if figures:
        for k, o in enumerate(rep.base.outcomes):
            if o.taut is None:
                continue
            tag = f"fold{k + 1}"
            plot_fold(o, out / f"{tag}_shape.png")
            plot_strain(o, out / f"{tag}_strain.png")
            figs["fold"].append(f"{tag}_shape.png")
            figs["strain"].append(f"{tag}_strain.png")
    (out / "result.json").write_text(json.dumps(_json(rep), indent=1, default=float))
    (out / "report.md").write_text(format_markdown(rep, figs))
    return out
