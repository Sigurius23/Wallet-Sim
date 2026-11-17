"""Cycle-damage bookkeeping for "x folds" — with the calibration made explicit.

There is no validated fatigue law for leather (no S-N curve, no crack-growth law, no accepted acceleration factor).
So this module does two honest things and refuses a third:

1. ``rank_locations`` — rank locations by damage RATE (cycles per use x strain^m) for a range of assumed exponents m.
   If the ranking does not change across the range, "location A wears first" is a robust statement even though no
   absolute number is known; if it does change, the answer depends on a material property you have not measured.
2. ``fit_law`` — fit  N_crack = A * strain^(-m)  to the user's OWN flex-test data (strain vs cycles to first crack,
   same leather lot, same conditioning). Predictions are only returned with an ``extrapolated`` flag when they leave
   the tested strain range.
3. Refused: an absolute service-life number from an uncalibrated law.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_EXPONENTS = (3.0, 5.0, 8.0, 12.0)   # sensitivity range for RANKING only; not a material property


@dataclass
class Exposure:
    """Load seen by one location per use of the wallet: strain amplitude, and how many such cycles per use."""
    strain: float
    cycles_per_use: float = 1.0


def rank_locations(exposure_by_location: dict[str, Exposure], exponents=DEFAULT_EXPONENTS) -> dict:
    """Rank locations by relative damage rate  rate = cycles_per_use * strain^m  (highest first), for each exponent m.

    The exponent only changes the order when locations differ in BOTH strain and cycles per use (e.g. a spine fold
    opened once per use versus a card-slot edge flexed on every card pull). ``stable`` is True when the order is the
    same for every exponent in ``exponents``; then "A wears before B" holds even though m is unknown.
    """
    if not exposure_by_location:
        raise ValueError("no locations")
    rankings = {m: sorted(exposure_by_location, key=lambda k: -(exposure_by_location[k].cycles_per_use
                                                                  * exposure_by_location[k].strain ** m))
                for m in exponents}
    first = next(iter(rankings.values()))
    stable = all(r == first for r in rankings.values())
    return {"rankings": rankings, "stable": stable, "order": first if stable else None}


@dataclass
class DamageLaw:
    """N_crack = coefficient * strain**(-exponent), fitted to flex-test data."""
    coefficient: float
    exponent: float
    r_squared: float
    strain_min: float
    strain_max: float
    n_points: int
    source: str = "user flex-test data"

    def cycles_to_crack(self, strain: float) -> dict:
        n = self.coefficient * strain ** (-self.exponent)
        extrapolated = not (self.strain_min * 0.8 <= strain <= self.strain_max * 1.25)
        return {"cycles": n, "extrapolated": extrapolated,
                "note": ("OUTSIDE the tested strain range: do not rely on this number" if extrapolated
                         else "within the tested range; applies only to the tested leather lot and conditioning")}

    def damage(self, strain: float, n_cycles: float) -> float:
        """Miner-style damage fraction after ``n_cycles`` at constant strain (1.0 = predicted first crack)."""
        return n_cycles / self.cycles_to_crack(strain)["cycles"]


def fit_law(strains: list[float], cycles: list[float], source: str = "user flex-test data") -> DamageLaw:
    """Least-squares fit of ln N = ln A - m ln eps. Needs >= 3 points spanning at least a factor 1.5 in strain."""
    if len(strains) != len(cycles) or len(strains) < 3:
        raise ValueError("need at least 3 (strain, cycles) points")
    if min(strains) <= 0 or min(cycles) <= 0:
        raise ValueError("strains and cycles must be positive")
    if max(strains) / min(strains) < 1.5:
        raise ValueError("strain range too narrow to fit an exponent (need max/min >= 1.5)")
    x = [math.log(s) for s in strains]
    y = [math.log(c) for c in cycles]
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((b - (intercept + slope * a)) ** 2 for a, b in zip(x, y))
    ss_tot = sum((b - my) ** 2 for b in y)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return DamageLaw(math.exp(intercept), -slope, r2, min(strains), max(strains), n, source)
