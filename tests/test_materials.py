import pytest

from walletsim.materials import LeatherMaterial, MaterialState, Value, scale_flexural_rigidity, vegetable_tanned_literature


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
    card = vegetable_tanned_literature()
    e = card.state("new").youngs_modulus_mpa
    assert e.source == "literature" and e.range == (24.0, 53.0)
    assert card.state("new").strain_to_crack is None
    with pytest.raises(KeyError):
        card.state("aged")          # ageing is never invented


def test_default_bending_exponent_is_marked_assumed():
    card = LeatherMaterial("x", "unknown", Value(1.0, "measured"))
    assert card.bending_exponent.source == "assumed"
    card.states["aged 28 d"] = MaterialState("aged 28 d", Value(80.0, "measured", ref="own strips"))
    assert card.state("aged 28 d").youngs_modulus_mpa.value == 80.0
