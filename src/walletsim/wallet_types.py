"""Overall wallet fold types: which folds a wallet has, what each one wraps, and which wears first.

A wallet type is a set of FOLDS. For a given load of contents, each fold wraps a different stack in the closed wallet, and that
stack sets the fold's inside radius. This module fixes the stack for each fold from the type's topology, runs each fold through the
wrap model of ``fem/fold.py`` (loose and lightly taut, as in ``fold_styles``), and ranks the folds with ``damage.rank_locations``.

Types (all panels are the same layup; contents are cards plus any extra thickness):

bifold     two panels, one spine. The spine wraps ALL the contents. (A long wallet, a passport cover, a card holder with one fold
           and a slim sleeve are the same fold with different panels and contents.)
trifold    letter fold: panel R folds onto M around contents C1, then L folds over the pack around contents C2. The inner fold wraps
           C1; the outer fold wraps C1 + C2 + one folded-in panel, so its radius is larger. Both folds have the grain outside.
z-fold     accordion / concertina of n panels, n-1 folds that alternate sense (grain out, grain in, ...). Each fold wraps only its own
           compartment, an equal share of the contents.

What this does NOT do: it does not model how the folds interact (the folds are evaluated one at a time with their own stack), the
pockets or card-slot edges, the 3D shape of a wallet, or partial opening (a fold's amplitude is closed -> flat). Cycles per use are an
assumption (every fold opens and closes once per use) that you can override.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .damage import Exposure, rank_locations
from .fem.fold import FoldJob, FoldResult, analytic_wrap, run_fold
from .fold_styles import ID1_CARD_MM, STYLES, StyleParams


@dataclass(frozen=True)
class Contents:
    cards: float = 8.0
    extra_mm: float = 0.0               # notes, receipts, anything else: total thickness
    slot_leather_mm: float = 0.0        # leather of the card pocket per card (an assumption; 0 = ignore it)
    card_mm: float = ID1_CARD_MM

    @property
    def thickness_mm(self) -> float:
        return self.cards * (self.card_mm + self.slot_leather_mm) + self.extra_mm


@dataclass(frozen=True)
class Fold:
    name: str
    stack_mm: float                     # thickness of everything this fold wraps in the closed wallet
    sense: str                          # "out": grain on the outside of the fold; "in": grain inside
    cycles_per_use: float = 1.0

    @property
    def half_mm(self) -> float:
        return self.stack_mm / 2


@dataclass(frozen=True)
class WalletPlan:
    type_name: str
    panels: int
    folds: tuple[Fold, ...]
    closed_thickness_mm: float          # panels + contents in the closed wallet, the thickness of the pack
    description: str


def panel_thickness(params: StyleParams, layup: str) -> float:
    """Thickness of the layup away from the fold (the panel)."""
    return sum(l.thickness(-1000.0) for l in STYLES[layup][0](params))


def bifold(c: Contents, t_panel: float, **_) -> WalletPlan:
    s = c.thickness_mm
    return WalletPlan("bifold", 2, (Fold("spine", s, "out"),), s + 2 * t_panel,
                      "two panels, one spine that wraps all the contents")


def trifold(c: Contents, t_panel: float, split: float = 0.5, **_) -> WalletPlan:
    if not 0.0 < split < 1.0:
        raise ValueError("split must be strictly between 0 and 1")
    s = c.thickness_mm
    c1, c2 = s * split, s * (1 - split)
    return WalletPlan("trifold", 3,
                      (Fold("inner fold (M|R)", c1, "out"), Fold("outer fold (L|M)", c1 + c2 + t_panel, "out")),
                      s + 3 * t_panel,
                      f"letter fold: the inner fold wraps {100 * split:.0f} % of the contents; the outer fold wraps all of them plus one folded-in panel")


def zfold(c: Contents, t_panel: float, panels: int = 3, **_) -> WalletPlan:
    if panels < 3:
        raise ValueError("a z-fold needs at least 3 panels (use bifold for 2)")
    s = c.thickness_mm
    share = s / (panels - 1)
    folds = tuple(Fold(f"fold {i + 1} (grain {'out' if i % 2 == 0 else 'in'})", share, "out" if i % 2 == 0 else "in")
                  for i in range(panels - 1))
    return WalletPlan(f"z-fold ({panels} panels)", panels, folds, s + panels * t_panel,
                      f"accordion of {panels} panels: {panels - 1} alternating folds, each wrapping an equal share of the contents")


WALLET_TYPES = {"bifold": bifold, "trifold": trifold, "z-fold": zfold}
ALIASES = {
    "long wallet / continental": "bifold",
    "passport cover": "bifold (the passport counts as contents: --extra-mm)",
    "card holder with one fold": "bifold",
    "slim sleeve": "bifold",
    "vertical or book-style bifold": "bifold",
    "concertina card case": "z-fold",
}


def plan_for(type_name: str, contents: Contents, t_panel: float, **kw) -> WalletPlan:
    if type_name not in WALLET_TYPES:
        raise KeyError(f"unknown wallet type {type_name!r}; known: {sorted(WALLET_TYPES)}")
    return WALLET_TYPES[type_name](contents, t_panel, **kw)


# --------------------------------------------------------------------------------------------------------------------

@dataclass
class FoldOutcome:
    fold: Fold
    radius_mm: float
    wall_half_mm: float
    loose: FoldResult | None
    taut: FoldResult | None
    closed_form: float | None
    error: str = ""
    note: str = ""                      # e.g. "closed form only": the fold was not run (R/t below 0.5: the elastic model would show the leather bridging the stack)

    @property
    def bridges(self) -> bool:
        """The elastic leather does not follow the stack: with no pull it stands further off the stack than the stack's radius (loose case)."""
        return self.loose is not None and self.closed_form is not None and self.loose.standoff_mm > self.radius_mm

    @property
    def screen_strain(self) -> float | None:
        """The strain used to rank and flag this fold: the taut FEM value; the closed form when the fold was not run or when the model's leather
        bridges the stack (then the FEM understates the strain of a leather that something pulls onto the stack, such as a thread tie)."""
        t = self.tension("taut")
        if t is None or self.bridges:
            return self.closed_form if self.closed_form is not None else t
        return t

    def tension(self, which: str = "taut") -> float | None:
        r = self.taut if which == "taut" else self.loose
        return None if r is None else r.peak_outer

    def grain(self, which: str = "taut") -> float | None:
        """Strain on the grain face: the tension face for a grain-out fold, the compression face for a grain-in fold."""
        r = self.taut if which == "taut" else self.loose
        if r is None:
            return None
        return r.peak_outer if self.fold.sense == "out" else r.peak_inner


