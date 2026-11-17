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

  function Turtle(T, x, y, phi) { this.T = T; this.x = x; this.y = y; this.phi = phi; this.pts = []; this.marks = {}; this.segs = []; this.push(0); }
  Turtle.prototype.push = function (e) { this.pts.push({ x: this.x, y: this.y, phi: this.phi, e: e }); };
  Turtle.prototype.straight = function (len, e) {
    this.segs.push({ x: this.x, y: this.y, phi: this.phi, len: len });           // each straight run is a panel: where it starts, which way it runs, how long it is
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
      // Pocket k (1..n) is the gap that hairpin k closes; pocket 0 is the gap between the last leaf and the bottom panel, closed by the spine. An empty pocket keeps the
      // recorded void (2 x the hairpin's inside radius); cards open it to their stack plus a little slack, so the hairpin's radius and the spine's stack follow the contents.
      var n = CFG.leaves, hs = model.hinges, CT = 0.76, SL = 0.3; rIn = p.rIn; L = sz.L;
      var gaps = [], cards = [];
      for (var q = 0; q <= n; q++) { var c = Math.max(0, Math.round(p["n_p" + q] || 0)); cards.push(c); gaps.push(c > 0 ? c * CT + SL : 2 * rIn); }
      var stack = n * T + gaps.reduce(function (s0, g0) { return s0 + g0; }, 0); rs = stack / 2 + T / 2;
      var rnK = function (k) { return gaps[k] / 2 + T / 2; }, rnMax = 0; for (var q2 = 1; q2 <= n; q2++) rnMax = Math.max(rnMax, rnK(q2));
      var rInSpine = rs - T / 2, Lt = L - rs - rnK(1) - T, xf = rnMax + T + 1.0, La = Lt - xf, Lb = Lt - 3, Lc = La - 8;
      t = new Turtle(T, Lb, 0, Math.PI);
      t.straight(Lb, 0); t.fold(hs[0].id, turn(hs[0]), Math.PI * rs, epsFull(rInSpine));
      for (var k = 1; k <= n; k++) { t.straight(k === 1 ? Lt : La, 0); t.fold(hs[k].id, turn(hs[k]), Math.PI * rnK(k), epsFull(gaps[k] / 2)); }
      t.straight(Lc, 0);
      // cards lie on the layer below their pocket, against the closed end, long side across the wallet
      var boxes = [], warn = [];
      for (var pk = 0; pk <= n; pk++) {
        if (!cards[pk]) continue;
        var seg = pk === 0 ? t.segs[0] : t.segs[1 + pk], sign = pk === 0 ? -1 : (pk % 2 === 0 ? 1 : -1), sAlong = pk === 0 ? seg.len - 1 - 27 : 1 + 27;
        if (54 + 2 > seg.len) warn.push("a card (54 mm) is longer than the leaf it sits on in pocket " + pk + " (" + seg.len.toFixed(0) + " mm)");
        for (var j = 0; j < cards[pk]; j++) {
          var off = T / 2 + SL / 2 + (j + 0.5) * CT, nx = -Math.sin(seg.phi) * sign, ny = Math.cos(seg.phi) * sign;
          boxes.push({ kind: "card", x: seg.x + Math.cos(seg.phi) * sAlong + nx * off, y: seg.y + Math.sin(seg.phi) * sAlong + ny * off, z: 0, sx: 54, sy: CT * 0.96, sz: 85.6, rz: seg.phi });
        }
      }
      if (85.6 + 2 > sz.W) warn.push("a card (85.6 mm) is wider than this size (" + sz.W + " mm)");
      var tight = 1; for (var q3 = 1; q3 <= n; q3++) if (gaps[q3] < gaps[tight]) tight = q3;
      return { strips: [t.pts], blocks: [], boxes: boxes, marks: t.marks, W: sz.W, segs: t.segs, panels: { "top panel": 1 },
               twin: { depth: stack + 2 * T, stack: stack, rIn: rInSpine },
               text: "Closed thickness " + (stack + 2 * T).toFixed(1) + " mm. The spine wraps " + stack.toFixed(1) + " mm (inside radius " + rInSpine.toFixed(1) + " mm, strain " + (100 * epsFull(rInSpine)).toFixed(1) +
                     " %). The tightest hairpin has an inside radius of " + (gaps[tight] / 2).toFixed(2) + " mm (strain " + (100 * epsFull(gaps[tight] / 2)).toFixed(0) + " %)." + (warn.length ? "<br>" + warn.join("; ") + "." : "") };
    }
    if (model.kind === "flap") {
      // One hinge, seen along the length: a back panel, the hinge, and the flap that lies over the front; a block stands for the pack the hinge wraps.
      var stack = p.stack, h0 = model.hinges[0]; rs = stack / 2 + T / 2; rIn = rs - T / 2; L = sz.L; W = sz.W;
      var Lb2 = L - rs, Lf = Lb2 - 2;
      t = new Turtle(T, Lb2, 0, Math.PI);
      t.straight(Lb2, 0); t.fold(h0.id, turn(h0), Math.PI * rs, epsFull(rIn)); t.straight(Lf, 0);
      return { segs: t.segs, panels: { "back panel": 0, flap: 1 }, strips: [t.pts], blocks: [{ x0: 3, x1: Lb2 - 4, y0: T / 2, y1: T / 2 + stack, z0: -W / 2 + 6, z1: W / 2 - 6, label: "pack the hinge wraps" }], marks: t.marks, W: W,
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
    if (model.kind === "twin") return buildTwin(CFG, model, p, v, turn, epsFull);
    throw new Error("unknown model kind " + model.kind);
  }

  // ---- the functional twin: real-size layers, pockets that fill with cards, and a flap hinge whose radius follows what is inside ----------------------------------
  // Closed and landscape: the back panel runs along +x from its free end (x = -L/2); every wall is attached at that free end and reaches toward the hinge; the hinge is at +x.
  // The stack between the back panel and the flap is  sum(gap + t) over the walls; the hinge wraps it, so its inside radius is half of that.
  function buildTwin(CFG, model, p, v, turn, epsFull) {
    var A = CFG.twin, T = p.t, L = A.L, W = A.W, walls = A.walls, nk = walls.length;
    var gaps = A.pockets.map(function (pk) {
      var n = p["n_" + pk.key] || 0, content = n * A.card.t;
      if (pk.id === A.bills_pocket) content += (p.notes || 0) * A.note_t * 2;
      return content > 0 ? content + A.slack : A.gapEmpty;
    });
    var pull = A.pockets.map(function (pk, q) { var w0 = A.walls[q]; return w0 && w0.gusset && v.pocket ? ease(v.pocket) * 1.7 * w0.gusset : 0; });   // a gusseted pocket pulled open by hand, as in the photograph
    var closedStack = gaps.reduce(function (a, b) { return a + b; }, 0) + walls.length * T;                // what the hinge wraps: contents only, not the hand's pull
    gaps = gaps.map(function (g0, q) { return g0 + pull[q]; });
    var plates = [], boxes = [], strips = [], gussets = [], yTop = T / 2, wallMid = [], wallTop = [];
    for (var k = 0; k < nk; k++) {
      var yb = yTop + gaps[k]; wallMid.push(yb + T / 2); yTop = yb + T; wallTop.push(yTop);
    }
    var S = closedStack, hs = S + A.flapGap, rIn = hs / 2, rs = rIn + T / 2, depth = 2 * T + hs;     // stack the hinge wraps, its inside and neutral radii, closed depth
    var Lb = L - (rIn + T), Lf = A.flapLen - (rIn + T), x0 = -L / 2, hinge = model.hinges[0];
    var t = new Turtle(T, x0, 0, 0);
    t.straight(Lb, 0);
    var iArc = t.pts.length - 1;
    t.fold(hinge.id, turn(hinge), Math.PI * rs, epsFull(rIn));
    var arc = t.pts.slice(iArc), ex = t.x, ey = t.y, ephi = t.phi;
    t.straight(Lf, 0);
    strips.push(t.pts);
    // the back panel and the flap are plates (they have plan shapes); the arc between them is an extruded strip
    plates.push({ id: "back panel", x: x0, y: 0, phi: 0, zc: 0, len: Lb, wid: W, t: T, rs: 1.0, re: [1.0, 1.0], tone: 0 });
    var stud = A.stud, zs = stud ? stud.z - W / 2 : 0, xs = stud ? x0 + stud.x : 0;
    plates.push({ id: "flap", x: ex, y: ey, phi: ephi, zc: 0, len: Lf, wid: W, t: T, rs: 1.0, re: [A.flapR, A.flapR], tone: 0,
                  hole: stud ? { u: (L / 2 - (rIn + T)) - xs, z: zs, r: stud.d / 2 + 0.6 } : null });
    if (A.petals) {                                                  // two overlapping panels with large rounded corners lining the inside of the flap
      var px = ex - Math.sin(ephi) * T * 0.98, py = ey + Math.cos(ephi) * T * 0.98, pr = Math.min(0.55 * W, Lf * 0.75);
      plates.push({ id: "petal", x: px, y: py, phi: ephi, zc: -W * 0.2, len: Lf - 2, wid: W * 0.6, t: T, rs: 1.0, re: [2, pr], tone: 1 });
      plates.push({ id: "petal", x: px - Math.sin(ephi) * T, y: py + Math.cos(ephi) * T, phi: ephi, zc: W * 0.2, len: Lf - 2, wid: W * 0.6, t: T, rs: 1.0, re: [pr, 2], tone: 2 });
    }
    for (var j = 0; j < nk; j++) {
      var w = walls[j], width = W - w.left - w.right, zc = (w.left - w.right) / 2;                // an inset from the left edge shifts the wall's centre toward +z
      plates.push({ id: w.id, x: x0, y: wallMid[j], phi: 0, zc: zc, len: w.top, wid: width, t: T, rs: 0.8, re: w.radii, tone: 1 + j % 2, notch: w.notch || null });
      if (w.gusset) {                                                // a V pleat at each side joins this wall to the layer behind it; it opens as the pocket fills
        var yBack = (j === 0 ? T / 2 : wallTop[j - 1]), yFront = wallMid[j] - T / 2, g = yFront - yBack, al = Math.asin(Math.min(1, g / (2 * w.gusset))), inward = w.gusset * Math.cos(al);
        [-1, 1].forEach(function (sd) {
          var zE = zc + sd * (width / 2), zM = zE - sd * inward, yM = (yBack + yFront) / 2;
          gussets.push({ quads: [[[x0, yBack, zE], [x0 + w.top * 0.96, yBack, zE], [x0 + w.top * 0.96, yM, zM], [x0, yM, zM]],
                                 [[x0, yM, zM], [x0 + w.top * 0.96, yM, zM], [x0 + w.top * 0.96, yFront, zE], [x0, yFront, zE]]] });
        });
      }
      strips.push([{ x: x0, y: wallMid[j], phi: 0, e: 0 }, { x: x0 + w.top, y: wallMid[j], phi: 0, e: 0 }]);
    }
    // contents: cards stand on the free end of the back panel with their long side toward the hinge; notes lie folded in the bills pocket
    var y = T / 2;
    for (var q = 0; q < nk; q++) {
      var pk = A.pockets[q], n = p["n_" + pk.key] || 0, wq = walls[q], zq = (wq.left - wq.right) / 2, cy = y + (n ? A.slack / 2 : 0);
      for (var c = 0; c < n; c++) boxes.push({ kind: "card", x: x0 + 0.8 + A.card.l / 2, y: cy + (c + 0.5) * A.card.t, z: zq, sx: A.card.l, sy: A.card.t * 0.96, sz: A.card.w });
      if (pk.id === A.bills_pocket && (p.notes || 0) > 0) boxes.push({ kind: "note", x: x0 + 1 + 80 / 2, y: cy + n * A.card.t + (p.notes * A.note_t), z: zq, sx: 80, sy: p.notes * A.note_t * 2, sz: 62 });
      y += gaps[q] + T;
    }
    var cyl = stud ? [{ x: xs, y: wallTop[nk - 1] + stud.h / 2, z: zs, r: stud.d / 2, h: stud.h }] : [];
    (A.slits || []).forEach(function (sl) { boxes.push({ kind: "slit", x: x0 + sl.u, y: T / 2 + 0.06, z: sl.z, sx: 0.9, sy: 0.12, sz: sl.len }); });
    var warn = [];
    A.pockets.forEach(function (pk, q) {
      var n = p["n_" + pk.key] || 0;
      if (pk.cap != null && n > pk.cap) warn.push(pk.id + " holds " + n + " cards; the maker says " + pk.cap + " per slot");
      var wq = walls[q]; if (n && A.card.w > W - wq.left - wq.right) warn.push("a card (" + A.card.w + " mm wide) is wider than the " + pk.id);
    });
    var fitT = (A.closedDepth - gaps.reduce(function (a, b) { return a + b; }, 0) - A.flapGap) / (2 + nk);
    var pulled = pull.some(function (x) { return x > 0.5; });
    var text = (pulled ? "The bill pocket is pulled open: the front wall stands " + (Math.max.apply(null, gaps)).toFixed(0) + " mm off the back and its V gussets open. " : "") + "Closed depth " + depth.toFixed(1) + " mm with this thickness and these contents" + (A.closedDepth ? " (the stated depth is " + A.closedDepth + " mm)" : "") + ". The hinge wraps " + hs.toFixed(1) +
      " mm of stack, inside radius " + rIn.toFixed(1) + " mm." + (A.incomplete ? " The parts drawn do not make up the stated depth: the rest is the parts not drawn and whatever was inside when it was measured." : A.closedDepth ? (fitT >= 0.4 ? " The sheet thickness that would give " + A.closedDepth + " mm with these contents is " + fitT.toFixed(2) + " mm." : " These contents alone take more room than the maker's " + A.closedDepth + " mm allows.") : "") +
      (warn.length ? "<br>" + warn.join("; ") + "." : "");
    return { strips: strips, drawStrips: [arc], plates: plates, boxes: boxes, cyl: cyl, gussets: gussets, blocks: [], marks: t.marks, W: W, text: text,
             segs: t.segs, panels: { "back panel": 0, flap: 1 }, sides: { flap: -1 },
             twin: { depth: depth, stack: hs, rIn: rIn, layers: 2 + nk, fitT: fitT } };
  }
  var api = { build: build, ease: ease, lerp: lerp };
  return api;
})();
