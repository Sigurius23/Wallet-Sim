"""Level-0 fold screen: outer-fibre strain of a bent leather sheet.

    eps = t / (2 R + t)        t = thickness, R = INSIDE bend radius, eps = tensile strain at the outer (grain) fibre

This is a thin-shell, pure-bending, small-strain relation. Leather is viscoelastic and anisotropic, it ignores the
finish layer and creep, and a crease tightens progressively. Treat the numbers as a way to COMPARE two designs and to
reject obviously bad geometry, not as a failure criterion. The thresholds below are screening heuristics taken from
``prior-research/reference/durability.md``; they are not validated limits.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Heuristics (not validated failure limits)
RADIUS_RULE_OF_THUMB = (2.0, 3.0)   # a leather fold wants an inside radius of roughly 2-3 x t
RADIUS_FLOOR = 1.0                  # below 1 x t the grain relies on the finish to hold together
STRAIN_SCREEN = 0.20                # ~20 % outer-fibre strain: screening threshold only


def outer_fibre_strain(thickness_mm: float, inside_radius_mm: float) -> float:
    """eps = t / (2R + t) for a sheet of thickness t bent to inside radius R."""
    if thickness_mm <= 0 or inside_radius_mm < 0:
        raise ValueError("thickness must be > 0 and radius >= 0")
    return thickness_mm / (2 * inside_radius_mm + thickness_mm)


def inside_radius_for_strain(thickness_mm: float, strain: float) -> float:
    """Inverse of :func:`outer_fibre_strain`: the inside radius that gives ``strain`` at the outer fibre."""
    if not 0 < strain <= 1:
        raise ValueError("strain must be in (0, 1]")
    return thickness_mm * (1 / strain - 1) / 2


@dataclass
class FoldScreen:
    thickness_mm: float
    inside_radius_mm: float
    strain: float
    radius_over_thickness: float
    flags: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        head = (f"t={self.thickness_mm:g} mm, R_in={self.inside_radius_mm:g} mm (R/t={self.radius_over_thickness:.2f}): "
                f"outer-fibre strain {100 * self.strain:.1f} %")
        return head + ("".join(f"\n  - {f}" for f in self.flags) if self.flags else "\n  - within the screening rules")


def screen(thickness_mm: float, inside_radius_mm: float) -> FoldScreen:
    eps = outer_fibre_strain(thickness_mm, inside_radius_mm)
    ratio = inside_radius_mm / thickness_mm
    flags = []
    if ratio < RADIUS_FLOOR:
        flags.append(f"inside radius below 1 x t: the grain relies on the finish to hold, expect cracking (R/t={ratio:.2f})")
    elif ratio < RADIUS_RULE_OF_THUMB[0]:
        flags.append(f"inside radius below the 2-3 x t rule of thumb (R/t={ratio:.2f})")
    if eps >= STRAIN_SCREEN:
        flags.append(f"outer-fibre strain >= {100 * STRAIN_SCREEN:.0f} % (screening threshold, not a validated failure criterion)")
    return FoldScreen(thickness_mm, inside_radius_mm, eps, ratio, flags)