@dataclass
class WalletResult:
    plan: WalletPlan
    layup: str
    spine: str
    outcomes: list[FoldOutcome]

    def exposures(self, basis: str = "tension") -> dict[str, Exposure]:
        """Load seen per use by each fold. basis 'tension': strain on the tension face of the whole layup (the flesh or back face for
        a grain-in fold); 'grain': tension on the grain face only, so a grain-in fold, whose grain is compressed, counts as zero."""
        out = {}
        for o in self.outcomes:
            if o.screen_strain is None:
                continue
            if o.tension("taut") is None:                       # closed form only: the tension face of a grain-out fold is the grain
                e = o.screen_strain if (basis == "tension" or o.fold.sense == "out") else 0.0
            else:
                e = o.tension("taut") if basis == "tension" else max(0.0, o.grain("taut") or 0.0)
            out[o.fold.name] = Exposure(e, o.fold.cycles_per_use)
        return out

    def wears_first(self, basis: str = "tension", tol: float = 0.005) -> dict:
        """Which fold has the highest damage rate. Folds within ``tol`` (absolute strain) of the top and with the same cycles per use are
        reported as tied: the solver's last digit must not decide. Uses damage.rank_locations over m = 3 to 12."""
        exp = self.exposures(basis)
        if not exp:
            return {"first": [], "stable": True, "tied": False, "rankings": {}}
        rk = rank_locations(exp) if len(exp) >= 2 else {"stable": True, "order": list(exp), "rankings": {}}
        if len({e.cycles_per_use for e in exp.values()}) == 1:
            top = max(e.strain for e in exp.values())
            first = [n for n, e in exp.items() if e.strain >= top - tol] if top > 0 else []
            return {"first": first, "stable": True, "tied": len(first) > 1, "rankings": rk.get("rankings", {})}
        order = rk["order"] or rk["rankings"][3.0]
        return {"first": [order[0]], "stable": rk["stable"], "tied": False, "rankings": rk["rankings"]}

    @property
    def worst(self) -> FoldOutcome | None:
        ok = [o for o in self.outcomes if o.screen_strain is not None]
        return max(ok, key=lambda o: o.screen_strain) if ok else None

    @property
    def total_closing_moment(self) -> float | None:
        """Sum of the moments at the fold centres, N mm per mm of width (round spines only)."""
        if self.spine != "round" or any(o.taut is None for o in self.outcomes):
            return None
        return sum(o.taut.moment_n_mm for o in self.outcomes)


