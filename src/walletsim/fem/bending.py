"""Pure-bending benchmark of a leather strip in CalculiX.

A strip (thickness t, length L, width W) is clamped at one end and rotated at the other through ``angle_deg``
about its width axis. The outer-fibre strain from the finite-element solution is compared with the closed-form
value  eps = t / (2 R + t)  for pure bending, where R is the *inside* radius.

This is the validation case for the FEM backend: before any wallet geometry is trusted, the solver must reproduce
this number. The material is linear elastic, which is only meaningful at the strains where leather is roughly linear;
the benchmark checks the *kinematics* (large rotation, strain recovery), not leather physics.
"""
from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


class FemUnavailable(RuntimeError):
    """CalculiX (ccx) is not installed or not on PATH."""


@dataclass
class BendingJob:
    thickness_mm: float = 1.0
    length_mm: float = 40.0
    width_mm: float = 10.0
    angle_deg: float = 180.0
    youngs_modulus_mpa: float = 50.0    # PLACEHOLDER. Measured vegetable-tanned bovine leather: ~24-53 MPa, depending on
                                        # hide position (Materials 2022, 15(15):5107). The strain result does not depend on it
    poisson: float = 0.3                # PLACEHOLDER: leather Poisson's ratio has no standard test
    material: str = "neo-hooke"         # "neo-hooke" (stable at large strain) or "linear" (St. Venant-Kirchhoff, small strain only)
    nx: int = 40                        # elements along the length
    ny: int = 4                         # across the width
    nz: int = 4                         # through the thickness


@dataclass
class BendingResult:
    job: BendingJob
    neutral_radius_mm: float
    inside_radius_mm: float
    analytic_strain: float              # t / (2 R_in + t)
    fem_max_strain: float               # largest engineering strain over all integration points
    fem_min_strain: float
    runtime_s: float
    n_integration_points: int
    fem_moment_n_mm: float = 0.0        # reaction moment at the rotating end (whole strip width)
    analytic_moment_n_mm: float = 0.0   # beam theory E*I*kappa, I = W t^3 / 12
    log_tail: str = field(default="", repr=False)

    @property
    def relative_error(self) -> float:
        return (self.fem_max_strain - self.analytic_strain) / self.analytic_strain

    @property
    def moment_ratio(self) -> float:
        """FEM moment / beam-theory moment. Between 1 and ~1/(1-nu^2) for a strip that is not infinitely narrow."""
        return self.fem_moment_n_mm / self.analytic_moment_n_mm


def analytic_outer_strain(thickness_mm: float, length_mm: float, angle_deg: float) -> tuple[float, float, float]:
    """Closed form for a mid-surface of fixed length bent through ``angle_deg``.

    Returns (neutral_radius, inside_radius, outer_fibre_strain).
    """
    theta = math.radians(angle_deg)
    r_neutral = length_mm / theta
    r_inside = r_neutral - thickness_mm / 2
    return r_neutral, r_inside, thickness_mm / (2 * r_inside + thickness_mm)


def surface_factor(nz: int) -> float:
    """Ratio of the strain at the outer surface to the strain at the outermost 2x2x2 Gauss point, for a field that is
    linear through the thickness. The Gauss point lies 0.5*(1 - 1/sqrt(3))*h inside the surface (h = t/nz)."""
    d = 0.5 * (1 - 1 / math.sqrt(3)) / nz          # in units of the thickness
    return 0.5 / (0.5 - d)


def analytic_moment(job: BendingJob) -> float:
    """Beam-theory bending moment (N mm) for the whole strip: E * (W t^3 / 12) * (theta / L)."""
    kappa = math.radians(job.angle_deg) / job.length_mm
    return job.youngs_modulus_mpa * job.width_mm * job.thickness_mm ** 3 / 12 * kappa


def job_for_inside_radius(thickness_mm: float, inside_radius_mm: float, angle_deg: float = 180.0, **kw) -> BendingJob:
    """A strip folded around a given INSIDE radius (what a wallet's contents impose), instead of a given length."""
    length = math.radians(angle_deg) * (inside_radius_mm + thickness_mm / 2)
    return BendingJob(thickness_mm=thickness_mm, length_mm=length, angle_deg=angle_deg, **kw)


def _material_cards(job: BendingJob) -> list[str]:
    E, nu = job.youngs_modulus_mpa, job.poisson
    if job.material == "linear":
        return ["*ELASTIC", f"{E}, {nu}"]
    if job.material == "neo-hooke":
        # initial shear modulus G = 2*C10, initial bulk modulus K = 2/D1, matched to (E, nu)
        return ["*HYPERELASTIC, NEO HOOKE", f"{E / (4 * (1 + nu)):.8g}, {6 * (1 - 2 * nu) / E:.8g}"]
    raise ValueError(f"unknown material model {job.material!r}")


