import math

import pytest

from walletsim.damage import Exposure, fit_law, rank_locations


def test_ranking_is_stable_when_one_location_dominates():
    r = rank_locations({"spine": Exposure(0.20, 1), "slot edge": Exposure(0.08, 1), "corner": Exposure(0.05, 1)})
    assert r["stable"] and r["order"] == ["spine", "slot edge", "corner"]


def test_ranking_flips_with_the_exponent_when_strain_and_frequency_trade_off():
    # spine: high strain, once per use. slot edge: half the strain, 100 cycles per use.
    # rate ratio spine/slot = 2^m / 100  ->  slot edge wins for m=3,5 and spine wins for m=8,12
    r = rank_locations({"spine": Exposure(0.20, 1), "slot edge": Exposure(0.10, 100)})
    assert not r["stable"] and r["order"] is None
    assert r["rankings"][3.0][0] == "slot edge" and r["rankings"][12.0][0] == "spine"


def test_fit_recovers_a_synthetic_law():
    a, m = 2.0e3, 4.0
    strains = [0.05, 0.08, 0.12, 0.2]
    cycles = [a * s ** (-m) for s in strains]
    law = fit_law(strains, cycles)
    assert law.exponent == pytest.approx(m, rel=1e-6)
    assert law.coefficient == pytest.approx(a, rel=1e-6)
    assert law.r_squared == pytest.approx(1.0)


def test_extrapolation_is_flagged():
    law = fit_law([0.05, 0.1, 0.2], [1e6, 1e5, 1e4])
    assert not law.cycles_to_crack(0.1)["extrapolated"]
    assert law.cycles_to_crack(0.5)["extrapolated"]


def test_damage_fraction():
    law = fit_law([0.05, 0.1, 0.2], [1e6, 1e5, 1e4])
    assert law.damage(0.1, 5e4) == pytest.approx(0.5, rel=1e-6)


def test_refuses_underdetermined_fit():
    with pytest.raises(ValueError):
        fit_law([0.1, 0.11], [1e5, 9e4])
    with pytest.raises(ValueError):
        fit_law([0.1, 0.101, 0.102], [1e5, 9e4, 8e4])
