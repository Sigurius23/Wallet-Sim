import pytest

from walletsim.fold_screen import inside_radius_for_strain, outer_fibre_strain, screen


@pytest.mark.parametrize("t,r,expected", [
    (0.8, 0.5, 0.444), (1.0, 0.5, 0.500), (1.0, 2.0, 0.200), (1.4, 3.0, 0.189), (2.5, 5.0, 0.200), (2.0, 5.0, 0.167),
])
def test_matches_the_reference_table(t, r, expected):
    # values from the strain table in prior-research/reference/durability.md
    assert outer_fibre_strain(t, r) == pytest.approx(expected, abs=0.001)


def test_inverse_roundtrip():
    assert outer_fibre_strain(1.2, inside_radius_for_strain(1.2, 0.15)) == pytest.approx(0.15)


def test_zero_radius_fold_is_flagged():
    s = screen(1.0, 0.0)
    assert s.strain == pytest.approx(1.0)
    assert any("below 1 x t" in f for f in s.flags)


def test_generous_radius_passes():
    assert screen(1.0, 3.0).flags == []


def test_bad_input_rejected():
    with pytest.raises(ValueError):
        outer_fibre_strain(0, 1)
