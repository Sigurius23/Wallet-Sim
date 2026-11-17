/* Procedural leather surfaces for the 3D views: colour, grain relief and sheen, drawn on a canvas so that no photograph is copied.
 *
 * Each grain kind is a recipe matched by eye to what the records and photographs say about the leather, not a scan of it:
 *   calf     fine, pebbled grain (jittered cells, low relief)
 *   horse    smooth to wrinkled and valleyed (the maker's words for the WHALET's horse skin): long soft creases, few pores
 *   nap      the reverse (flesh) side worn outward, as on reversed pig: fine fibrous fuzz, matt, no grain pattern
 *   pig      grain side of pig: pores in groups of three across the surface
 *   fish     scale pockets in offset rows (tilapia and perch leathers)
 *   plain    almost featureless
 *
 *   LeatherLook.material(THREE, look) -> MeshStandardMaterial with map, bumpMap and roughness; textures repeat every look.tile_mm millimetres
 *   look = { kind, colour: "#rrggbb", tile_mm, roughness, bump }
 */
var LeatherLook = (function () {
  "use strict";
  var cache = {};
  function rng(seed) { var s = seed >>> 0; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
  function grid(n, seed) { var r = rng(seed), g = new Float32Array(n * n); for (var i = 0; i < g.length; i++) g[i] = r(); return g; }
  function smooth(t) { return t * t * (3 - 2 * t); }
  function vnoise(g, n, x, y) {                                    // periodic value noise on an n x n lattice; x, y in lattice units
    var xi = Math.floor(x), yi = Math.floor(y), fx = smooth(x - xi), fy = smooth(y - yi), a = ((xi % n) + n) % n, b = ((yi % n) + n) % n, a1 = (a + 1) % n, b1 = (b + 1) % n;
    var v00 = g[b * n + a], v10 = g[b * n + a1], v01 = g[b1 * n + a], v11 = g[b1 * n + a1];
    return (v00 + (v10 - v00) * fx) + ((v01 + (v11 - v01) * fx) - (v00 + (v10 - v00) * fx)) * fy;
  }
  function fbm(gs, n, x, y, oct) { var s = 0, a = 0.5, f = 1, t = 0; for (var o = 0; o < oct; o++) { s += a * vnoise(gs[o], n * f, x * f, y * f); t += a; a *= 0.5; f *= 2; } return s / t; }
  function cells(n, seed) { var r = rng(seed), p = []; for (var j = 0; j < n; j++) for (var i = 0; i < n; i++) p.push([i + 0.15 + 0.7 * r(), j + 0.15 + 0.7 * r()]); return p; }
  function worley(pts, n, x, y) {                                  // distances to the nearest and second-nearest feature point, periodic
    var d1 = 9, d2 = 9, xi = Math.floor(x), yi = Math.floor(y);
    for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) {
      var cx = xi + dx, cy = yi + dy, ix = ((cx % n) + n) % n, iy = ((cy % n) + n) % n, q = pts[iy * n + ix], px = q[0] - ix + cx, py = q[1] - iy + cy;
      var d = Math.hypot(px - x, py - y); if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) d2 = d;
    }
    return [d1, d2];
  }
  function height(kind, S, seed) {                                  // a tileable height field in [0, 1], S x S pixels
    var h = new Float32Array(S * S), n = 8, gs = [grid(n, seed), grid(n * 2, seed + 1), grid(n * 4, seed + 2), grid(n * 8, seed + 3), grid(n * 16, seed + 4), grid(n * 32, seed + 5)];
    var pc = kind === "calf" ? cells(26, seed + 9) : kind === "pig" ? cells(14, seed + 9) : kind === "fish" ? null : cells(10, seed + 9);
    for (var y = 0; y < S; y++) for (var x = 0; x < S; x++) {
      var u = x / S, v = y / S, val;
      if (kind === "calf") { var w = worley(pc, 26, u * 26, v * 26); val = 0.62 * Math.min(1, (w[1] - w[0]) * 2.2) + 0.38 * fbm(gs, n, u * n, v * n, 6); }
      else if (kind === "horse") {
        var wx = fbm(gs, n, u * n, v * n, 3) * 2.2, wy = fbm(gs, n, u * n + 3.1, v * n + 1.7, 3) * 2.2;
        var c = 1 - Math.abs(2 * fbm(gs, n, (u + 0.08 * wx) * n * 0.5, (v * 0.35 + 0.08 * wy) * n * 0.5, 4) - 1);   // long, soft valleys running mostly one way
        val = 0.55 + 0.35 * (1 - Math.pow(c, 6)) - 0.1 * fbm(gs, n, u * n * 2, v * n * 2, 5);
      }
      else if (kind === "nap") { var f = fbm(gs, n, u * n * 4, v * n * 2, 6); val = 0.5 + 0.5 * (f - 0.5) * 2 * (0.7 + 0.3 * fbm(gs, n, u * n, v * n, 3)); }
      else if (kind === "pig") { var w2 = worley(pc, 14, u * 14, v * 14); val = 0.75 + 0.2 * fbm(gs, n, u * n, v * n, 5) - (w2[0] < 0.06 ? 0.55 : w2[0] < 0.1 ? 0.25 : 0); }
      else if (kind === "fish") { var row = Math.floor(v * 18), off = (row % 2) * 0.5, sx = (u * 14 + off) % 1, sy = (v * 18) % 1, rr = Math.hypot(sx - 0.5, sy * 1.2 - 0.2); val = 0.45 + 0.4 * Math.min(1, Math.abs(rr - 0.42) * 6) + 0.15 * fbm(gs, n, u * n, v * n, 4); }
      else val = 0.5 + 0.15 * fbm(gs, n, u * n, v * n, 5);
      h[y * S + x] = Math.max(0, Math.min(1, val));
    }
    return h;
  }
  function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
  function canvases(look) {
    var key = look.kind + look.colour + (look.seed || 7);
    if (cache[key]) return cache[key];
    var S = 384, h = height(look.kind, S, look.seed || 7), base = hex(look.colour || "#2a2a2c"), bump = document.createElement("canvas"), col = document.createElement("canvas");
    bump.width = bump.height = col.width = col.height = S;
    var bc = bump.getContext("2d"), cc = col.getContext("2d"), bi = bc.createImageData(S, S), ci = cc.createImageData(S, S), mott = height("plain", S, (look.seed || 7) + 40);
    for (var i = 0; i < S * S; i++) {
      var g = Math.round(h[i] * 255); bi.data[4 * i] = bi.data[4 * i + 1] = bi.data[4 * i + 2] = g; bi.data[4 * i + 3] = 255;
      var k = 0.86 + 0.22 * (mott[i] - 0.5) * 2 + 0.12 * (h[i] - 0.5);                     // gentle mottling, darker in the valleys
      for (var c = 0; c < 3; c++) ci.data[4 * i + c] = Math.max(0, Math.min(255, Math.round(base[c] * k)));
      ci.data[4 * i + 3] = 255;
    }
    bc.putImageData(bi, 0, 0); cc.putImageData(ci, 0, 0);
    return (cache[key] = { bump: bump, col: col });
  }
  function material(THREE, look, tint) {
    var cv = canvases(look), tile = look.tile_mm || 30, maps = [cv.col, cv.bump].map(function (c) {
      var t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / tile, 1 / tile); t.anisotropy = 4; return t;
    });
    if (THREE.sRGBEncoding) maps[0].encoding = THREE.sRGBEncoding;
    return new THREE.MeshStandardMaterial({ map: maps[0], bumpMap: maps[1], bumpScale: look.bump == null ? 0.35 : look.bump, roughness: look.roughness == null ? 0.7 : look.roughness,
                                            metalness: 0, color: new THREE.Color(tint || "#ffffff"), side: THREE.DoubleSide });
  }
  return { material: material, height: height };
})();
