"""Leather material cards: what is known about a leather, how it is known, and in which state it is.

Two ideas drive the design:

* Every number carries its PROVENANCE (``measured`` | ``literature`` | ``assumed``) and, where known, a range. A card with
  an ``assumed`` value is allowed, but results that depend on it say so.
* AGEING is not a formula. No validated model predicts how a given leather changes with time, and the evidence on
  chrome- versus vegetable-tanned ageing is mixed (see ``docs/MATERIALS.md``). So an aged leather is a separate
  ``MaterialState`` whose numbers come from measurements on aged strips of that leather, never from a built-in curve.

No leather property values are shipped as defaults except the one range backed by a cited measurement.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Value:
    """A number with provenance and, optionally, a plausible range."""
    value: float
    source: str                      # "measured" | "literature" | "assumed"
    low: float | None = None
    high: float | None = None
    ref: str = ""                    # citation or test description

    def __post_init__(self) -> None:
        if self.source not in ("measured", "literature", "assumed"):
            raise ValueError(f"unknown provenance {self.source!r}")
        if (self.low is None) != (self.high is None):
            raise ValueError("give both low and high, or neither")
        if self.low is not None and not self.low <= self.value <= self.high:
            raise ValueError("value must lie within [low, high]")

    @property
    def range(self) -> tuple[float, float]:
        return (self.value, self.value) if self.low is None else (self.low, self.high)


@dataclass
class MaterialState:
    """The leather at one point in its life. ``strain_to_crack`` stays None until flex tests exist for this state."""
    name: str                                       # e.g. "new", "aged 28 d, 70 C / 65 % RH (own test)"
    youngs_modulus_mpa: Value
    poisson: Value = field(default_factory=lambda: Value(0.3, "assumed", ref="no standard test; placeholder"))
    strain_to_crack: Value | None = None
    notes: str = ""


@dataclass
class LeatherMaterial:
    name: str
    tanning: str                                    # "vegetable" | "chrome" | "combination" | "other" | "unknown"
    thickness_mm: Value
    states: dict[str, MaterialState] = field(default_factory=dict)
    # D = D_ref * (t / t_ref)**n. n = 3 is the homogeneous-plate value; fibrous, layered leather may differ and the
    # exponent should be measured by testing strips of several thicknesses of the same leather.
    bending_exponent: Value = field(default_factory=lambda: Value(3.0, "assumed", ref="homogeneous plate"))

    def state(self, name: str = "new") -> MaterialState:
        try:
            return self.states[name]
        except KeyError:
            raise KeyError(f"{self.name!r} has no state {name!r}; known: {sorted(self.states)}") from None


def scale_flexural_rigidity(d_ref: float, t_ref_mm: float, t_mm: float, exponent: float = 3.0) -> float:
    """Flexural rigidity of the same leather at another thickness: D = D_ref * (t / t_ref)^n."""
    if min(d_ref, t_ref_mm, t_mm) <= 0:
        raise ValueError("values must be positive")
    return d_ref * (t_mm / t_ref_mm) ** exponent


def vegetable_tanned_literature() -> LeatherMaterial:
    """The one card backed by a published measurement: metal-free vegetable-tanned bovine leather, tensile modulus
    ~24 MPa (flank) to ~53 MPa (back), Materials 2022, 15(15):5107 (check which sample is which before citing).
    Thickness is deliberately unset (the wallet's own measurement goes here) and no aged state is provided."""
    e = Value(38.0, "literature", low=24.0, high=53.0, ref="Materials 2022, 15(15):5107, tensile modulus, back vs flank")
    return LeatherMaterial(
        name="vegetable-tanned bovine (literature range)", tanning="vegetable",
        thickness_mm=Value(1.2, "assumed", ref="set to the measured thickness of the real wallet"),
        states={"new": MaterialState("new", e, notes="range spans hide position; use the strip you actually tested")})
