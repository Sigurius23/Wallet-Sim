import shutil

import pytest

from walletsim.fem.bending import BendingJob, analytic_outer_strain, run_bending

pytestmark = pytest.mark.fem
needs_ccx = pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")


def test_analytic_value():
    _, r_in, eps = analytic_outer_strain(1.0, 40.0, 180.0)
    assert r_in == pytest.approx(12.23, abs=0.01)
    assert eps == pytest.approx(0.0393, abs=0.0002)


@needs_ccx
@pytest.mark.parametrize("angle", [90.0, 180.0])
def test_fem_reproduces_pure_bending(angle):
    res = run_bending(BendingJob(angle_deg=angle))
    assert abs(res.relative_error) < 0.03        # within 3 % of eps = t/(2R+t)
    assert res.fem_min_strain < 0                # compression on the inside fibre
