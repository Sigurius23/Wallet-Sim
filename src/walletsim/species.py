"""Which kind of hide is this, and can the sheet model be applied to it?

The anatomy library (``prior-research/reference/anatomy/``) groups hides by what the skin is made of. For the simulator the one question that matters is whether the leather
behaves as a **sheet** (fibrous, bendable all over: cow, horse, sheep, goat, pig, deer, food-fish skins) or as a **composite** (hard plates or scales in a soft matrix: crocodilian,
snake and lizard, stingray). The library is explicit that plated hides are composites where failure is an interface problem, so the sheet-based fold model must not be applied to them.

* ``sheet``      the fold model applies, with the usual caveats (one material card, no direction or region effects yet)
* ``caution``    some of the hide is a sheet and some is not, or the hide is defined by something the model does not have (ostrich, elephant, toad, turtle): not validated
* ``composite``  plates or scales: the sheet model is refused
* ``unknown``    the species text matches nothing; say so and do not guess

A classification is read from the record's species text and says which anatomy file backs it. It never changes a number; it only decides whether a result may be shown.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (group key, display name, hide class, anatomy file, regex on the species text). Order matters: the first match wins.
GROUPS = [
    ("crocodilian", "Crocodile, alligator, caiman", "composite", "crocodilian.md", r"crocodil|alligator|caiman|gator"),
    ("reptile-snake", "Snake and lizard", "composite", "reptile-snake.md", r"snake|python|cobra|\bboa\b|lizard|teju|reptile|monitor"),
    ("stingray", "Stingray (armour)", "composite", "fish-stingray.md", r"stingray|galuchat|shagreen|\bray\b"),
    ("ostrich", "Ostrich", "caution", "ostrich.md", r"ostrich"),
    ("amphibian-shell", "Toad, turtle, frog", "caution", "amphibian-shell.md", r"\btoad|turtle|tortoise|\bfrog"),
    ("heavy-exotics", "Elephant, hippo, yak, walrus", "caution", "heavy-exotics.md", r"elephant|hippo|\byak\b|walrus"),
    ("porcine", "Pig, hog, peccary", "sheet", "porcine.md", r"porcin|\bpigs?\b|\bhog|swine|peccary"),
    ("caprine", "Goat, kid", "sheet", "ovine-caprine.md", r"caprin|\bgoats?\b|\bkids?\b"),
    ("ovine", "Sheep, lamb", "sheet", "ovine-caprine.md", r"\bovin|sheep|\blamb|merino"),
    ("equine", "Horse, pony, donkey", "sheet", "equine.md", r"equin|horse|pony|ponies|colt|donkey|\bmule"),
    ("bovine", "Cow, calf, steer, buffalo", "sheet", "bovine.md", r"bovin|\bcows?\b|\bcalf|\bcalves|\bkip\b|steer|\bbulls?\b|\box\b|\boxen\b|buffalo|bison|zebu|cattle"),
    ("poultry", "Emu, rhea, chicken, duck, goose", "sheet", "poultry.md", r"\bemu\b|\brhea\b|chicken|turkey|\bduck|\bgoose|poultry"),
    ("shark", "Shark", "sheet", "fish-stingray.md", r"shark"),
    ("fish", "Food fish: salmon, perch, tilapia, cod, eel", "sheet", "fish-stingray.md",
     r"\bfish|salmon|\bcod\b|haddock|perch|tilapia|pirarucu|\beel\b|sturgeon|wolffish|catfish|carp|plaice|hake"),
    ("deer-kangaroo-other", "Deer, kangaroo, camel, rabbit, seal", "sheet", "kangaroo-deer-other.md", r"deer|\belk\b|moose|kangaroo|camel|llama|alpaca|rabbit|\bseal\b"),
]
NAMES = {g[0]: g[1] for g in GROUPS}
CLASS = {g[0]: g[2] for g in GROUPS}

WHY = {
    "composite": "Plates or scales sit in a soft matrix, and failure is an interface problem (the plates lift or the soft zone between them tears). The sheet-based fold model does not describe it and is not run.",
    "caution": "Part of this hide is not a sheet, or what defines it (surface structure, thickness) is outside the model. The fold model is not validated for it.",
    "sheet": "A fibrous sheet that bends all over: the fold model applies, with the caveats that every leather shares today (one placeholder stiffness, no direction or region effects).",
    "unknown": "The species is not recorded, or its text matches no known hide group, so no class is assigned.",
}


@dataclass(frozen=True)
class Classification:
    group: str | None
    name: str
    hide_class: str            # sheet | caution | composite | unknown
    anatomy_file: str | None
    why: str


def classify(species: str | None) -> Classification:
    text = str(species or "").lower()
    if text and text != "unknown":
        for key, name, cls, fname, rx in GROUPS:
            if re.search(rx, text):
                return Classification(key, name, cls, fname, WHY[cls])
    return Classification(None, "Unknown", "unknown", None, WHY["unknown"])


def species_of(raw: dict) -> str | None:
    """The shell leather's species text from a wallet record's raw dict (a leaf with a value, a bare string, or missing)."""
    shell = next((l for l in raw.get("leather", []) if isinstance(l, dict) and l.get("id") == "shell"), None)
    sp = (shell or {}).get("species")
    return sp.get("value") if isinstance(sp, dict) else sp