def _job(layers, fold: Fold, spine: str, corner_mm: float | None, tension: float):
    from .fem.fold import FoldJob as FJ
    use = tuple(reversed(layers)) if fold.sense == "in" else layers
    flat = "inner" if fold.sense == "in" else "outer"
    half = fold.half_mm
    if spine == "box":
        rc = min(corner_mm if corner_mm is not None else 1.0, half)
        wall = half - rc
    else:
        rc, wall = half, 0.0
    probe = FJ(use, "wrap", inside_radius_mm=rc, wall_half_mm=wall, flat_face=flat)
    dx = min(0.5, max(0.08, probe.bend_mm / 14))
    return FJ(use, "wrap", inside_radius_mm=rc, wall_half_mm=wall, flat_face=flat, dx_mm=dx, tension_n_per_mm=tension), rc, wall


def evaluate_wallet(plan: WalletPlan, params: StyleParams | None = None, layup: str = "plain", spine: str = "round",
                    corner_mm: float | None = None, taut_n_per_mm: float = 0.1, workers: int = 4,
                    cycles: dict[str, float] | None = None, min_r_over_t: float = 0.5) -> WalletResult:
    if layup not in STYLES:
        raise KeyError(f"unknown layup {layup!r}; known: {sorted(STYLES)}")
    if spine not in ("round", "box"):
        raise ValueError("spine must be 'round' or 'box'")
    p = params or StyleParams()
    layers = STYLES[layup][0](p)
    if cycles:
        unknown = set(cycles) - {f.name for f in plan.folds}
        if unknown:
            raise KeyError(f"no such fold(s) {sorted(unknown)}; folds of this wallet: {[f.name for f in plan.folds]}")
        plan = WalletPlan(plan.type_name, plan.panels, tuple(Fold(f.name, f.stack_mm, f.sense, cycles.get(f.name, f.cycles_per_use)) for f in plan.folds),
                          plan.closed_thickness_mm, plan.description)
    from .fold_screen import outer_fibre_strain
    t_layup = sum(l.thickness(0.0) for l in layers)
    specs: dict[tuple, FoldJob] = {}
    plan_rows = []
    skipped: dict[str, FoldOutcome] = {}
    for f in plan.folds:
        if spine == "round" and f.half_mm < min_r_over_t * t_layup:
            # R/t below 0.5: the elastic model shows the leather bridging the stack (tried at R/t 0.13-0.25 in the edge-turn trial), so only the closed form is given
            skipped[f.name] = FoldOutcome(f, f.half_mm, 0.0, None, None, outer_fibre_strain(t_layup, f.half_mm),
                                          note=f"R/t = {f.half_mm / t_layup:.2f} < {min_r_over_t:g}: closed form only; the elastic model cannot say whether the leather survives")
            continue
        row = {}
        for label, tension in (("loose", 0.0), ("taut", taut_n_per_mm)):
            job, rc, wall = _job(layers, f, spine, corner_mm, tension)
            key = (f.sense, round(rc, 4), round(wall, 4), tension)
            specs.setdefault(key, job)
            row[label] = key
        plan_rows.append((f, rc, wall, row))

    def safe(job):
        try:
            return run_fold(job), ""
        except (RuntimeError, ValueError) as exc:
            return None, str(exc).strip().splitlines()[0]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        done = dict(zip(specs, pool.map(safe, specs.values())))
    outcomes = []
    by_name = {f.name: (f, rc, wall, row) for f, rc, wall, row in plan_rows}
    for f in plan.folds:
        if f.name in skipped:
            outcomes.append(skipped[f.name])
            continue
        f, rc, wall, row = by_name[f.name]
        loose, e1 = done[row["loose"]]
        taut, e2 = done[row["taut"]]
        cf = None
        if taut is not None:
            try:
                w = taut._checked_window()
                cf = max(analytic_wrap(taut.job, u)["outer"] for u in taut.u[w])
            except ValueError:
                cf = None
        outcomes.append(FoldOutcome(f, rc, wall, loose, taut, cf, e1 or e2))
    return WalletResult(plan, layup, spine, outcomes)