def build_input(job: BendingJob) -> str:
    """CalculiX input deck: C3D8I solids, geometrically nonlinear, end face tied to a rigid body that is rotated."""
    t, L, W = job.thickness_mm, job.length_mm, job.width_mm
    xs = np.linspace(0, L, job.nx + 1)
    ys = np.linspace(0, W, job.ny + 1)
    zs = np.linspace(-t / 2, t / 2, job.nz + 1)
    ids: dict[tuple[int, int, int], int] = {}
    nodes: list[tuple[float, float, float]] = []
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for k, z in enumerate(zs):
                nodes.append((x, y, z))
                ids[(i, j, k)] = len(nodes)
    elems = []
    for i in range(job.nx):
        for j in range(job.ny):
            for k in range(job.nz):
                elems.append([ids[(i, j, k)], ids[(i + 1, j, k)], ids[(i + 1, j + 1, k)], ids[(i, j + 1, k)],
                              ids[(i, j, k + 1)], ids[(i + 1, j, k + 1)], ids[(i + 1, j + 1, k + 1)], ids[(i, j + 1, k + 1)]])
    ref, rot = len(nodes) + 1, len(nodes) + 2
    nodes += [(L, W / 2, 0.0), (L, W / 2, 0.0)]
    fixed = [ids[(0, j, k)] for j in range(job.ny + 1) for k in range(job.nz + 1)]
    end = [ids[(job.nx, j, k)] for j in range(job.ny + 1) for k in range(job.nz + 1)]

    def nset(name: str, members: list[int]) -> list[str]:
        out = [f"*NSET, NSET={name}"]
        out += [", ".join(map(str, members[a:a + 8])) for a in range(0, len(members), 8)]
        return out

    deck = ["*NODE, NSET=NALL"]
    deck += [f"{n + 1}, {x:.6f}, {y:.6f}, {z:.6f}" for n, (x, y, z) in enumerate(nodes)]
    deck += ["*ELEMENT, TYPE=C3D8I, ELSET=EALL"]
    deck += [f"{n + 1}, " + ", ".join(map(str, e)) for n, e in enumerate(elems)]
    deck += nset("FIX", fixed) + nset("ENDF", end) + [f"*NSET, NSET=REF\n{ref}", f"*NSET, NSET=ROT\n{rot}"]
    deck += ["*MATERIAL, NAME=LEATHER"] + _material_cards(job) + [
             "*SOLID SECTION, ELSET=EALL, MATERIAL=LEATHER",
             f"*RIGID BODY, NSET=ENDF, REF NODE={ref}, ROT NODE={rot}",
             "*BOUNDARY", "FIX, 1, 3",
             "*STEP, NLGEOM, INC=1000", "*STATIC", "0.02, 1.0, 1e-6, 0.1",
             "*BOUNDARY", f"{rot}, 2, 2, {math.radians(job.angle_deg)}",
             "*EL PRINT, ELSET=EALL, FREQUENCY=1000", "E",
             "*NODE PRINT, NSET=ROT, FREQUENCY=1000", "RF",
             "*END STEP"]
    return "\n".join(deck) + "\n"


_HEADER = re.compile(r"strains \(elem, integ\.pnt\.,exx,eyy,ezz,exy,exz,eyz\)[^\n]*\n")


def parse_last_green_strains(dat_text: str) -> np.ndarray:
    """Rows (elem, ip, exx, eyy, ezz, exy, exz, eyz) of the last strain block in a CalculiX .dat file."""
    headers = list(_HEADER.finditer(dat_text))
    if not headers:
        raise ValueError("no strain block in the .dat file")
    rows = []
    for line in dat_text[headers[-1].end():].split("\n"):
        if not line.strip():
            if rows:
                break
            continue
        rows.append([float(v) for v in line.split()])
    return np.array(rows)


_MOMENT = re.compile(r"forces \(fx,fy,fz\) for set ROT[^\n]*\n\s*\n\s*\d+\s+(\S+)\s+(\S+)\s+(\S+)")


def parse_rotation_moment(dat_text: str) -> float:
    """Reaction moment about the width (y) axis at the rotation node of the rigid end, N mm."""
    m = list(_MOMENT.finditer(dat_text))
    if not m:
        raise ValueError("no reaction block for the rotation node in the .dat file")
    return float(m[-1].group(2))


def run_bending(job: BendingJob | None = None, workdir: str | Path | None = None, ccx: str = "ccx",
                strain_window: tuple[float, float] = (0.3, 0.7)) -> BendingResult:
    job = job or BendingJob()
    exe = shutil.which(ccx)
    if exe is None:
        raise FemUnavailable("CalculiX not found. Install it (Debian/Ubuntu: apt-get install calculix-ccx).")
    ctx = tempfile.TemporaryDirectory() if workdir is None else None
    wd = Path(ctx.name if ctx else workdir)
    wd.mkdir(parents=True, exist_ok=True)
    try:
        (wd / "bend.inp").write_text(build_input(job))
        t0 = time.time()
        proc = subprocess.run([exe, "-i", "bend"], cwd=wd, capture_output=True, text=True, timeout=1800)
        runtime = time.time() - t0
        if proc.returncode != 0:
            raise RuntimeError(f"ccx failed ({proc.returncode}):\n{proc.stdout[-1500:]}")
        dat = (wd / "bend.dat").read_text()
        rows = parse_last_green_strains(dat)
        # Pure-bending theory applies away from the clamped and rotated ends, where the constraints concentrate strain
        # (and that peak grows with mesh refinement). Elements are numbered i-major: e = (i*ny + j)*nz + k + 1.
        i_el = (rows[:, 0].astype(int) - 1) // (job.ny * job.nz)
        mid = (i_el >= int(job.nx * strain_window[0])) & (i_el < int(job.nx * strain_window[1]))
        e_xx = rows[mid, 2]                     # Green-Lagrange strain along the strip, mid-length only
        eng = (np.sqrt(1 + 2 * e_xx) - 1) * surface_factor(job.nz)   # integration points sit inside the surface
        r_n, r_in, eps = analytic_outer_strain(job.thickness_mm, job.length_mm, job.angle_deg)
        return BendingResult(job, r_n, r_in, eps, float(eng.max()), float(eng.min()), runtime, len(eng),
                             parse_rotation_moment(dat), analytic_moment(job), proc.stdout[-400:])
    finally:
        if ctx:
            ctx.cleanup()
