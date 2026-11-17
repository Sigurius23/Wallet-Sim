"""Overall wallet fold types: the plans (no solver) and the evaluation (CalculiX)."""
import shutil
from types import SimpleNamespace

import pytest

from walletsim.fold_styles import StyleParams, compare_styles, stack_inside_radius
from walletsim.wallet_types import (ALIASES, WALLET_TYPES, Contents, Fold, FoldOutcome, WalletResult, bifold, compare_wallet_types,
                                    evaluate_wallet, panel_thickness, plan_for, trifold, zfold, _job)
from walletsim.fold_styles import STYLES

needs_ccx = pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")
fem = pytest.mark.fem


# ---- plans and bookkeeping (no solver) ---------------------------------------------------------------------------

def test_contents_thickness_adds_cards_pocket_leather_and_extras():
    assert Contents(cards=8).thickness_mm == pytest.approx(8 * 0.76)
    assert Contents(cards=4, slot_leather_mm=0.5, extra_mm=1.0).thickness_mm == pytest.approx(4 * 1.26 + 1.0)


def test_panel_thickness_follows_the_layup():
    p = StyleParams(t=1.2, lining_t=0.5)
    assert panel_thickness(p, "plain") == pytest.approx(1.2)
    assert panel_thickness(p, "lined") == pytest.approx(1.7)
    assert panel_thickness(p, "skived") == pytest.approx(1.2)               # thickness away from the fold, not at the groove


def test_bifold_spine_wraps_all_the_contents():
    plan = bifold(Contents(cards=8), t_panel=1.2)
    assert len(plan.folds) == 1 and plan.folds[0].stack_mm == pytest.approx(6.08)
    assert plan.closed_thickness_mm == pytest.approx(6.08 + 2 * 1.2)
    assert plan.folds[0].sense == "out" and plan.folds[0].half_mm == pytest.approx(3.04)


def test_trifold_nests_the_outer_fold_around_the_inner_pack_plus_one_panel():
    plan = trifold(Contents(cards=8), t_panel=1.2, split=0.5)
    inner, outer = plan.folds
    assert inner.stack_mm == pytest.approx(3.04)
    assert outer.stack_mm == pytest.approx(6.08 + 1.2)                       # all the contents plus ONE folded-in panel
    assert outer.stack_mm > inner.stack_mm
    assert plan.closed_thickness_mm == pytest.approx(6.08 + 3 * 1.2)
    assert inner.sense == outer.sense == "out"                                # a letter fold has the grain outside on both
    skew = trifold(Contents(cards=8), 1.2, split=0.25)
    assert skew.folds[0].stack_mm == pytest.approx(0.25 * 6.08)
    with pytest.raises(ValueError):
        trifold(Contents(cards=8), 1.2, split=1.0)


def test_zfold_has_n_minus_one_alternating_folds_each_with_an_equal_share():
    plan = zfold(Contents(cards=9), t_panel=1.2, panels=4)
    assert [f.sense for f in plan.folds] == ["out", "in", "out"]
    assert all(f.stack_mm == pytest.approx(9 * 0.76 / 3) for f in plan.folds)
    assert plan.closed_thickness_mm == pytest.approx(9 * 0.76 + 4 * 1.2)
    with pytest.raises(ValueError):
        zfold(Contents(cards=9), 1.2, panels=2)


def test_registry_and_aliases_are_consistent():
    assert set(WALLET_TYPES) == {"bifold", "trifold", "z-fold"}
    assert all(v.split(" ")[0] in WALLET_TYPES for v in ALIASES.values())
    with pytest.raises(KeyError):
        plan_for("pentafold", Contents(), 1.2)


def test_grain_in_folds_are_run_reversed_with_the_inner_face_flat_and_box_spines_get_a_wall():
    layers = STYLES["lined"][0](StyleParams())
    job_in, rc, wall = _job(layers, Fold("f", 3.04, "in"), "round", None, 0.0)
    assert job_in.flat_face == "inner" and [l.name for l in job_in.layers] == ["lining", "shell"] and wall == 0.0
    job_out, *_ = _job(layers, Fold("f", 3.04, "out"), "round", None, 0.0)
    assert job_out.flat_face == "outer" and [l.name for l in job_out.layers] == ["shell", "lining"]
    job_box, rc, wall = _job(layers, Fold("f", 3.04, "out"), "box", 1.0, 0.1)
    assert rc == pytest.approx(1.0) and wall == pytest.approx(3.04 / 2 - 1.0) and job_box.tension_n_per_mm == 0.1


def _stub(strain_taut, strain_loose=None, grain=None):
    r = SimpleNamespace(peak_outer=strain_taut, peak_inner=-0.5 * strain_taut if grain is None else grain, moment_n_mm=1.0, standoff_mm=0.0)
    return r


