/* Fold geometry shared by the 3D viewer and the archive app: pure functions, no DOM and no three.js.
 *
 * A model is a centre line of fixed-length hinge arcs and straight runs ("turtle"). Each fold turns through a fixed length of sheet, so a fold that opens
 * gets a larger radius. Strain at a fold = |turn| / 180 x t / (2 R + t), the closed form for a full hairpin at the closed inside radius, scaled with the angle.
 * It is a sketch of how the sheet folds, not a simulation.
 *
 *   WalletGeometry.build(CFG, model, size, p, v) -> { strips, blocks, marks, W, text }
 *     model  one entry of CFG.models        size  a key of CFG.sizes
 *     p      {paramId: value}                v     {controlId: 0..1}  (0 closed, 1 open)
 */
var WalletGeometry = (function () {
  "use strict";
  var ease = function (u) { return u * u * (3 - 2 * u); };
  var lerp = function (a, b, u) { return a + (b - a) * u; };

  function Turtle(T, x, y, phi) { this.T = T; this.x = x; this.y = y; this.phi = phi; this.pts = []; this.marks = {}; this.push(0); }
  Turtle.prototype.push = function (e) { this.pts.push({ x: this.x, y: this.y, phi: this.phi, e: e }); };
  Turtle.prototype.straight = function (len, e) {
    var n = Math.max(2, Math.ceil(len / 10)), dx = Math.cos(this.phi) * len / n, dy = Math.sin(this.phi) * len / n;
    for (var k = 0; k < n; k++) { this.x += dx; this.y += dy; this.push(e); }
  };
  // A fold turns through `deg` degrees (positive = anticlockwise) along a neutral arc of fixed LENGTH ell, so its radius grows as it opens.
  Turtle.prototype.fold = function (id, deg, ell, epsFull) {
    var th = deg * Math.PI / 180, e = Math.abs(deg) / 180 * epsFull;
    if (Math.abs(th) < 1e-3) { this.straight(ell, e); this.marks[id] = { x: this.x, y: this.y, e: e, ang: deg, r: Infinity }; return; }
    var r = ell / Math.abs(th), s = Math.sign(th), nx = -Math.sin(this.phi), ny = Math.cos(this.phi);
    var cx = this.x + s * r * nx, cy = this.y + s * r * ny, m = Math.max(6, Math.ceil(Math.abs(th) / (Math.PI / 30))), mid = null;
    for (var k = 1; k <= m; k++) {
      var ph = this.phi + th * k / m, qx = -Math.sin(ph), qy = Math.cos(ph);
      this.pts.push({ x: cx - s * r * qx, y: cy - s * r * qy, phi: ph, e: e });
      if (k === Math.round(m / 2)) mid = { x: cx - s * r * qx, y: cy - s * r * qy };
    }
    var last = this.pts[this.pts.length - 1]; this.x = last.x; this.y = last.y; this.phi = last.phi;
    this.marks[id] = { x: mid.x, y: mid.y, e: e, ang: deg, r: r - this.T / 2 };
  };

  function build(CFG, model, size, p, v) {
    var T = CFG.T, sz = CFG.sizes[size];
    var epsFull = function (rIn) { return T / (2 * rIn + T); };
    var turn = function (h) { return lerp(h.closed, h.open, ease(v[h.drv] || 0)); };       // current signed turn of a hinge, degrees
    var t, rIn, rn, rs, L, W;
    if (model.kind === "chain") {
      // One sheet folded as an accordion: bottom panel, spine, top panel, then n tight hairpins with a leaf after each (loops turn one way, left folds the other).
      var n = CFG.leaves, hs = model.hinges; rIn = p.rIn; rn = rIn + T / 2; rs = (n + 1) * rn; L = sz.L;
      var rInSpine = rs - T / 2, Lt = L - rs - rn - T, xf = rn + T + 1.0, La = Lt - xf, Lb = Lt - 3, Lc = La - 8;
      t = new Turtle(T, Lb, 0, Math.PI);
      t.straight(Lb, 0); t.fold(hs[0].id, turn(hs[0]), Math.PI * rs, epsFull(rInSpine));
      for (var k = 1; k <= n; k++) { t.straight(k === 1 ? Lt : La, 0); t.fold(hs[k].id, turn(hs[k]), Math.PI * rn, epsFull(rIn)); }
      t.straight(Lc, 0);
      return { strips: [t.pts], blocks: [], marks: t.marks, W: sz.W,
               text: "The layers sit one loop-gap apart, so the spine wraps " + (2 * rs - T).toFixed(1) + " mm here (inside radius " + rInSpine.toFixed(1) + " mm)." };
    }
    if (model.kind === "flap") {
      // One hinge, seen along the length: a back panel, the hinge, and the flap that lies over the front; a block stands for the pack the hinge wraps.
      var stack = p.stack, h0 = model.hinges[0]; rs = stack / 2 + T / 2; rIn = rs - T / 2; L = sz.L; W = sz.W;
      var Lb2 = L - rs, Lf = Lb2 - 2;
      t = new Turtle(T, Lb2, 0, Math.PI);
      t.straight(Lb2, 0); t.fold(h0.id, turn(h0), Math.PI * rs, epsFull(rIn)); t.straight(Lf, 0);
      return { strips: [t.pts], blocks: [{ x0: 3, x1: Lb2 - 4, y0: T / 2, y1: T / 2 + stack, z0: -W / 2 + 6, z1: W / 2 - 6, label: "pack the hinge wraps" }], marks: t.marks, W: W,
               text: "The hinge wraps " + stack.toFixed(1) + " mm here (inside radius " + rIn.toFixed(1) + " mm). The grey block is that pack; it is not modelled." };
    }
    if (model.kind === "gusset") {
      // A side gusset of the bill pocket, seen across the width: front panel, a V-shaped pleat at each side, back panel. phi is the included angle of the V.
      var G = CFG.gusset; rIn = p.rIn; rn = rIn + T / 2;
      var ell = Math.PI * rn, ef = epsFull(rIn), phi = lerp(0, G.maxPhi, ease(v.gusset || 0)), ph2 = phi / 2;
      t = new Turtle(T, 0, 0, Math.PI);
      t.straight(G.w, 0);
      t.fold("edgeF", 180 - ph2, ell, ef); t.straight(G.a, 0);
      t.fold("crease", -(180 - phi), ell, ef); t.straight(G.a, 0);
      t.fold("edgeB", 180 - ph2, ell, ef); t.straight(G.w, 0);
      var other = t.pts.map(function (q) { return { x: -q.x, y: q.y, phi: Math.PI - q.phi, e: q.e }; });
      var gap = Math.abs(t.pts[t.pts.length - 1].y);
      return { strips: [t.pts, other], blocks: [], marks: t.marks, W: G.depth,
               text: "The V of the pleat is open " + phi.toFixed(0) + "&deg;; front and back panels are " + gap.toFixed(1) + " mm apart, centre line to centre line." };
    }
    throw new Error("unknown model kind " + model.kind);
  }
  return { build: build, ease: ease, lerp: lerp };
})();
