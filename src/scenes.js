/*
 * scenes.js — procedural target images for the fitting demo.
 * Pure math (no canvas), so Node can use the same pictures when tuning.
 * Each function returns Float32Array(w*h*3) with values in 0..1.
 */
(function (root) {
  'use strict';

  function mix(a, b, t) { return a + (b - a) * t; }
  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function smooth(e0, e1, x) { var t = clamp01((x - e0) / (e1 - e0)); return t * t * (3 - 2 * t); }
  function hex(h) { return [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255]; }

  // Mountain lake at dusk: soft gradients (easy) plus ridges, snow lines,
  // trees and ripples (hard) — the hard parts are where densification pays off.
  function landscape(w, h) {
    var out = new Float32Array(w * h * 3);
    var skyTop = hex('#1f3a6e'), skyMid = hex('#6f7fb5'), skyLow = hex('#f4b77a');
    var far = hex('#7f8fb8'), near = hex('#2f4858'), snow = hex('#eef2f6');
    var forest = hex('#1f3a2c'), water = hex('#1c3550'), sun = hex('#fff3cf');
    var horizon = 0.62;
    function ridgeFar(u) { return 0.47 - 0.10 * Math.abs(Math.sin(u * 5.1 + 0.4)) - 0.05 * Math.sin(u * 13.7 + 1.1) - 0.02 * Math.sin(u * 31 + 2); }
    function ridgeNear(u) { return 0.60 - 0.20 * Math.pow(Math.abs(Math.sin(u * 3.3 - 0.2)), 1.6) - 0.03 * Math.sin(u * 23 + 0.5) - 0.012 * Math.sin(u * 61); }
    function sky(u, v) {
      var c = v < 0.35 ? [mix(skyTop[0], skyMid[0], v / 0.35), mix(skyTop[1], skyMid[1], v / 0.35), mix(skyTop[2], skyMid[2], v / 0.35)]
                       : [mix(skyMid[0], skyLow[0], smooth(0.35, horizon, v)), mix(skyMid[1], skyLow[1], smooth(0.35, horizon, v)), mix(skyMid[2], skyLow[2], smooth(0.35, horizon, v))];
      var dx = (u - 0.70) * w / h, dy = v - 0.33, d = Math.sqrt(dx * dx + dy * dy);
      var glow = Math.exp(-d * d / 0.02) * 0.45;
      var disk = smooth(0.062, 0.055, d);
      for (var k = 0; k < 3; k++) c[k] = mix(c[k] + glow * (sun[k] - c[k]), sun[k], disk);
      return c;
    }
    function land(u, v) {
      // returns null for sky
      var rn = ridgeNear(u), rf = ridgeFar(u);
      if (v >= rn) {
        var depth = (v - rn) / 0.2;
        var c = [near[0] * (1 - 0.3 * depth), near[1] * (1 - 0.3 * depth), near[2] * (1 - 0.3 * depth)];
        var snowLine = rn + 0.035 + 0.015 * Math.sin(u * 47);
        if (rn < 0.47 && v < snowLine) c = snow.slice();
        // a band of pine trees along the foot of the near range
        var foot = 0.585 + 0.01 * Math.sin(u * 9);
        var tree = Math.abs(((u * 38) % 1) - 0.5) * 2;           // 0 at tree centre
        var top = foot - 0.035 * (1 - tree) * (0.7 + 0.3 * Math.sin(u * 77));
        if (v > top && v < horizon) c = forest.slice();
        return c;
      }
      if (v >= rf) {
        var haze = smooth(rf, rf + 0.12, v);
        return [mix(far[0], skyLow[0], 0.25 * (1 - haze)), mix(far[1], skyLow[1], 0.25 * (1 - haze)), mix(far[2], skyLow[2], 0.25 * (1 - haze))];
      }
      return null;
    }
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var u = (x + 0.5) / w, v = (y + 0.5) / h, c;
        if (v < horizon) {
          c = land(u, v) || sky(u, v);
        } else {
          // lake: mirrored scene, darker and bluer, broken up by ripples
          var mv = 2 * horizon - v + 0.004 * Math.sin(v * h * 2.1 + u * 9);
          var rc = land(u, mv) || sky(u, mv);
          var t = smooth(horizon, 1, v);
          var ripple = 0.5 + 0.5 * Math.sin(v * h * 1.7 + 3 * Math.sin(u * 17));
          c = [];
          for (var k = 0; k < 3; k++) c[k] = mix(rc[k] * 0.78, water[k], 0.25 + 0.45 * t) + 0.05 * (ripple - 0.5);
          // sun path on the water
          var sx = Math.abs(u - 0.70) * w / h;
          c[0] += 0.35 * Math.exp(-sx * sx / 0.0025) * ripple * (1 - t);
          c[1] += 0.28 * Math.exp(-sx * sx / 0.0025) * ripple * (1 - t);
          c[2] += 0.15 * Math.exp(-sx * sx / 0.0025) * ripple * (1 - t);
        }
        var o = (y * w + x) * 3;
        out[o] = clamp01(c[0]); out[o + 1] = clamp01(c[1]); out[o + 2] = clamp01(c[2]);
      }
    }
    return out;
  }

  // Jelly beans: glossy ellipses on a pale tray — the analogy used on the page.
  function beans(w, h) {
    var out = new Float32Array(w * h * 3);
    var bg = hex('#eef1ee');
    var cols = ['#e5484d', '#f76b15', '#ffc53d', '#46a758', '#12a594', '#3e63dd', '#8e4ec6', '#d6409f'].map(hex);
    var s = 11, list = [];
    function rnd() { s = (s * 16807) % 2147483647; return s / 2147483647; }
    for (var i = 0; i < 26; i++) {
      list.push({ x: rnd(), y: rnd(), a: 0.055 + 0.03 * rnd(), b: 0.03 + 0.012 * rnd(), t: rnd() * Math.PI, c: cols[i % cols.length] });
    }
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var u = (x + 0.5) / w, v = (y + 0.5) / h;
        var c = [bg[0] - 0.05 * v, bg[1] - 0.05 * v, bg[2] - 0.04 * v];
        for (var j = 0; j < list.length; j++) {
          var B = list[j];
          var dx = (u - B.x) * w / h, dy = v - B.y;
          var ct = Math.cos(B.t), st = Math.sin(B.t);
          var p = (ct * dx + st * dy) / (B.a * 0.72), q = (-st * dx + ct * dy) / B.b;
          var r2 = p * p + q * q;
          // soft shadow first, then the bean with a highlight
          var sp = (ct * (dx - 0.01) + st * (dy - 0.012)) / (B.a * 0.72), sq = (-st * (dx - 0.01) + ct * (dy - 0.012)) / B.b;
          var sh = Math.exp(-(sp * sp + sq * sq) * 0.8) * 0.18;
          c[0] -= sh; c[1] -= sh; c[2] -= sh;
          if (r2 < 1) {
            var shade = 0.78 + 0.22 * (1 - r2);
            var hp = p + 0.35, hq = q + 0.45;
            var hl = Math.exp(-(hp * hp + hq * hq) * 12) * 0.7;
            var edge = smooth(1, 0.9, r2);
            for (var k = 0; k < 3; k++) c[k] = mix(c[k], B.c[k] * shade + hl * (1 - B.c[k] * shade), edge);
          }
        }
        var o = (y * w + x) * 3;
        out[o] = clamp01(c[0]); out[o + 1] = clamp01(c[1]); out[o + 2] = clamp01(c[2]);
      }
    }
    return out;
  }

  var api = { landscape: landscape, beans: beans };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Scenes = api;
})(this);
