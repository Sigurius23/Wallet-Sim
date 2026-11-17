"""A self-contained HTML page for one wallet report: the strain at each fold and how uncertain it is, the folds as pictures, the ranges, the failure modes.

Everything on the page is read from a saved run (``wallets/<id>/sim/run-<hash>/result.json`` and its figures), and the sentences that state a finding
are computed from those numbers, so the page cannot disagree with the report. Images are embedded, so the file can be opened or published as is.
"""
from __future__ import annotations

import base64
import html
import json
import math
from pathlib import Path

from .record import load_wallet, measure_first

E = html.escape
STRAIN_LINE = 0.20


def _pct(x, nd: int = 0) -> str:
    if x is None:
        return "n/a"
    return f"{math.floor(100 * x + 0.5):d} %" if nd == 0 else f"{100 * x:.{nd}f} %"       # halves round up, so 12.5 % reads 13 %, as the report's 12.5


def _short(name: str) -> str:
    return name.split(" (")[0].strip().capitalize()


def _wrap(text: str, width: int) -> list[str]:
    """Break a label at spaces into at most three lines of about `width` characters (a hyphenated word may also break after its hyphen)."""
    out: list[str] = []
    cur = ""
    for w in text.replace("-", "- ").split():
        glue = "" if cur.endswith("-") else " "
        if cur and len(cur) + len(glue) + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur}{glue}{w}" if cur else w
    out.append(cur)
    return [ln.replace("- ", "-") for ln in out[:3]]


def latest_run(wallet_dir: str | Path) -> Path:
    runs = sorted((Path(wallet_dir) / "sim").glob("run-*"), key=lambda p: p.stat().st_mtime)
    if not runs:
        raise FileNotFoundError(f"no run under {wallet_dir}/sim; run `walletsim wallet-report` first")
    return runs[-1]


