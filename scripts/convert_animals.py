"""Convert the CC0 Quaternius farm-animal OBJ models into the compact JSON the archive app embeds.

Source: "Farm Animals Pack" by Quaternius, CC0 1.0 Universal (public domain dedication), https://opengameart.org/content/lowpoly-animated-farm-animal-pack
Download:  https://opengameart.org/sites/default/files/Farm%20Animals%20by%20%40Quaternius.zip  (OBJ folder: Cow, Pig, Horse, Sheep)

Each model is reoriented to x forward (head at +x), y up (feet at 0), z lateral, scaled so its body length is 2.6 units, and stored as flat triangles
(float32 positions, base64) with its bounding box. Colours and materials are dropped: the app draws every animal in one neutral material.

    python scripts/convert_animals.py "Farm Animals by @Quaternius/OBJ" src/walletsim/assets/animals.json
"""
import base64
import json
import struct
import sys
from pathlib import Path

MODELS = {"bovine": "Cow", "porcine": "Pig", "equine": "Horse", "ovine": "Sheep"}
LENGTH = 2.6


def load(path: Path):
    V, F = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            V.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith("f "):
            idx = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
            for k in range(1, len(idx) - 1):
                F.append((idx[0], idx[k], idx[k + 1]))
    return V, F


def convert(src: Path) -> dict:
    out = {}
    for key, name in MODELS.items():
        V, F = load(src / f"{name}.obj")
        # source frame: y up, body along z with the head toward +z, width along x  ->  head at +x, y up, z lateral
        V = [(z, y, x) for (x, y, z) in V]
        xs, ys, zs = zip(*V)
        s = LENGTH / (max(xs) - min(xs))
        cx = (max(xs) + min(xs)) / 2
        V = [((x - cx) * s, (y - min(ys)) * s, z * s) for (x, y, z) in V]
        flat = [c for f in F for i in f for c in V[i]]
        xs, ys, zs = zip(*V)
        out[key] = {"source": f"{name}.obj", "triangles": len(F), "bbox": [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)],
                    "positions": base64.b64encode(struct.pack(f"<{len(flat)}f", *flat)).decode()}
    return {"license": "CC0 1.0 Universal", "author": "Quaternius", "title": "Farm Animals Pack",
            "url": "https://opengameart.org/content/lowpoly-animated-farm-animal-pack", "models": out}


if __name__ == "__main__":
    data = convert(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(data, separators=(",", ":")))
    print({k: v["triangles"] for k, v in data["models"].items()}, Path(sys.argv[2]).stat().st_size, "bytes")