def compare_wallet_types(types: list[tuple[str, dict]], contents: Contents, params: StyleParams | None = None, layup: str = "plain",
                         spine: str = "round", corner_mm: float | None = None, taut_n_per_mm: float = 0.1) -> list[WalletResult]:
    p = params or StyleParams()
    t_panel = panel_thickness(p, layup)
    return [evaluate_wallet(plan_for(name, contents, t_panel, **kw), p, layup, spine, corner_mm, taut_n_per_mm) for name, kw in types]


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{100 * x:5.1f}%"


def format_wallet_report(results: list[WalletResult], contents: Contents, params: StyleParams) -> str:
    from .fold_screen import STRAIN_SCREEN
    L = [f"overall wallet fold types: {contents.cards:g} cards" + (f" + {contents.extra_mm:g} mm other" if contents.extra_mm else "")
         + f" = {contents.thickness_mm:.2f} mm of contents (pocket leather per card: {contents.slot_leather_mm:g} mm). "
         f"{results[0].layup} layup, shell {params.t:g} mm, E = {params.E:g} MPa, {results[0].spine} spine.",
         "Every fold is run on its own with the stack it wraps in the closed wallet (wrap, loose and taut as in `fold-styles`). Cycles per use are an assumption: 1 each.", ""]
    for r in results:
        L += [f"{r.plan.type_name}: {r.plan.description}; closed thickness {r.plan.closed_thickness_mm:.1f} mm",
              f"  {'fold':22s} {'grain':>5s} {'stack':>7s} {'radius':>7s} {'R/t':>5s} | {'tension face':^22s} | {'grain face':>10s} {'moment':>7s}",
              f"  {'':22s} {'':>5s} {'[mm]':>7s} {'[mm]':>7s} {'':>5s} | {'loose':>7s} {'taut':>7s} {'limit':>7s} | {'(taut)':>10s} {'taut':>7s}"]
        for o in r.outcomes:
            if o.note and o.taut is None:
                L.append(f"  {o.fold.name:22s} {o.fold.sense:>5s} {o.fold.stack_mm:7.2f} {o.radius_mm:7.2f} {o.radius_mm / params.t:5.2f} | closed form only: {_pct(o.closed_form)} (R/t < 0.5, not run)")
                continue
            if o.error and o.taut is None:
                L.append(f"  {o.fold.name:22s} {o.fold.sense:>5s} {o.fold.stack_mm:7.2f} {o.radius_mm:7.2f} {o.radius_mm / params.t:5.2f} | not run: {o.error[:70]}")
                continue
            mom = f"{o.taut.moment_n_mm:7.2f}" if r.spine == "round" else "    n/a"
            if o.bridges:
                mom += "  (bridges: the elastic leather stands off the stack by more than its radius; the closed form is used to rank)"
            L.append(f"  {o.fold.name:22s} {o.fold.sense:>5s} {o.fold.stack_mm:7.2f} {o.radius_mm:7.2f} {o.radius_mm / params.t:5.2f} | "
                     f"{_pct(o.tension('loose')):>7s} {_pct(o.tension('taut')):>7s} {_pct(o.closed_form):>7s} | {_pct(o.grain('taut')):>10s} {mom}")
        if len(r.outcomes) > 1:
            for basis, label in (("tension", "highest tension-face strain"), ("grain", "highest GRAIN-face tension (finish cracking)")):
                w = r.wears_first(basis)
                if not w["first"]:
                    L.append(f"  {label}: none (no grain-face tension)")
                elif not w["stable"]:
                    L.append(f"  {label}: {w['first'][0]}, but the order changes with the exponent m: " + str(w["rankings"]))
                else:
                    L.append(f"  {label}: " + (" and ".join(w["first"]) + (" (tied within 0.5 point)" if w["tied"] else "")))
        L.append("")
    ref = next((r for r in results if r.plan.type_name == "bifold"), results[0])
    L += [f"SUMMARY (same contents; worst fold = highest taut tension-face strain; damage rate = (strain / {ref.plan.type_name}'s)^m, m = 3 to 12)",
          f"  {'type':18s} {'folds':>5s} {'closed':>8s} {'worst fold':>26s} {'loose':>7s} {'taut':>7s} {'damage rate of the worst fold':>31s} {'total moment':>13s}",
          f"  {'':18s} {'':>5s} {'[mm]':>8s} {'':>26s} {'':>7s} {'':>7s} {'vs ' + ref.plan.type_name:>31s} {'[N mm/mm]':>13s}"]
    rw = ref.worst
    for r in results:
        w = r.worst
        if w is None:
            L.append(f"  {r.plan.type_name:18s} no fold could be run")
            continue
        a = (w.tension("taut") / rw.tension("taut")) if rw else float("nan")
        mom = r.total_closing_moment
        tied = r.wears_first("tension")["first"]
        label = tied[0] + (f" +{len(tied) - 1} tied" if len(tied) > 1 else "")
        L.append(f"  {r.plan.type_name:18s} {len(r.plan.folds):5d} {r.plan.closed_thickness_mm:8.1f} {label:>26s} {_pct(w.tension('loose')):>7s} {_pct(w.tension('taut')):>7s} "
                 f"{a ** 3:12.2f}x to {a ** 12:10.3f}x {('%.2f' % mom) if mom is not None else 'n/a':>13s}")
    flagged = [r.plan.type_name for r in results if any((o.tension('taut') or 0) >= STRAIN_SCREEN for o in r.outcomes)]
    L += ["", "NOTES"]
    if flagged:
        L.append(f"  - tension-face strain >= {100 * STRAIN_SCREEN:.0f} % (screening threshold, not a failure criterion; the neo-Hookean model is unvalidated there): " + ", ".join(flagged))
    L += ["  - folds are evaluated one at a time with the stack each wraps; their interaction, the pockets and card-slot edges, and the wallet's 3D shape are not modelled.",
          "  - a fold's amplitude is closed -> flat; wallets are opened part-way in real use, and sit closed most of the time (creep and set, not modelled).",
          "  - grain-in folds (z-fold) have the grain in compression and the back face in tension; the tension face is what is ranked.",
          "  - the damage rates are relative and uncalibrated, with no leather-specific exponent; they say which wallet is gentler, not how long anything lasts."]
    return "\n".join(L)
