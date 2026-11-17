import shutil

import pytest

from walletsim.fem.bending import BendingJob, analytic_outer_strain, job_for_inside_radius, run_bending, surface_factor

pytestmark = pytest.mark.fem
needs_ccx = pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")


def test_analytic_value():
    _, r_in, eps = analytic_outer_strain(1.0, 40.0, 180.0)
    assert r_in == pytest.approx(12.23, abs=0.01)
    assert eps == pytest.approx(0.0393, abs=0.0002)


def test_surface_factor_goes_to_one_with_refinement():
    assert surface_factor(4) == pytest.approx(1.118, abs=0.001)
    assert surface_factor(4) > surface_factor(8) > 1.0


@needs_ccx
@pytest.mark.parametrize("angle", [90.0, 180.0])
def test_fem_reproduces_the_closed_form_when_its_assumptions_hold(angle):
    # Poisson 0: no anticlastic curvature, which the closed form ignores. Strain within 3 %, moment within 2 %.
    res = run_bending(BendingJob(angle_deg=angle, poisson=0.0))
    assert abs(res.relative_error) < 0.03
    assert res.moment_ratio == pytest.approx(1.0, abs=0.02)
    assert res.fem_min_strain < 0                 # compression on the inside fibre


@needs_ccx
def test_poisson_contraction_raises_strain_and_stiffness():
    # With Poisson 0.3 the constrained ends stiffen the strip and the middle bends tighter: both go UP relative to the
    # closed form. This is real 3D behaviour, not solver error (the Poisson-0 run above agrees with theory).
    flat = run_bending(BendingJob(poisson=0.0))
    real = run_bending(BendingJob(poisson=0.3))
    assert real.fem_max_strain > 1.05 * flat.fem_max_strain
    assert 1.02 < real.moment_ratio < 1.12


@needs_ccx
def test_bending_moment_follows_the_thickness_cubed_law_at_fixed_radius():
    # Fixed inside radius 3 mm. Beam theory: M ~ t^3 / R_neutral. FEM uses neo-Hooke, so finite-strain effects (strain up
    # to 26 %) lower the thick case slightly; within 8 % of beam theory across a 3.3x thickness range.
    thin = run_bending(job_for_inside_radius(0.6, 3.0, poisson=0.0))
    thick = run_bending(job_for_inside_radius(2.0, 3.0, poisson=0.0))
    fem_ratio = thick.fem_moment_n_mm / thin.fem_moment_n_mm
    beam_ratio = thick.analytic_moment_n_mm / thin.analytic_moment_n_mm
    assert fem_ratio == pytest.approx(beam_ratio, rel=0.08)
    assert thick.fem_max_strain > thin.fem_max_strain
