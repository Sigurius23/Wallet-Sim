"""Fold-style simulator: a layered, variable-thickness leather strip folded in CalculiX (plane strain).

One model describes every "bending style" a wallet fold can have, because a fold is a strip with a layup along its length:

* plain          one layer of constant thickness
* skived         the flesh side of the shell is thinned over the fold (the grain face stays flat)
* lined          shell + glued lining (or an interlining), each with its own thickness and stiffness
* hinged         the fold zone is a different (softer / thinner) leather than the panels
* grain in / out which face of the leather is in tension (``flat_face`` keeps the grain face the flat one)

Two load cases, both symmetric halves of a 180 degree fold (the symmetry plane is the fold centre, u = 0):

``free``  the end at the fold centre is rotated by half the fold angle and may translate freely. The strip finds its own
          shape: curvature collects where the strip is most compliant. Moment-controlled; closed form exists
          (``analytic_free``) and is the validation.
``wrap``  the strip is wrapped around a rigid rounded stack (what the contents of a wallet impose), frictionless
          contact. Radius-controlled: the inside radius is the stack's, whatever the leather.

Conventions: layers are listed from the OUTER face (tension side) inward. u is the arc distance from the fold centre
along the strip, negative toward the panel. Plane strain, width 1 mm, so moments are per mm of wallet width.
Adhesive between layers is a perfect bond (no slip, no thickness); the leather is isotropic neo-Hookean. There is no
permanent set, creep, friction or finish film in this model.
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

from .bending import FemUnavailable, parse_last_green_strains  # noqa: F401  (re-exported)

GP = 1 / math.sqrt(3)       # 2x2x2 Gauss point offset in element-local coordinates


@dataclass(frozen=True)
class Layer:
    """One layer of the strip. ``profile`` is the thickness along the strip as (u_mm, thickness_mm) breakpoints
    (linear in between, constant beyond the ends). ``zones`` optionally changes the stiffness along the strip:
    (u_from, u_to, E_MPa, poisson), first match wins, else the layer's own values."""
    name: str
    profile: tuple[tuple[float, float], ...]
    youngs_modulus_mpa: float
    poisson: float = 0.3
    nz: int = 4
    zones: tuple[tuple[float, float, float, float], ...] = ()

    def thickness(self, u: float) -> float:
        us, ts = zip(*self.profile)
        return float(np.interp(u, us, ts))

    def material_at(self, u: float) -> tuple[float, float]:
        for u0, u1, e, nu in self.zones:
            if u0 <= u <= u1:
                return e, nu
        return self.youngs_modulus_mpa, self.poisson


def uniform(name: str, t: float, E: float, nu: float = 0.3, nz: int = 4) -> Layer:
    return Layer(name, ((0.0, t),), E, nu, nz)


@dataclass
class FoldJob:
    layers: tuple[Layer, ...]
    mode: str = "wrap"                  # "wrap" | "free"
    fold_deg: float = 180.0             # the full fold; the model is the half to the symmetry plane
    inside_radius_mm: float = 3.0       # wrap: radius of the stack the leather folds around
    run_mm: float = 12.0                # length of strip modelled beyond the start of the bend (flat tail, wrap) / strip half length (free)
    dx_mm: float = 0.5                  # element length along the strip
    grain_layer: str | None = None      # name of the layer whose OUTER face is the grain (reporting only)
    skip_mm: float | None = None        # ignore the strip this far from the bend start (constraint effects); default 2 x thickness
    tension_n_per_mm: float = 0.0       # wrap: pull on the free start of the strip (N per mm of width); 0 = leather lies on the stack untensioned
    flat_face: str = "outer"            # which face of the layup stays flat where thickness varies: "outer" (grain out, flesh side thinned)
                                        # or "inner" (grain in: the grain face is the one against the stack / on the inside of the fold)

    def total_thickness(self, u: float) -> float:
        return sum(l.thickness(u) for l in self.layers)

    @property
    def half_angle(self) -> float:
        return math.radians(self.fold_deg) / 2

    @property
    def arc_mm(self) -> float:
        """Length of the bent part of the half model (wrap): the neutral fibre around the stack."""
        return self.half_angle * (self.inside_radius_mm + self.total_thickness(0.0) / 2)

    @property
    def u_start(self) -> float:
        return -(self.arc_mm + self.run_mm) if self.mode == "wrap" else -self.run_mm


