"""Fold-style simulator: closed forms (no solver needed) and the FEM checks against them (need CalculiX)."""
import shutil

import numpy as np
import pytest

from walletsim.fem.fold import (FoldJob, Layer, analytic_free, analytic_wrap, build_fold_input, build_mesh, run_fold, section,
                                uniform, wrap_strain_closed_form)
from walletsim.fold_screen import outer_fibre_strain
from walletsim.fold_styles import (STYLES, StyleParams, compare_pleats, compare_styles, damage_rate_vs_reference, edge_turn_table,
                                   format_edge_turn_report, pleat_layers, skived, stack_inside_radius, turned_edge)

needs_ccx = pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")
fem = pytest.mark.fem


# ---- closed forms and model construction (no solver) --------------------------------------------------------------

def test_homogeneous_wrap_matches_the_textbook_formula():
    job = FoldJob((uniform("shell", 1.2, 72.0, 0.0),), "wrap", inside_radius_mm=3.0)
    a = analytic_wrap(job, 0.0)
    assert a["outer"] == pytest.approx(wrap_strain_closed_form(1.2, 3.0))
    assert a["inner"] == pytest.approx(-a["outer"])             # symmetric about mid-thickness for one layer


def test_a_soft_lining_barely_moves_the_neutral_axis_and_a_stiff_one_does():
    def na(ratio):
        job = FoldJob((uniform("shell", 1.2, 72.0, 0.0), uniform("lining", 0.5, 72.0 * ratio, 0.0, nz=2)), "free")
        return section(job, 0.0)["z_na"]
    shell_mid = 0.6
    assert na(1e-4) == pytest.approx(shell_mid, abs=0.01)       # lining carries nothing
    assert na(1.0) == pytest.approx(0.85, abs=1e-6)              # same leather: middle of the 1.7 mm stack
    assert na(10.0) > na(1.0)                                    # a stiff lining pulls the neutral axis toward itself (inward)


def test_lining_raises_tension_face_strain_at_a_given_stack():
    plain = FoldJob((uniform("shell", 1.2, 72.0, 0.0),), "wrap", inside_radius_mm=3.0)
    lined = FoldJob((uniform("shell", 1.2, 72.0, 0.0), uniform("lining", 0.5, 72.0, 0.0, nz=2)), "wrap", inside_radius_mm=3.0)
    assert analytic_wrap(lined, 0.0)["outer"] > analytic_wrap(plain, 0.0)["outer"]     # farther from the stack


def test_free_fold_closed_form_is_consistent():
    job = FoldJob((uniform("shell", 1.2, 72.0, 0.0),), "free", run_mm=15.0)
    a = analytic_free(job)
    assert a["angle"][-1] == pytest.approx(job.half_angle, rel=1e-3)          # the rotation adds up to half the fold
    # uniform strip: curvature = angle / length, moment = D * curvature
    d = section(job, 0.0)["D"]
    assert a["moment"] == pytest.approx(d * job.half_angle / 15.0, rel=1e-3)
    double_e = FoldJob((uniform("shell", 1.2, 144.0, 0.0),), "free", run_mm=15.0)
    assert analytic_free(double_e)["moment"] == pytest.approx(2 * a["moment"])     # moment scales with E
    assert analytic_free(double_e)["outer"][0] == pytest.approx(a["outer"][0])     # strain does not


def test_thinner_zone_collects_the_fold_in_the_closed_form():
    p = StyleParams()
    plain = FoldJob(STYLES["plain"][0](p), "free", run_mm=15.0)
    skv = FoldJob(skived(p), "free", run_mm=15.0)
    def centre_share(job):
        a = analytic_free(job)
        lo, hi = np.interp([-4.0, 0.0], a["u"], a["angle"])
        return (hi - lo) / a["angle"][-1]
    assert centre_share(plain) == pytest.approx(4 / 15, abs=0.01)
    assert centre_share(skv) > 2 * centre_share(plain)


def test_style_builders_put_the_thickness_where_they_say():
    p = StyleParams(t=1.2, skive_ratio=0.5)
    assert sum(l.thickness(0.0) for l in STYLES["skived"][0](p)) == pytest.approx(0.6)       # thin at the fold centre
    assert sum(l.thickness(-30.0) for l in STYLES["skived"][0](p)) == pytest.approx(1.2)     # full thickness in the panel
    assert sum(l.thickness(0.0) for l in STYLES["lined"][0](p)) == pytest.approx(1.2 + p.lining_t)
    hinge = STYLES["hinged"][0](p)[0]
    assert hinge.material_at(-1.0)[0] == pytest.approx(p.E * p.hinge_e_ratio)               # softer leather in the hinge
    assert hinge.material_at(-30.0)[0] == pytest.approx(p.E)


def test_deck_has_contact_only_for_a_wrap_and_a_rigid_end_in_both():
    layers = (uniform("shell", 1.2, 72.0, 0.0),)
    wrap, _ = build_fold_input(FoldJob(layers, "wrap", inside_radius_mm=3.0))
    free, _ = build_fold_input(FoldJob(layers, "free"))
    assert "*CONTACT PAIR" in wrap and "*CONTACT PAIR" not in free
    assert "*RIGID BODY" in wrap and "*RIGID BODY" in free
    assert "NLGEOM" in wrap and "C3D8I" in wrap