def _chart(rows: list[dict]) -> str:
    W, H, L, R, T, B = 760, 70 + 62 * len(rows), 168, 30, 38, 52
    xmax = max(0.70, min(1.0, max(r["hi"] for r in rows) * 1.08))
    sx = lambda v: L + (W - L - R) * v / xmax
    rowh = (H - T - B) / len(rows)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Strain at each fold across the range of its stack">']
    s.append(f'<rect x="{sx(STRAIN_LINE):.1f}" y="{T - 8}" width="{sx(xmax) - sx(STRAIN_LINE):.1f}" height="{H - T - B + 8}" class="zone"/>')
    v = 0.0
    while v <= xmax + 1e-9:
        s.append(f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{T - 8}" y2="{H - B}" class="grid"/>')
        s.append(f'<text x="{sx(v):.1f}" y="{H - B + 18}" class="tick" text-anchor="middle">{int(round(v * 100))} %</text>')
        v += 0.1
    s.append(f'<text x="{sx((STRAIN_LINE + xmax) / 2):.1f}" y="{T - 16}" class="zonelabel" text-anchor="middle">above the 20 % screening line</text>')
    s.append(f'<text x="{(L + W - R) / 2:.1f}" y="{H - 8}" class="axis" text-anchor="middle">strain on the outside face of the fold</text>')
    for k, r in enumerate(rows):
        y = T + rowh * k + rowh / 2
        lines = _wrap(r["name"], 17)                                      # the label column is ~150 px wide: long names take two lines instead of running off the left edge
        top = y - 4 - 15 * (len(lines) - 1)
        for j, ln in enumerate(lines):
            s.append(f'<text x="{L - 14}" y="{top + 15 * j:.1f}" class="rowname" text-anchor="end">{E(ln)}</text>')
        rng = f"{r['stack_lo']:g} to {r['stack_hi']:g} mm" if r["stack_lo"] != r["stack_hi"] else f"{r['stack_lo']:g} mm"
        s.append(f'<text x="{L - 14}" y="{y + 12:.1f}" class="rowsub" text-anchor="end">wraps {rng}</text>')
        s.append(f'<line x1="{sx(r["lo"]):.1f}" x2="{sx(r["hi"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="range"/>')
        s.append(f'<circle cx="{sx(r["rec"]):.1f}" cy="{y:.1f}" r="7" class="rec"/>')
        s.append(f'<text x="{sx(r["rec"]):.1f}" y="{y - 14:.1f}" class="val" text-anchor="middle">{_pct(r["rec"])}</text>')
        if r["lo"] != r["rec"]:
            s.append(f'<text x="{sx(r["lo"]) - 6:.1f}" y="{y + 4:.1f}" class="end" text-anchor="end">{_pct(r["lo"])}</text>')
        if r["hi"] != r["rec"]:
            s.append(f'<text x="{sx(r["hi"]) + 6:.1f}" y="{y + 4:.1f}" class="end" text-anchor="start">{_pct(r["hi"])}</text>')
        if r["fem"] is not None:
            cls = "fem hollow" if r["bridges"] else "fem"
            s.append(f'<path d="M{sx(r["fem"]):.1f} {y + 18:.1f} l6 7 l-6 7 l-6 -7z" class="{cls}"/>')
            s.append(f'<text x="{sx(r["fem"]) + 12:.1f}" y="{y + 29:.1f}" class="femval">{_pct(r["fem"])}</text>')
    s.append("</svg>")
    return "\n".join(s)


CSS = """
:root {
  --bg: #f2f3f4; --surface: #ffffff; --fg: #17191b; --muted: #5d646b; --line: #d9dcdf;
  --accent: #b3261e; --ink2: #1d5ba1; --warn: #9a5b00; --warnbg: #fbf0dc; --okbg: #e8f1ea; --ok: #2d6a3e; --zone: #f6e3e1; --grid: #e4e6e8;
  --display: "Space Grotesk", "Helvetica Neue", Arial, sans-serif; --body: Inter, "Helvetica Neue", Arial, sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #121416; --surface: #1b1e21; --fg: #e9eaeb; --muted: #9aa1a8; --line: #33383d; --accent: #ef6a60; --ink2: #6fa5e6;
  --warn: #e8b560; --warnbg: #3a2e18; --okbg: #1c2e22; --ok: #7fc293; --zone: #3a1f1d; --grid: #2a2e32; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #121416; --surface: #1b1e21; --fg: #e9eaeb; --muted: #9aa1a8; --line: #33383d; --accent: #ef6a60; --ink2: #6fa5e6;
  --warn: #e8b560; --warnbg: #3a2e18; --okbg: #1c2e22; --ok: #7fc293; --zone: #3a1f1d; --grid: #2a2e32; color-scheme: dark; }
body { background: var(--bg); color: var(--fg); font-family: var(--body); line-height: 1.55; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
main { max-width: 980px; margin: 0 auto; display: grid; gap: 34px; }
h1, h2, h3 { font-family: var(--display); letter-spacing: -0.01em; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(1.9rem, 5vw, 2.8rem); line-height: 1.08; font-weight: 700; } h2 { font-size: 1.3rem; font-weight: 600; } h3 { font-size: 1.15rem; font-weight: 600; }
.eyebrow { font-size: .78rem; letter-spacing: .09em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }
.lede { font-size: 1.05rem; max-width: 62ch; margin: 12px 0 0; }
.banner { background: var(--warnbg); color: var(--warn); border-radius: 6px; padding: 12px 16px; font-size: .93rem; max-width: 80ch; }
section { display: grid; gap: 14px; min-width: 0; } .sub { color: var(--muted); font-size: .93rem; max-width: 72ch; margin: 0; }
.chartwrap { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px 14px 8px; overflow-x: auto; }
.chart { width: 100%; min-width: 620px; height: auto; display: block; }
.chart .zone { fill: var(--zone); } .chart .grid { stroke: var(--grid); stroke-width: 1; }
.chart .tick, .chart .rowsub, .chart .axis, .chart .end { fill: var(--muted); font: 11.5px var(--body); }
.chart .zonelabel { fill: var(--accent); font: 600 11.5px var(--body); } .chart .rowname { fill: var(--fg); font: 600 14px var(--display); }
.chart .val { fill: var(--fg); font: 600 12.5px var(--body); font-variant-numeric: tabular-nums; }
.chart .femval { fill: var(--ink2); font: 600 12px var(--body); font-variant-numeric: tabular-nums; }
.chart .range { stroke: var(--accent); stroke-width: 3; opacity: .45; stroke-linecap: round; }
.chart .rec { fill: var(--accent); } .chart .fem { fill: var(--ink2); } .chart .fem.hollow { fill: var(--surface); stroke: var(--ink2); stroke-width: 2; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: .84rem; color: var(--muted); padding: 4px 4px 10px; }
.legend span::before { content: ""; display: inline-block; width: 12px; height: 12px; margin-right: 7px; vertical-align: -1px; }
.legend .l1::before { background: var(--accent); border-radius: 50%; } .legend .l2::before { background: var(--accent); opacity: .45; height: 4px; vertical-align: 3px; width: 20px; border-radius: 2px; }
.legend .l3::before { background: var(--ink2); transform: rotate(45deg) scale(.8); } .legend .l4::before { border: 2px solid var(--ink2); transform: rotate(45deg) scale(.7); }
.fold { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 20px; align-items: start; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
.plate { background: #fff; border-radius: 4px; padding: 6px; } .plate img { display: block; width: 100%; height: auto; }
.noplate { background: var(--bg); border: 1px dashed var(--line); border-radius: 4px; padding: 26px 14px; color: var(--muted); font-size: .88rem; text-align: center; }
.foldtext { display: grid; gap: 10px; min-width: 0; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; margin: 0; font-size: .92rem; } dt { color: var(--muted); } dd { margin: 0; font-variant-numeric: tabular-nums; }
.warn, .ok { font-size: .88rem; padding: 8px 12px; border-radius: 5px; margin: 0; } .warn { background: var(--warnbg); color: var(--warn); } .ok { background: var(--okbg); color: var(--ok); }
summary { cursor: pointer; font-size: .88rem; color: var(--muted); } details .plate { margin-top: 8px; }
.scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: .88rem; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-weight: 600; font-size: .78rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }
tr:last-child td { border-bottom: 0; } tr.rec td { background: color-mix(in srgb, var(--accent) 7%, transparent); font-weight: 500; }
.fm td:nth-child(1) { color: var(--muted); } .fm td:nth-child(2) { white-space: nowrap; } .fm td:nth-child(4) { min-width: 280px; }
.pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: .78rem; font-weight: 600; white-space: nowrap; border: 1px solid transparent; }
.p-computed { background: color-mix(in srgb, var(--ink2) 16%, transparent); color: var(--ink2); } .p-flagged { background: var(--warnbg); color: var(--warn); }
.p-unknown { border: 1px dashed var(--muted); color: var(--muted); } .p-not-modelled, .p-not-triggered { background: color-mix(in srgb, var(--muted) 14%, transparent); color: var(--muted); }
ol { margin: 0; padding-left: 1.2em; display: grid; gap: 8px; max-width: 78ch; }
footer { color: var(--muted); font-size: .82rem; border-top: 1px solid var(--line); padding-top: 14px; max-width: 90ch; }
@media (max-width: 720px) { .fold { grid-template-columns: minmax(0, 1fr); } }
"""

BANNERS = {
    "photos-only": "Built from the retailer's text, product photographs and any measurements a seller stated. Nothing is measured here.",
    "design": "This record is a generated design, not a measured wallet.",
    "measured": "",
}


def build_page(run_dir: str | Path) -> str:
    run = Path(run_dir)
    d = json.loads((run / "result.json").read_text())
    rec = load_wallet(run.parents[1])
    folds, sweeps = d["folds"], d["sweeps"]
    # ---- chart rows
    rows = []
    for f in folds:
        mine = [s for s in sweeps if s["fold"] == f["fold"]]
        vals = [f["closed_form"]] + [s["closed_form"] for s in mine]
        stacks = [f["stack_mm"]] + [s["stack_mm"] for s in mine]
        rows.append({"name": _short(f["fold"]), "rec": f["closed_form"], "lo": min(vals), "hi": max(vals), "fem": f["tension_taut"],
                     "bridges": (f["standoff_loose_mm"] or 0) > f["inside_radius_mm"], "stack_lo": min(stacks), "stack_hi": max(stacks)})
    tight = [r for r in rows if r["rec"] >= STRAIN_LINE]
    easy = [r for r in rows if r["rec"] < STRAIN_LINE]
    # ---- the finding, computed
    if tight and easy:
        names = ", ".join(r["name"] for r in tight)
        mild = min(r["lo"] for r in tight)
        top = max(r["hi"] for r in easy)
        finding = (f"{len(tight)} of {len(rows)} folds are above the 20 % screening line at the recorded stack: {names}. "
                   + (f"Even at their tightest, the others reach {_pct(top)} against the tight folds' mildest {_pct(mild)}." if top < mild
                      else f"The others reach {_pct(top)} at their tightest, which overlaps the tight folds' mildest case ({_pct(mild)}). The ranking depends on the unmeasured stacks.")
                   + f" At the tight end of the range a fold is {_pct(max(r['hi'] for r in tight))} kinematic strain.")
    elif tight:
        finding = f"Every fold is above the 20 % screening line at the recorded stack. The tightest reaches {_pct(max(r['hi'] for r in tight))} at the tight end of its range."
    else:
        finding = f"No fold is above the 20 % screening line at the recorded stack; the highest reaches {_pct(max(r['hi'] for r in rows))} at the tight end of its range."
    # ---- fold cards
    inputs = {i["name"]: i for i in d["inputs"]}
    cards = []
    for k, f in enumerate(folds, 1):
        nm = _short(f["fold"])
        br = (f["standoff_loose_mm"] or 0) > f["inside_radius_mm"]
        stack_in = next((i for n, i in inputs.items() if n.startswith(f["fold"]) and "stack" in n), None)
        how = ("derived" if stack_in and "derived" in stack_in["name"] else stack_in["source"] if stack_in else "recorded")
        facts = [("grain", "outside" if f["sense"] == "out" else "inside"), (f"stack it wraps ({how})", f"{f['stack_mm']:g} mm"), ("inside radius", f"{f['inside_radius_mm']:g} mm"),
                 ("model, loose / taut", f"{_pct(f['tension_loose'], 1)} / {_pct(f['tension_taut'], 1)}" if f["tension_taut"] is not None else "not run"), ("closed form", _pct(f["closed_form"]))]
        if f["tension_taut"] is None:
            note, cls = "The inside radius is under half the leather thickness. The elastic model shows leather like that bridging the gap, so only the closed form is given.", "warn"
        elif br:
            note, cls = "The model's leather stands off this stack by more than its radius, so it does not follow it. A real fold turns tighter, so the closed form is the number to read.", "warn"
        else:
            note, cls = "The model's leather follows this stack closely enough for its numbers to stand.", "ok"
        shape, strain = run / f"fold{k}_shape.png", run / f"fold{k}_strain.png"
        pic = (f'<div class="plate"><img src="data:image/png;base64,{base64.b64encode(shape.read_bytes()).decode()}" alt="{E(nm)}: the folded sheet around its stack, coloured by strain"></div>'
               if shape.exists() else '<div class="noplate">Not simulated: closed form only</div>')
        more = (f'<details><summary>strain along the sheet</summary><div class="plate"><img src="data:image/png;base64,{base64.b64encode(strain.read_bytes()).decode()}" alt="strain along the sheet at {E(nm)}"></div></details>'
                if strain.exists() else "")
        cards.append(f'<article class="fold">{pic}<div class="foldtext"><h3>{E(nm)}</h3><dl>' + "".join(f"<dt>{E(a)}</dt><dd>{E(b)}</dd>" for a, b in facts)
                     + f'</dl><p class="{cls}">{note}</p>{more}</div></article>')
    # ---- range table
    tab = ['<table><thead><tr><th>fold</th><th>end of range</th><th>stack</th><th>inside radius</th><th>model, taut</th><th>closed form</th></tr></thead><tbody>']
    for f in folds:
        nm = _short(f["fold"])
        grp = ([s for s in sweeps if s["fold"] == f["fold"] and s["end"] == "low"]
               + [{"end": "recorded", "stack_mm": f["stack_mm"], "inside_radius_mm": f["inside_radius_mm"], "tension_taut": f["tension_taut"], "closed_form": f["closed_form"]}]
               + [s for s in sweeps if s["fold"] == f["fold"] and s["end"] == "high"])
        for s in grp:
            model = _pct(s["tension_taut"], 1) if s["tension_taut"] is not None else "not run: radius under half the leather thickness"
            tab.append(f'<tr class="{"rec" if s["end"] == "recorded" else ""}"><td>{E(nm)}</td><td>{s["end"]}</td><td>{s["stack_mm"]:g} mm</td><td>{s["inside_radius_mm"]:g} mm</td><td>{model}</td><td>{_pct(s["closed_form"])}</td></tr>')
    tab.append("</tbody></table>")
    # ---- failure modes
    fm = ['<table class="fm"><thead><tr><th>#</th><th>mode</th><th>status</th><th>for this wallet</th></tr></thead><tbody>']
    for m in d["failure_modes"]:
        st = m["status"].split(" (")[0]
        fm.append(f'<tr><td>{m["id"]}</td><td>{E(m["name"])}</td><td><span class="pill p-{st.replace(" ", "-")}">{E(m["status"])}</span></td><td>{E(m["text"])}</td></tr>')
    fm.append("</tbody></table>")
    meas = "".join(f"<li><strong>{E(a)}.</strong> {E(b)}</li>" for a, b in measure_first(rec))
    counts: dict[str, int] = {}
    for i in d["inputs"]:
        counts[i["source"]] = counts.get(i["source"], 0) + 1
    src = ", ".join(f"{n} {k}" for k, n in counts.items())
    arch = rec.raw.get("archive", {}) or {}
    eyebrow = " &middot; ".join(E(x) for x in (rec.raw.get("maker"), arch.get("series")) if x)
    banner = BANNERS.get(rec.status, "")
    usage = rec.raw.get("usage") or {}
    used = f' It has been used. {E(str(usage.get("condition", "")))}'.rstrip() if usage.get("used") else ""
    note = rec.raw.get("rights_note", "")
    n_unmeasured = sum(1 for i in d["inputs"] if i["source"] != "measured")
    return f"""<title>{E(rec.name)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap">
<style>{CSS}</style>
<main>
  <header><p class="eyebrow">{eyebrow}</p><h1>{E(rec.name)}</h1>
    <p class="lede">{len(folds)} folds modelled. What the fold model says about them, how far that can be trusted, and what a measurement would settle.{used}</p></header>
  {f'<div class="banner"><strong>{E(banner)}</strong> {n_unmeasured} of {len(d["inputs"])} inputs are not measured. Every radius and stack is an inference or an assumption unless marked otherwise, and the results say what the model gives for those inputs, not what the wallet does.</div>' if banner else ""}
  <section>
    <h2>How strained is each fold, and how sure are we?</h2>
    <p class="sub">The dot is the strain if the leather follows its stack exactly, at the stack I recorded. The bar spans the stack range I allowed. The diamond is the full simulation at the recorded stack; hollow means the simulated leather bridges the stack instead of turning round it.</p>
    <div class="chartwrap">{_chart(rows)}
      <div class="legend"><span class="l1">closed form, recorded stack</span><span class="l2">across the stack range</span><span class="l3">simulation, taut</span><span class="l4">simulation, bridging</span></div></div>
    <p class="sub">{E(finding)} Strains that high are not elastic, so those folds must rely on set, thinning and the stitching, which this model does not have.</p>
  </section>
  <section><h2>The folds</h2>
    <p class="sub">Each is the simulated sheet folded round the stack it is assumed to wrap, mirrored to show the whole fold, coloured by strain on its outside face.</p>
    {"".join(cards)}</section>
  <section><h2>Across the range of each stack</h2><div class="scroll">{"".join(tab)}</div></section>
  <section><h2>Failure modes</h2>
    <p class="sub">The fourteen modes in the project's catalogue, as they stand for this wallet. Most are not modelled yet, and the report says so for every wallet.</p>
    <div class="scroll">{"".join(fm)}</div></section>
  <section><h2>What to measure first</h2><ol>{meas}</ol></section>
  <footer>Run {E(d["meta"]["hash"])} &middot; walletsim {E(d["meta"]["walletsim"])} &middot; {E(d["meta"]["ccx"])} &middot; plane-strain neo-Hookean fold, light pull {d["meta"]["taut_n_per_mm"]} N per mm for "taut". Inputs by source: {E(src)}. {E(note)}</footer>
</main>
"""


def write_page(run_dir: str | Path | None = None, wallet_dir: str | Path | None = None, out: str | Path | None = None) -> Path:
    run = Path(run_dir) if run_dir else latest_run(wallet_dir)
    path = Path(out) if out else run / "page.html"
    path.write_text(build_page(run))
    return path