@dataclass
class Mesh:
    xs: np.ndarray
    us: np.ndarray
    z: np.ndarray                       # (nx+1, K+1) reference z of the nodes
    row_layer: list[int]                # layer index of each element row
    row_sub: list[int]                  # sub-index of each element row inside its layer
    ids: dict
    nodes: list
    elems: list
    elem_key: list                      # (i, k) of each element
    elem_mat: list                      # (layer index, E, nu) of each element


def build_mesh(job: FoldJob) -> Mesh:
    u0 = job.u_start
    nx = max(8, int(round(-u0 / job.dx_mm)))
    us = np.linspace(u0, 0.0, nx + 1)
    shift = -u0 if job.mode == "free" else job.arc_mm       # free: clamp at x=0. wrap: bend starts at x=0
    xs = us + shift
    row_layer, row_sub = [], []
    for li, l in enumerate(job.layers):
        row_layer += [li] * l.nz
        row_sub += list(range(l.nz))
    K = len(row_layer)
    if job.flat_face not in ("outer", "inner"):
        raise ValueError("flat_face must be 'outer' or 'inner'")
    # wrap: the flat tail lies on the stack, so the outer face sits one tail-thickness above it (thinner zones then hang above the stack)
    ztop = job.inside_radius_mm + job.total_thickness(u0) if job.mode == "wrap" else 0.0
    z = np.zeros((nx + 1, K + 1))
    for i, u in enumerate(us):
        zc = ztop
        z[i, 0] = zc
        k = 0
        for l in job.layers:
            t = l.thickness(u)
            for s in range(1, l.nz + 1):
                z[i, k + s] = zc - t * s / l.nz
            zc -= t
            k += l.nz
    if job.flat_face == "inner":                    # keep the inner face flat instead (on the stack for a wrap), thickness change on the outer face
        z += (job.inside_radius_mm if job.mode == "wrap" else 0.0) - z[:, [K]]
    ids, nodes = {}, []
    for i in range(nx + 1):
        for j in (0, 1):
            for k in range(K + 1):
                nodes.append((xs[i], float(j), z[i, k]))
                ids[(i, j, k)] = len(nodes)
    elems, keys, mats = [], [], []
    for i in range(nx):
        uc = 0.5 * (us[i] + us[i + 1])
        for k in range(K):
            li = row_layer[k]
            e, nu = job.layers[li].material_at(uc)
            # rows run from the outer face (k=0, high z) inward; element z axis points up, so node order uses k+1 below k
            elems.append([ids[(i, 0, k + 1)], ids[(i + 1, 0, k + 1)], ids[(i + 1, 1, k + 1)], ids[(i, 1, k + 1)],
                          ids[(i, 0, k)], ids[(i + 1, 0, k)], ids[(i + 1, 1, k)], ids[(i, 1, k)]])
            keys.append((i, k))
            mats.append((li, e, nu))
    return Mesh(xs, us, z, row_layer, row_sub, ids, nodes, elems, keys, mats)


def _nset(name: str, members: list[int]) -> list[str]:
    out = [f"*NSET, NSET={name}"]
    out += [", ".join(map(str, members[a:a + 10])) for a in range(0, len(members), 10)]
    return out


def _elset(name: str, members: list[int]) -> list[str]:
    out = [f"*ELSET, ELSET={name}"]
    out += [", ".join(map(str, members[a:a + 10])) for a in range(0, len(members), 10)]
    return out


def _neo_hooke(E: float, nu: float) -> list[str]:
    return ["*HYPERELASTIC, NEO HOOKE", f"{E / (4 * (1 + nu)):.8g}, {6 * (1 - 2 * nu) / E:.8g}"]


