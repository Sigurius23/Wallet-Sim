"""Measured and published leather cards, and the map of what is still unknown.

A card is one leather as a paper or a test describes it: species, tanning, how it was tested, and each property as a value with its source and spread. Cards live in ``cards/*.yaml`` so that
your own strip measurements can be added without touching code. ``coverage`` answers "how far are we": for every hide group and every property the simulator would need, which cards have it
(and none, where nobody has measured it). Nothing is filled in from a name: a card is evidence about the leather it describes and about no other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .species import GROUPS, NAMES, CLASS, classify

# The properties a complete picture of how a leather behaves in a fold needs. `key` is the card field.
PROPERTIES = [
    ("thickness_mm", "Thickness"),
    ("youngs_modulus_mpa", "Tensile stiffness"),
    ("bending_modulus_mpa", "Bending stiffness"),
    ("tensile_strength_mpa", "Tensile strength"),
    ("elongation_at_break_pct", "Elongation at break"),
    ("tear_strength_n_mm", "Tear strength"),
    ("grain_crack_strain", "Strain at grain crack"),
    ("direction", "Along vs across"),
    ("regions", "Hide-region effect"),
    ("ageing", "Aged states"),
]
PROVENANCE = ("measured", "literature", "assumed")


class CardError(ValueError):
    pass


@dataclass
class LeatherCard:
    id: str
    name: str
    species: str
    group: str | None
    tanning: str
    test: str
    cite: str
    props: dict = field(default_factory=dict)       # property key -> {value, cv, low, high, source, ref} or {tested, ratio, ...}
    not_this: list = field(default_factory=list)    # what this card must not be used for
    raw: dict = field(default_factory=dict)

    def has(self, key: str) -> bool:
        v = self.props.get(key)
        if v in (None, {}, []):
            return False
        if key in ("direction",):
            return isinstance(v, dict) and v.get("ratio") is not None
        if key in ("regions", "ageing"):
            return bool(v)
        return isinstance(v, dict) and v.get("value") is not None

    def partial(self, key: str) -> str | None:
        """For direction: the one direction that was tested, when no ratio exists."""
        v = self.props.get(key)
        if key == "direction" and isinstance(v, dict) and v.get("ratio") is None and v.get("tested"):
            return str(v["tested"])
        return None


def _check_value(card_id: str, key: str, v) -> None:
    if not isinstance(v, dict) or "value" not in v:
        return
    if v.get("source") not in PROVENANCE:
        raise CardError(f"{card_id}: {key} needs source: one of {PROVENANCE}")
    if not v.get("ref"):
        raise CardError(f"{card_id}: {key} needs a ref (the table, page or test it came from)")


def load_card(path: Path) -> LeatherCard:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for k in ("id", "name", "species", "test", "cite"):
        if k not in d:
            raise CardError(f"{path}: missing {k}")
    props = {k: d.get(k) for k, _ in PROPERTIES}
    for k, v in props.items():
        _check_value(d["id"], k, v)
    cls = classify(d["species"])
    return LeatherCard(d["id"], d["name"], str(d["species"]), cls.group, str(d.get("tanning", "unknown")), d["test"], d["cite"], props, list(d.get("not_this") or []), d)


def load_cards(folder: str | Path = "cards") -> list[LeatherCard]:
    p = Path(folder)
    return [load_card(f) for f in sorted(p.glob("*.yaml"))] if p.is_dir() else []


def coverage(cards: list[LeatherCard]) -> dict:
    """For every hide group and property: the ids of the cards that have it, the direction that was tested if no ratio exists, or nothing."""
    rows = []
    for key, name, cls, fname, _ in GROUPS:
        cells = {}
        for pk, _ in PROPERTIES:
            have = [c.id for c in cards if c.group == key and c.has(pk)]
            part = [c.id for c in cards if c.group == key and c.partial(pk)]
            cells[pk] = {"cards": have, "partial": part}
        rows.append({"group": key, "name": name, "hide_class": cls, "anatomy": fname, "n_cards": len([c for c in cards if c.group == key]), "cells": cells})
    filled = sum(1 for r in rows if r["hide_class"] == "sheet" for c in r["cells"].values() if c["cards"])
    total = sum(1 for r in rows if r["hide_class"] == "sheet" for _ in r["cells"])
    return {"properties": [{"key": k, "name": n} for k, n in PROPERTIES], "rows": rows, "sheet_cells_filled": filled, "sheet_cells_total": total}