def _result(folds_and_strains):
    outs = [FoldOutcome(f, f.half_mm, 0.0, _stub(s), _stub(s), s) for f, s in folds_and_strains]
    from walletsim.wallet_types import WalletPlan
    return WalletResult(WalletPlan("x", 3, tuple(f for f, _ in folds_and_strains), 10.0, ""), "plain", "round", outs)


def test_wears_first_reports_ties_instead_of_letting_the_last_digit_decide():
    r = _result([(Fold("a", 3, "out"), 0.1950), (Fold("b", 3, "in"), 0.1951), (Fold("c", 6, "out"), 0.14)])
    w = r.wears_first("tension")
    assert set(w["first"]) == {"a", "b"} and w["tied"]
    g = r.wears_first("grain")                                            # b is grain-in: its grain is compressed, so it counts as zero
    assert g["first"] == ["a"] and not g["tied"]


def test_different_cycles_can_change_who_wears_first_and_the_order_is_flagged_by_exponent():
    r = _result([(Fold("hard", 3, "out", cycles_per_use=1.0), 0.20), (Fold("busy", 6, "out", cycles_per_use=10.0), 0.14)])
    w = r.wears_first("tension")
    assert not w["tied"]
    assert w["stable"] is False                                            # 10x the cycles beats 1.43x the strain at m=3 but not at m=12
    assert w["rankings"][3.0][0] == "busy" and w["rankings"][12.0][0] == "hard"


def test_unknown_cycle_override_is_rejected():
    plan = bifold(Contents(cards=2), 1.2)
    with pytest.raises(KeyError):
        evaluate_wallet(plan, cycles={"nope": 2.0})


# ---- the solver ----------------------------------------------------------------------------------------------------

@fem
@needs_ccx
def test_a_bifold_spine_is_the_same_number_as_the_fold_styles_wrap_at_that_radius():
    p = StyleParams()
    res = evaluate_wallet(bifold(Contents(cards=5), panel_thickness(p, "plain")), p)
    ref = compare_styles(p, stack_inside_radius(5), styles=["plain"])[0]
    o = res.outcomes[0]
    assert o.radius_mm == pytest.approx(1.9)
    assert o.tension("taut") == pytest.approx(ref.wrap_taut.peak_outer, rel=1e-6)
    assert o.tension("loose") == pytest.approx(ref.wrap_loose.peak_outer, rel=1e-6)


@fem
@needs_ccx
def test_trifold_outer_fold_is_gentler_than_the_inner_one_and_zfold_folds_mirror_each_other():
    p = StyleParams()
    c = Contents(cards=6)
    tri, zf = compare_wallet_types([("trifold", {}), ("z-fold", {"panels": 3})], c, p)
    inner, outer = tri.outcomes
    assert outer.radius_mm > inner.radius_mm
    assert outer.tension("taut") < inner.tension("taut")                    # nesting: the outer fold wraps a bigger pack
    f1, f2 = zf.outcomes
    assert f1.tension("taut") == pytest.approx(f2.tension("taut"), abs=0.01)    # mirror folds of one leather
    assert f1.grain("taut") > 0 > f2.grain("taut")                          # grain in tension in fold 1, in compression in fold 2
    assert zf.wears_first("grain")["first"] == [f1.fold.name]               # only the grain-out fold can crack the grain
    assert zf.wears_first("tension")["tied"]


def test_folds_with_r_over_t_below_half_are_not_run_and_are_ranked_by_the_closed_form():
    from walletsim.fold_screen import outer_fibre_strain
    from walletsim.wallet_types import WalletPlan
    plan = WalletPlan("x", 3, (Fold("tight", 0.6, "out"), Fold("also tight", 0.4, "in")), 5.0, "")
    res = evaluate_wallet(plan, StyleParams(t=1.2))                             # radii 0.3 and 0.2 mm: R/t 0.25 and 0.17, no solver involved
    for o in res.outcomes:
        assert o.taut is None and o.loose is None and "closed form only" in o.note
        assert o.screen_strain == pytest.approx(outer_fibre_strain(1.2, o.radius_mm))
    assert res.worst.fold.name == "also tight"                                  # the smaller radius has the higher strain
    assert res.wears_first("tension")["first"] == ["also tight"]


def test_a_fold_whose_loose_leather_stands_off_by_more_than_its_radius_is_ranked_by_the_closed_form():
    ok = FoldOutcome(Fold("a", 3, "out"), 1.5, 0.0, _stub(0.15), _stub(0.17), 0.25)
    bridging = FoldOutcome(Fold("b", 1, "out"), 0.5, 0.0, SimpleNamespace(peak_outer=0.19, peak_inner=-0.1, moment_n_mm=1.0, standoff_mm=0.75),
                           _stub(0.206), 0.5)
    assert not ok.bridges and ok.screen_strain == pytest.approx(0.17)
    assert bridging.bridges and bridging.screen_strain == pytest.approx(0.5)