def _mandrel(job: FoldJob, first_node: int, first_elem: int):
    """Rigid rounded stack: flat top for x <= 0, then a quarter-circle of radius R about the origin. Returns nodes, elements,
    the element ids of the contact (top) faces."""
    R = job.inside_radius_mm
    flat_x = list(np.arange(-(job.run_mm + 3.0), 0.0, 1.0)) + [0.0]
    st = [((x, R), (0.0, 1.0)) for x in flat_x]
    dphi = 1.5 if R > 1.0 else 1.0
    n_arc = max(8, int(round(math.degrees(job.half_angle) / dphi)))
    for j in range(1, n_arc + 1):
        phi = job.half_angle * j / n_arc
        st.append(((R * math.sin(phi), R * math.cos(phi)), (math.sin(phi), math.cos(phi))))
    depth = min(1.0, 0.5 * R)
    nodes, ids = [], {}
    for m, ((px, pz), (nx_, nz_)) in enumerate(st):
        for role, off in (("in", depth), ("out", 0.0)):
            for j in (0, 1):
                nodes.append((px - off * nx_, float(j), pz - off * nz_))
                ids[(m, role, j)] = first_node + len(nodes) - 1
    elems, top = [], []
    for m in range(len(st) - 1):
        elems.append([ids[(m, "in", 0)], ids[(m + 1, "in", 0)], ids[(m + 1, "in", 1)], ids[(m, "in", 1)],
                      ids[(m, "out", 0)], ids[(m + 1, "out", 0)], ids[(m + 1, "out", 1)], ids[(m, "out", 1)]])
        top.append(first_elem + len(elems) - 1)
    return nodes, elems, top