def test_wrap_strip_starts_with_its_inner_face_on_the_stack_even_when_thinner_at_the_fold():
    p = StyleParams()
    job = FoldJob(skived(p), "wrap", inside_radius_mm=3.0)
    mesh = build_mesh(job)
    k_last = len(mesh.row_layer)
    assert mesh.z[0, k_last] == pytest.approx(3.0)                     # tail: inner face exactly at the stack top
    assert mesh.z[-1, k_last] > 3.0 + 0.5                              # thin zone hangs above it until the fold closes it down


def test_unknown_style_and_helpers():
    with pytest.raises(KeyError):
        compare_styles(styles=["nonsense"])
    assert stack_inside_radius(5) == pytest.approx(1.9)
    lo, hi = damage_rate_vs_reference(0.5, 1.0)
    assert lo == pytest.approx(0.125) and hi == pytest.approx(0.5 ** 12)


# ---- the solver against the closed forms --------------------------------------------------------------------------

STYLE_SET = {
    "plain": (uniform("shell", 1.4, 38.0, 0.0),),
    "skived": (Layer("shell", ((-40, 1.4), (-6, 1.4), (-3, 0.6), (0, 0.6)), 38.0, 0.0, 4),),
    "lined": (uniform("shell", 1.4, 38.0, 0.0), uniform("lining", 0.6, 12.0, 0.0, nz=2)),
}


@fem
@needs_ccx
@pytest.mark.parametrize("name", list(STYLE_SET))
def test_free_fold_matches_the_composite_beam_closed_form(name):
    # Poisson 0 so the closed form's assumptions hold. Validated: moment within ~2 %, tension-face strain within ~3 %.
    job = FoldJob(STYLE_SET[name], "free", run_mm=15.0)
    r, a = run_fold(job), analytic_free(job)
    assert r.moment_n_mm == pytest.approx(a["moment"], rel=0.04)
    w = r.window()
    closed = np.interp(r.u, a["u"], a["outer"])
    assert np.abs(r.outer_strain[w] - closed[w]).max() < 0.04 * np.abs(closed[w]).max()
    assert r.angle[-1] == pytest.approx(job.half_angle, abs=1e-4)         # the end really turned through half the fold
    assert r.peak_inner < 0 < r.peak_outer


@fem
@needs_ccx
def test_skived_fold_collects_in_the_thin_zone_like_the_closed_form_says():
    plain = run_fold(FoldJob(STYLE_SET["plain"], "free", run_mm=15.0))
    skv = run_fold(FoldJob(STYLE_SET["skived"], "free", run_mm=15.0))
    assert plain.angle_share(-4, 0) == pytest.approx(4 / 15, abs=0.02)
    assert skv.angle_share(-4, 0) > 0.6
    assert skv.moment_n_mm < 0.5 * plain.moment_n_mm                    # and it closes with far less effort
    assert skv.peak_outer > plain.peak_outer                            # at the same strip length the thin zone strains MORE


@fem
@needs_ccx
@pytest.mark.parametrize("name", ["plain", "lined"])
def test_wrap_matches_the_taut_closed_form_where_the_leather_hugs_the_stack(name):
    # A gentle radius (R = 8 mm), so the bend is long enough to develop. Developed zone only; within 4 %.
    job = FoldJob(STYLE_SET[name], "wrap", inside_radius_mm=8.0, skip_mm=3.0)
    r = run_fold(job)
    w = r.window()
    closed = np.array([analytic_wrap(job, u)["outer"] for u in r.u[w]])
    assert r.outer_strain[w].max() == pytest.approx(closed.max(), rel=0.04)
    assert r.penetration_mm < 0.02


@fem
@needs_ccx
def test_a_tight_stack_is_not_fully_hugged_without_tension_and_more_pull_closes_the_gap():
    layers = (uniform("shell", 1.2, 72.0, 0.3),)
    loose = run_fold(FoldJob(layers, "wrap", inside_radius_mm=1.9))
    taut = run_fold(FoldJob(layers, "wrap", inside_radius_mm=1.9, tension_n_per_mm=0.5))
    limit = wrap_strain_closed_form(1.2, 1.9)
    assert loose.standoff_mm > 0.3                                       # R/t = 1.6: bridges the stack
    assert taut.standoff_mm < loose.standoff_mm
    assert loose.peak_outer < limit                                      # the textbook value is an upper bound here


@fem
@needs_ccx
def test_results_are_mesh_converged_to_a_few_percent():
    layers = STYLE_SET["lined"]
    a = run_fold(FoldJob(layers, "wrap", inside_radius_mm=3.0, tension_n_per_mm=0.1, dx_mm=0.5))
    b = run_fold(FoldJob(layers, "wrap", inside_radius_mm=3.0, tension_n_per_mm=0.1, dx_mm=0.25))
    assert b.peak_outer == pytest.approx(a.peak_outer, rel=0.04)
    assert b.moment_n_mm == pytest.approx(a.moment_n_mm, rel=0.06)


