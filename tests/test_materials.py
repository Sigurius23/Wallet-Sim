import pytest

from walletsim.materials import LeatherMaterial, MaterialState, Value, scale_flexural_rigidity, calfskin_upper_literature


def test_value_validates_provenance_and_range():
    with pytest.raises(ValueError):
        Value(1.0, "guessed")
    with pytest.raises(ValueError):
        Value(5.0, "measured", low=1.0, high=2.0)
    with pytest.raises(ValueError):
        Value(1.0, "measured", low=0.5)
    assert Value(3.0, "literature", low=2.0, high=4.0).range == (2.0, 4.0)
    assert Value(3.0, "measured").range == (3.0, 3.0)


def test_flexural_rigidity_scales_with_the_exponent():
    assert scale_flexural_rigidity(1.0, 1.0, 2.0) == pytest.approx(8.0)                    # homogeneous plate, n = 3
    assert scale_flexural_rigidity(1.0, 1.0, 2.0, exponent=2.2) == pytest.approx(2 ** 2.2)   # a measured, lower exponent
    with pytest.raises(ValueError):
        scale_flexural_rigidity(1.0, 0.0, 2.0)


def test_literature_card_is_labelled_and_has_no_aged_state():
    card = calfskin_upper_literature()
    e = card.state("new").youngs_modulus_mpa
    assert e.source == "literature" and e.value == 72.0 and e.cv == 0.29 and "5107" in e.ref
    assert card.tanning == "unknown"      # the paper does not state it, so the card does not guess
    assert card.state("new").strain_to_crack is None
    with pytest.raises(KeyError):
        card.state("aged")          # ageing is never invented


def test_default_bending_exponent_is_marked_assumed():
    card = LeatherMaterial("x", "unknown", Value(1.0, "measured"))
    assert card.bending_exponent.source == "assumed"
    card.states["aged 28 d"] = MaterialState("aged 28 d", Value(80.0, "measured", ref="own strips"))
    assert card.state("aged 28 d").youngs_modulus_mpa.value == 80.0


def test_sampling_matches_the_stated_mean_and_cv():
    import numpy as np
    x = Value(50.0, "assumed", cv=0.4).sample(200_000, seed=1)
    assert x.mean() == pytest.approx(50.0, rel=0.02)
    assert x.std() / x.mean() == pytest.approx(0.4, rel=0.03)
    assert (x > 0).all()
    assert isinstance(x, np.ndarray)


def test_sampling_uses_the_range_when_there_is_no_cv_and_never_invents_spread():
    x = Value(40.0, "assumed", low=30.0, high=50.0).sample(10_000, seed=2)
    assert x.min() >= 30.0 and x.max() <= 50.0 and x.std() > 2
    assert (Value(7.0, "measured").sample(5) == 7.0).all()


def test_negative_cv_rejected():
    with pytest.raises(ValueError):
        Value(1.0, "measured", cv=-0.1)


def test_missing_windows_are_reported():
    card = LeatherMaterial("x", "chrome", Value(1.0, "measured"), windows={"tanning": "chrome, 3-5 % Cr2O3", "finishing": ""})
    assert card.missing_windows() == ["beamhouse", "post_tanning", "finishing"]