def build_fold_input(job: FoldJob, contact_stiffness: float | None = None) -> tuple[str, Mesh]:
    if job.mode not in ("wrap", "free"):
        raise ValueError("mode must be 'wrap' or 'free'")
    mesh = build_mesh(job)
    nx, K = len(mesh.xs) - 1, len(mesh.row_layer)
    nodes, elems = list(mesh.nodes), list(mesh.elems)
    n_strip, e_strip = len(nodes), len(elems)
    left = [mesh.ids[(0, j, k)] for j in (0, 1) for k in range(K + 1)]
    end = [mesh.ids[(nx, j, k)] for j in (0, 1) for k in range(K + 1)]
    inner = [mesh.ids[(i, j, K)] for i in range(nx + 1) for j in (0, 1)]
    strip_nodes = list(range(1, n_strip + 1))

    deck: list[str] = []
    mand_nodes: list[tuple] = []
    mand_elems: list[list[int]] = []
    top: list[int] = []
    zmid0 = float(mesh.z[nx, 0] + mesh.z[nx, K]) / 2
    n_mand = 0
    if job.mode == "wrap":
        mand_nodes, mand_elems, top = _mandrel(job, n_strip + 1, e_strip + 1)
    n_mand = len(mand_nodes)
    ref, rot = n_strip + n_mand + 1, n_strip + n_mand + 2
    extra = [(mesh.xs[nx], 0.5, zmid0), (mesh.xs[nx], 0.5, zmid0)]

    deck += ["*NODE, NSET=NALL"]
    allnodes = nodes + mand_nodes + extra
    deck += [f"{n + 1}, {x:.7f}, {y:.7f}, {z:.7f}" for n, (x, y, z) in enumerate(allnodes)]
    deck += ["*ELEMENT, TYPE=C3D8I, ELSET=STRIP"]
    deck += [f"{n + 1}, " + ", ".join(map(str, e)) for n, e in enumerate(elems)]
    if mand_elems:
        deck += ["*ELEMENT, TYPE=C3D8, ELSET=MAND"]
        deck += [f"{e_strip + n + 1}, " + ", ".join(map(str, e)) for n, e in enumerate(mand_elems)]
    # materials: one per distinct (E, nu)
    cards: dict[tuple[float, float], list[int]] = {}
    for n, (_, e, nu) in enumerate(mesh.elem_mat):
        cards.setdefault((e, nu), []).append(n + 1)
    for c, ((e, nu), members) in enumerate(cards.items()):
        deck += _elset(f"EM{c}", members)
        deck += [f"*MATERIAL, NAME=LM{c}"] + _neo_hooke(e, nu) + [f"*SOLID SECTION, ELSET=EM{c}, MATERIAL=LM{c}"]
    if mand_elems:
        deck += ["*MATERIAL, NAME=RIGID", "*ELASTIC", "1e6, 0.3", "*SOLID SECTION, ELSET=MAND, MATERIAL=RIGID"]
    deck += _nset("LEFT", left) + _nset("END", end) + _nset("INNER", inner) + _nset("STRIPN", strip_nodes)

    # the end face is a rigid body in both modes (REF translates, ROT carries the rotation)
    zmid = float(mesh.z[nx, 0] + mesh.z[nx, K]) / 2
    deck += [f"*NSET, NSET=REF\n{ref}", f"*NSET, NSET=ROT\n{rot}"]
    deck += [f"*RIGID BODY, NSET=END, REF NODE={ref}, ROT NODE={rot}"]
    end_set = set(end)
    deck += _nset("NOTEND", [n for n in strip_nodes if n not in end_set])
    amp: list[str] = []
    if job.mode == "wrap":
        k = contact_stiffness or _default_contact_stiffness(job)
        mn = list(range(n_strip + 1, n_strip + len(mand_nodes) + 1))
        deck += _nset("MANDN", mn)
        deck += ["*SURFACE, NAME=MASTER, TYPE=ELEMENT"] + [f"{e}, S2" for e in top]
        deck += ["*SURFACE, NAME=SLAVE, TYPE=NODE", "INNER"]
        deck += ["*SURFACE INTERACTION, NAME=SI", "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR", f"{k:.6g}",
                 "*CONTACT PAIR, INTERACTION=SI, TYPE=NODE TO SURFACE", "SLAVE, MASTER"]
        # the start slides freely along the stack: vertical position and rotation fixed, one common x displacement
        deck += ["*EQUATION"]
        for n in left[1:]:
            deck += ["2", f"{n}, 1, 1.0, {left[0]}, 1, -1.0"]
        deck += ["*BOUNDARY", "MANDN, 1, 3", "LEFT, 3, 3", "NOTEND, 2, 2", f"{ref}, 2, 2", f"{rot}, 1, 1", f"{rot}, 3, 3"]
        # roll the end face onto the stack along its true path: tangent point at angle phi, straight tangent beyond
        R, th, L = job.inside_radius_mm, job.half_angle, job.arc_mm
        # radius of the end face's mid-thickness point: starts where the outer-flat layup puts it and is drawn down until
        # the end face's inner face lies on the stack (a skived or hinged zone is thinner than the tail, so it starts above it)
        rn_final = R + job.total_thickness(0.0) / 2
        x_e = float(mesh.xs[nx])
        phis = np.linspace(0.0, th, 41)
        rn = zmid + (rn_final - zmid) * phis / th
        px = rn * np.sin(phis) + (L - phis * rn) * np.cos(phis) - x_e
        pz = rn * np.cos(phis) - (L - phis * rn) * np.sin(phis) - zmid
        ts = np.linspace(0.0, 1.0, len(phis))
        for name, vals in (("AX", px), ("AZ", pz), ("AR", phis)):
            amp += [f"*AMPLITUDE, NAME={name}"] + [f"{t:.6f}, {v:.8f}" for t, v in zip(ts, vals)]
        pull: list[str] = []
        if job.tension_n_per_mm:
            pull = ["*CLOAD, AMPLITUDE=AT"] + [f"{n}, 1, {-job.tension_n_per_mm / len(left):.8g}" for n in left]
            amp += ["*AMPLITUDE, NAME=AT"] + [f"{t:.6f}, {1.0 if t > 0.25 else 4 * t:.4f}" for t in np.linspace(0, 1, 41)]
        step_bc = ["*BOUNDARY, AMPLITUDE=AX", f"{ref}, 1, 1, 1.0", "*BOUNDARY, AMPLITUDE=AZ", f"{ref}, 3, 3, 1.0",
                   "*BOUNDARY, AMPLITUDE=AR", f"{rot}, 2, 2, 1.0"] + pull
    else:
        deck += ["*BOUNDARY", "LEFT, 1, 3", "NOTEND, 2, 2", f"{ref}, 2, 2", f"{rot}, 1, 1", f"{rot}, 3, 3"]
        step_bc = ["*BOUNDARY", f"{rot}, 2, 2, {job.half_angle:.8f}"]

    deck += amp + ["*STEP, NLGEOM, INC=4000", "*STATIC", "0.02, 1.0, 1e-7, 0.05"] + step_bc
    deck += ["*EL PRINT, ELSET=STRIP, FREQUENCY=1000", "E",
             "*NODE PRINT, NSET=STRIPN, FREQUENCY=1000", "U"]
    deck += ["*NODE PRINT, NSET=ROT, FREQUENCY=1000", "RF", "*NODE PRINT, NSET=REF, FREQUENCY=1000", "RF"]
    deck += ["*END STEP"]
    return "\n".join(deck) + "\n", mesh


# --------------------------------------------------------------------------------------------------------------------
# Closed forms (small-strain composite beam, plane strain). These are the references the FEM is validated against, and
# the level-0/1 estimate for layups where no solver is needed.