# ---- grain-in folds, the gusset pleat and the turned edge -----------------------------------------------------------

def test_flat_inner_face_keeps_the_inner_face_flat_and_the_outer_face_dips():
    job = FoldJob(skived(StyleParams()), "wrap", inside_radius_mm=3.0, flat_face="inner")
    mesh = build_mesh(job)
    K = len(mesh.row_layer)
    assert np.allclose(mesh.z[:, K], 3.0)                               # inner face on the stack everywhere
    assert mesh.z[-1, 0] < mesh.z[0, 0] - 0.5                           # outer face dips where the leather is skived
    with pytest.raises(ValueError):
        build_mesh(FoldJob(skived(StyleParams()), "free", flat_face="middle"))


def test_turned_edge_is_a_shell_plus_a_lip_of_the_same_leather():
    p = StyleParams(t=1.2, lip_ratio=0.5)
    layers = turned_edge(p)
    assert [l.name for l in layers] == ["shell", "lip"]
    assert layers[1].thickness(0.0) == pytest.approx(0.6)
    assert layers[1].youngs_modulus_mpa == layers[0].youngs_modulus_mpa      # same leather
    plain = FoldJob(STYLES["plain"][0](p), "wrap", inside_radius_mm=3.0)
    hem = FoldJob(layers, "wrap", inside_radius_mm=3.0)
    assert analytic_wrap(hem, 0.0)["outer"] > 1.2 * analytic_wrap(plain, 0.0)["outer"]   # the double layer strains the shell more


def test_edge_turn_table_is_the_kinematic_formula_and_is_flagged():
    rows = edge_turn_table(1.2, skive_ratios=(1.0, 0.5), cores=(0.6, 0.3))
    assert len(rows) == 4
    for r in rows:
        assert r.strain == pytest.approx(outer_fibre_strain(r.t_turn_mm, r.inside_radius_mm))
        assert r.flags and r.strain > 0.30                                      # nowhere near the elastic range
        assert outer_fibre_strain(r.max_thickness_for_20pct_mm, r.inside_radius_mm) == pytest.approx(0.20)
    assert "no permanent set" in format_edge_turn_report(rows, 1.2)
    thinner = [r.strain for r in rows if r.core_mm == 0.6]
    assert thinner[1] < thinner[0]                                              # skiving lowers the kinematic strain


def test_unknown_pleat_layup_is_rejected():
    with pytest.raises(KeyError):
        pleat_layers(StyleParams(), "nonsense")


@fem
@needs_ccx
def test_grain_in_free_fold_is_the_mirror_of_grain_out_for_one_leather():
    layers = (uniform("shell", 1.4, 72.0, 0.0),)
    out = run_fold(FoldJob(layers, "free", run_mm=15.0, flat_face="outer"))
    inn = run_fold(FoldJob(layers, "free", run_mm=15.0, flat_face="inner"))
    assert inn.peak_inner == pytest.approx(out.peak_inner, rel=0.02)
    assert inn.moment_n_mm == pytest.approx(out.moment_n_mm, rel=0.01)
    assert inn.peak_outer == pytest.approx(out.peak_outer, rel=0.02)            # same layup, same fold: which face stays flat is only the reference shape


@fem
@needs_ccx
def test_reversed_lined_layup_with_flat_inner_face_matches_the_composite_beam():
    layers = tuple(reversed(STYLE_SET["lined"]))
    job = FoldJob(layers, "free", run_mm=15.0, flat_face="inner")
    r, a = run_fold(job), analytic_free(job)
    assert r.moment_n_mm == pytest.approx(a["moment"], rel=0.04)
    w = r.window()
    closed = np.interp(r.u, a["u"], a["outer"])
    assert np.abs(r.outer_strain[w] - closed[w]).max() < 0.04 * np.abs(closed[w]).max()


@fem
@needs_ccx
def test_pleat_groove_creates_a_tight_crease_and_strain_follows_the_fold_angle():
    res = compare_pleats(StyleParams(), angles=(180.0, 90.0), layups=("plain", "grooved"))
    d = {(r.layup, r.fold_deg): r for r in res}
    assert d[("grooved", 180.0)].crease_radius_mm() < 0.35 * d[("plain", 180.0)].crease_radius_mm()
    assert d[("grooved", 180.0)].grain1 > 2 * d[("plain", 180.0)].grain1       # the groove concentrates the fold
    g180, g90 = d[("grooved", 180.0)], d[("grooved", 90.0)]
    assert g180.crease_radius_mm() * 180 == pytest.approx(g90.crease_radius_mm() * 90, rel=0.08)   # curvature proportional to the angle
    assert g90.grain1 < g180.grain1
    assert g180.grain1 > 0 > g180.grain2                                         # grain in tension in fold 1, in compression in fold 2
    plain = d[("plain", 180.0)]
    assert abs(plain.grain2) == pytest.approx(plain.grain1, rel=0.12)           # mirror folds of one leather, up to tension/compression asymmetry
    assert all(r.fold1.leg_overlap_mm < 0.02 and r.fold2.leg_overlap_mm < 0.02 for r in res)