def _plane_strain_modulus(E: float, nu: float) -> float:
    return E / (1 - nu * nu)


def section(job: FoldJob, u: float) -> dict:
    """Composite section at u: face positions (distance from the outer face, mm), E-weighted neutral axis and flexural
    rigidity D per mm width (N mm^2/mm)."""
    ts = [l.thickness(u) for l in job.layers]
    mats = [_plane_strain_modulus(*l.material_at(u)) for l in job.layers]
    faces = np.concatenate([[0.0], np.cumsum(ts)])
    T = faces[-1]
    ea = sum(e * t for e, t in zip(mats, ts))
    z_na = sum(e * t * (faces[i] + t / 2) for i, (e, t) in enumerate(zip(mats, ts))) / ea     # from the outer face
    d = sum(e * (t ** 3 / 12 + t * (faces[i] + t / 2 - z_na) ** 2) for i, (e, t) in enumerate(zip(mats, ts)))
    return {"faces": faces, "thickness": T, "z_na": z_na, "D": d, "EA": ea}


def analytic_free(job: FoldJob, n: int = 400) -> dict:
    """Moment-controlled fold: M constant, curvature kappa(u) = M / D(u), total rotation = half the fold angle."""
    us = np.linspace(job.u_start, 0.0, n)
    D = np.array([section(job, u)["D"] for u in us])
    M = job.half_angle / np.trapezoid(1.0 / D, us)
    kappa = M / D
    out = {"u": us, "moment": M, "kappa": kappa, "angle": np.concatenate([[0.0], np.cumsum(0.5 * (kappa[1:] + kappa[:-1]) * np.diff(us))])}
    eo, ei = [], []
    for u, k in zip(us, kappa):
        s = section(job, u)
        eo.append(k * s["z_na"])                      # outer face is z_na from the neutral axis, in tension
        ei.append(-k * (s["thickness"] - s["z_na"]))
    out["outer"], out["inner"] = np.array(eo), np.array(ei)
    return out


def analytic_wrap(job: FoldJob, u: float) -> dict:
    """Radius-controlled fold: the inner face lies on the stack (radius R). A fibre at depth zeta above the inner face has
    stretch (R + zeta) / rho, where rho is the radius of the unstrained fibre, fixed by zero net axial force."""
    s = section(job, u)
    R, T = job.inside_radius_mm, s["thickness"]
    zeta_na = T - s["z_na"]                           # E-weighted centroid height above the inner face
    rho = R + zeta_na
    return {"outer": (R + T) / rho - 1.0, "inner": R / rho - 1.0, "rho": rho}


def wrap_strain_closed_form(thickness_mm: float, inside_radius_mm: float) -> float:
    """Single homogeneous layer: the textbook t / (2 R + t)."""
    return thickness_mm / (2 * inside_radius_mm + thickness_mm)


# --------------------------------------------------------------------------------------------------------------------
# Running and reading results

def _last_block(dat: str, header: str) -> np.ndarray:
    ms = list(re.finditer(header + r"[^\n]*\n\s*\n", dat))
    if not ms:
        raise ValueError(f"no block matching {header!r} in the .dat file")
    rows = []
    for line in dat[ms[-1].end():].split("\n"):
        if not line.strip():
            break
        rows.append([float(v) for v in line.split()])
    return np.array(rows)


@dataclass
class FoldResult:
    job: FoldJob
    u: np.ndarray                       # element-column centres
    face_strain: np.ndarray             # (n_columns, n_layers, 2): engineering strain at each layer's outer / inner face
    angle: np.ndarray                   # cross-section rotation at each node column (rad), 0 at the start
    angle_u: np.ndarray
    moment_n_mm: float                  # reaction moment at the fold centre, per mm of width
    standoff_mm: float                  # wrap: largest gap between the leather's inner face and the stack inside the bend
    penetration_mm: float               # wrap: deepest overlap of the leather into the stack (penalty contact; should be small)
    leg_overlap_mm: float               # free: how far the inner face crosses the symmetry plane, i.e. how far the two mirror legs would
                                        # interpenetrate (self-contact is not modelled); 0 when the legs clear each other
    contact_stiffness: float            # wrap: penalty stiffness that converged (MPa/mm)
    runtime_s: float
    skip_mm: float
    log_tail: str = field(default="", repr=False)

    def window(self) -> np.ndarray:
        """Columns away from the constraints: the clamped / sliding start, the tangent point of a wrap, and the last
        thickness before the rigid symmetry face at the fold centre."""
        start = (-self.job.arc_mm if self.job.mode == "wrap" else self.job.u_start) + self.skip_mm
        end = self.job.total_thickness(0.0)
        if self.job.mode == "wrap":
            end = min(end, 0.25 * self.job.arc_mm)               # a tight bend is short: keep a usable middle
        return (self.u >= start) & (self.u <= -end)

    @property
    def outer_strain(self) -> np.ndarray:
        """Strain on the tension face of the whole strip along u."""
        return self.face_strain[:, 0, 0]

    @property
    def inner_strain(self) -> np.ndarray:
        return self.face_strain[:, -1, 1]

    def _checked_window(self) -> np.ndarray:
        w = self.window()
        if w.sum() < 2:
            raise ValueError("the bend is too short for a strain window away from the constraints; use a longer run or a smaller skip_mm")
        return w

    @property
    def peak_outer(self) -> float:
        return float(self.outer_strain[self._checked_window()].max())

    @property
    def peak_outer_u(self) -> float:
        w = self._checked_window()
        return float(self.u[w][np.argmax(self.outer_strain[w])])

    @property
    def peak_inner(self) -> float:
        return float(self.inner_strain[self._checked_window()].min())

    def layer_peak(self, layer: int) -> tuple[float, float]:
        """(largest tension, largest compression) strain on any face of one layer."""
        w = self._checked_window()
        f = self.face_strain[w, layer, :]
        return float(f.max()), float(f.min())

    def angle_share(self, u0: float, u1: float) -> float:
        """Fraction of the total fold taken between two positions on the strip (where the strip actually bends)."""
        a = np.interp([u0, u1], self.angle_u, self.angle)
        return float((a[1] - a[0]) / (self.angle[-1] - self.angle[0]))


def _default_contact_stiffness(job: FoldJob) -> float:
    e_ref = max(l.youngs_modulus_mpa for l in job.layers)
    return 40.0 * e_ref / min(l.thickness(job.u_start) / l.nz for l in job.layers)


def run_fold(job: FoldJob, workdir: str | Path | None = None, ccx: str = "ccx", contact_stiffness: float | None = None) -> FoldResult:
    """Run one fold. For a wrap, the penalty contact stiffness starts stiff and is softened (x1/4, x1/20, x1/100) until the
    solver converges; the stiffness used and the resulting penetration are on the result, so a soft contact is visible."""
    exe = shutil.which(ccx)
    if exe is None:
        raise FemUnavailable("CalculiX not found. Install it (Debian/Ubuntu: apt-get install calculix-ccx).")
    if job.mode == "wrap":
        k0 = contact_stiffness or _default_contact_stiffness(job)
        ladder = [k0] if contact_stiffness else [k0, k0 / 4, k0 / 20, k0 / 100]
    else:
        ladder = [None]
    last = ""
    for k in ladder:
        ctx = tempfile.TemporaryDirectory() if workdir is None else None
        wd = Path(ctx.name if ctx else workdir)
        wd.mkdir(parents=True, exist_ok=True)
        try:
            deck, mesh = build_fold_input(job, k)
            (wd / "fold.inp").write_text(deck)
            t0 = time.time()
            proc = subprocess.run([exe, "-i", "fold"], cwd=wd, capture_output=True, text=True, timeout=3600)
            runtime = time.time() - t0
            if proc.returncode == 0 and (wd / "fold.dat").exists() and "*ERROR" not in proc.stdout:
                return _read_results(job, mesh, (wd / "fold.dat").read_text(), runtime, proc.stdout[-400:], k or 0.0)
            last = proc.stdout[-1500:]
        finally:
            if ctx:
                ctx.cleanup()
    raise RuntimeError(f"ccx did not converge (contact stiffness tried: {ladder}):\n{last}")


def _read_results(job: FoldJob, mesh: Mesh, dat: str, runtime: float, tail: str, k_contact: float = 0.0) -> FoldResult:
    nx, K = len(mesh.xs) - 1, len(mesh.row_layer)
    rows = parse_last_green_strains(dat)
    eng = np.sqrt(1 + 2 * rows[:, 2]) - 1                     # Green-Lagrange along the strip -> engineering strain
    n_layers = len(job.layers)
    # position of each integration point through the element (CalculiX order: first four at the lower local z)
    zlo = np.empty(len(mesh.elems)); zhi = np.empty(len(mesh.elems))
    for n, (i, k) in enumerate(mesh.elem_key):
        zhi[n] = 0.5 * (mesh.z[i, k] + mesh.z[i + 1, k])
        zlo[n] = 0.5 * (mesh.z[i, k + 1] + mesh.z[i + 1, k + 1])
    e_idx = rows[:, 0].astype(int) - 1
    ip = rows[:, 1].astype(int)
    zc, h = 0.5 * (zlo + zhi), zhi - zlo
    zgp = zc[e_idx] + np.where(ip <= 4, -1, 1) * 0.5 * h[e_idx] * GP
    col = np.array([mesh.elem_key[e][0] for e in e_idx])
    lay = np.array([mesh.row_layer[mesh.elem_key[e][1]] for e in e_idx])
    face = np.full((nx, n_layers, 2), np.nan)
    for i in range(nx):
        for li in range(n_layers):
            m = (col == i) & (lay == li)
            if m.sum() < 2:
                continue
            slope, icpt = np.polyfit(zgp[m], eng[m], 1)
            ks = [k for k in range(K) if mesh.row_layer[k] == li]
            z_top = 0.5 * (mesh.z[i, ks[0]] + mesh.z[i + 1, ks[0]])
            z_bot = 0.5 * (mesh.z[i, ks[-1] + 1] + mesh.z[i + 1, ks[-1] + 1])
            face[i, li] = (icpt + slope * z_top, icpt + slope * z_bot)
    U = _last_block(dat, r"displacements \(vx,vy,vz\) for set STRIPN")
    ref = {int(r[0]): r for r in U}
    ang = np.zeros(nx + 1)
    for i in range(nx + 1):
        a, b = mesh.ids[(i, 0, 0)], mesh.ids[(i, 0, K)]
        dx = (mesh.nodes[a - 1][0] + ref[a][1]) - (mesh.nodes[b - 1][0] + ref[b][1])
        dz = (mesh.nodes[a - 1][2] + ref[a][3]) - (mesh.nodes[b - 1][2] + ref[b][3])
        ang[i] = math.atan2(dx, dz)
    rot_rf = _last_block(dat, r"forces \(fx,fy,fz\) for set ROT")
    moment = float(abs(rot_rf[0][2]))
    standoff = penetration = leg_overlap = 0.0
    if job.mode == "free":
        # the symmetry plane is the end face; the mirror leg is the strip reflected in it. Overlap = the inner face crossing that line.
        def pos(i, k):
            n = mesh.ids[(i, 0, k)]
            return np.array([mesh.nodes[n - 1][0] + ref[n][1], mesh.nodes[n - 1][2] + ref[n][3]])
        a, b = pos(nx, 0), pos(nx, K)                           # outer and inner node of the end face
        d = (b - a) / np.linalg.norm(b - a)
        nrm = np.array([-d[1], d[0]])
        side = np.sign(float((pos(nx - 2, K // 2) - a) @ nrm)) or 1.0       # which side of the line the strip body lies on
        dist = [side * float((pos(i, K) - a) @ nrm) for i in range(nx + 1)]
        leg_overlap = float(max(0.0, -min(dist)))
    if job.mode == "wrap":
        R = job.inside_radius_mm
        gaps = []
        for i in range(nx + 1):
            n = mesh.ids[(i, 0, K)]
            X, Z = mesh.nodes[n - 1][0] + ref[n][1], mesh.nodes[n - 1][2] + ref[n][3]
            if mesh.us[i] > -job.arc_mm:                    # inside the bend
                gaps.append((math.hypot(X, Z) if X > 0 else Z) - R)
        standoff = float(max(gaps)) if gaps else 0.0
        penetration = float(max(0.0, -min(gaps))) if gaps else 0.0
    skip = job.skip_mm if job.skip_mm is not None else 2.0 * max(job.total_thickness(u) for u in (job.u_start, 0.0))
    if job.skip_mm is None and job.mode == "wrap":
        skip = min(skip, 0.3 * job.arc_mm)                  # a tight bend is short: do not exclude all of it
    u_c = 0.5 * (mesh.us[1:] + mesh.us[:-1])
    return FoldResult(job, u_c, face, ang, mesh.us, moment, standoff, penetration, leg_overlap, k_contact, runtime, skip, tail)
