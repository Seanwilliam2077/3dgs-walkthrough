/*
 * splat2d.js — 2D Gaussian splatting that trains in the browser.
 *
 * Same math as 3DGS, minus the projection step: each Gaussian has a mean,
 * two log-scales, a rotation, an RGB colour and an opacity. Pixels are
 * composited front to back (index 0 is nearest), the backward pass is the
 * analytic gradient walked back to front, parameters are updated with Adam,
 * and adaptive density control clones, splits and prunes Gaussians.
 *
 * Shared by the hero animation and the fitting demo. `node src/gradcheck.cjs`
 * compares the analytic gradient against finite differences.
 */
(function (root) {
  'use strict';

  // One Gaussian = 9 numbers: mx, my, log sx, log sy, theta, r, g, b, opacity.
  // Colour and opacity are stored as logits and squashed with a sigmoid.
  var P = 9;
  var CUT = 9;              // q = Mahalanobis^2; stop at 3 sigma like 3DGS
  var ALPHA_MIN = 1 / 255;  // 3DGS skips fragments fainter than this
  var ALPHA_MAX = 0.99;     // ...and clamps opacity so transmittance never hits 0
  var T_MIN = 1e-4;         // early termination once a pixel is saturated

  // exp(-q/2) lookup: about 3x faster than Math.exp in the inner loop.
  var LUT_N = 4096;
  var LUT_S = LUT_N / CUT;
  var LUT = new Float32Array(LUT_N + 1);
  for (var li = 0; li <= LUT_N; li++) LUT[li] = Math.exp(-0.5 * li / LUT_S);

  function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }
  function logit(p) { p = Math.min(0.999, Math.max(0.001, p)); return Math.log(p / (1 - p)); }

  // Small deterministic RNG so runs are repeatable.
  function rng(seed) {
    var s = seed >>> 0 || 1;
    return function () {
      s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0;
      return s / 4294967296;
    };
  }
  function gauss(rand) {
    var u = 1 - rand(), v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  function Model(cap) {
    this.cap = cap;
    this.n = 0;
    this.p = new Float64Array(cap * P);   // parameters
    this.g = new Float64Array(cap * P);   // gradients
    this.m = new Float64Array(cap * P);   // Adam first moment
    this.v = new Float64Array(cap * P);   // Adam second moment
    this.gacc = new Float64Array(cap);    // accumulated |d L / d mean|
    this.gcnt = new Uint32Array(cap);     // steps in which the Gaussian was visible
    this.t = 0;                           // optimiser step
  }

  // Append a Gaussian given in "human" units (pixels, radians, 0..1).
  Model.prototype.add = function (mx, my, sx, sy, th, r, g, b, op) {
    if (this.n >= this.cap) return -1;
    var o = this.n * P, p = this.p;
    p[o] = mx; p[o + 1] = my;
    p[o + 2] = Math.log(sx); p[o + 3] = Math.log(sy);
    p[o + 4] = th;
    p[o + 5] = logit(r); p[o + 6] = logit(g); p[o + 7] = logit(b);
    p[o + 8] = logit(op);
    for (var k = 0; k < P; k++) { this.m[o + k] = 0; this.v[o + k] = 0; }
    this.gacc[this.n] = 0; this.gcnt[this.n] = 0;
    return this.n++;
  };

  // Human-readable view of Gaussian i (for drawing ellipses and read-outs).
  Model.prototype.get = function (i) {
    var o = i * P, p = this.p;
    return {
      x: p[o], y: p[o + 1], sx: Math.exp(p[o + 2]), sy: Math.exp(p[o + 3]), th: p[o + 4],
      r: sigmoid(p[o + 5]), g: sigmoid(p[o + 6]), b: sigmoid(p[o + 7]), op: sigmoid(p[o + 8])
    };
  };

  // Work buffers for one resolution. Float64Array is only needed for gradcheck.
  function Frame(w, h, Arr) {
    Arr = Arr || Float32Array;
    this.w = w; this.h = h;
    this.color = new Arr(w * h * 3);
    this.T = new Arr(w * h);                 // transmittance after the last contributor
    this.stop = new Int32Array(w * h);       // index of the Gaussian that saturated the pixel
    this.behind = new Arr(w * h * 3);
    this.Tb = new Arr(w * h);
    this.dC = new Arr(w * h * 3);
  }

  // Per-Gaussian quantities shared by the forward and backward passes.
  function setup(p, o, scale, w, h, out) {
    var mx = p[o] * scale, my = p[o + 1] * scale;
    var sx = Math.exp(p[o + 2]) * scale, sy = Math.exp(p[o + 3]) * scale;
    var th = p[o + 4];
    var c = Math.cos(th), s = Math.sin(th);
    var u = 1 / (sx * sx), v = 1 / (sy * sy);
    out.mx = mx; out.my = my; out.c = c; out.s = s; out.u = u; out.v = v;
    // inverse covariance [[A, B], [B, C]] = R diag(u, v) R^T
    out.A = c * c * u + s * s * v;
    out.B = c * s * (u - v);
    out.C = s * s * u + c * c * v;
    // tight 3-sigma box from the covariance diagonal
    var rx = 3 * Math.sqrt(c * c * sx * sx + s * s * sy * sy);
    var ry = 3 * Math.sqrt(s * s * sx * sx + c * c * sy * sy);
    out.x0 = Math.max(0, Math.floor(mx - rx));
    out.x1 = Math.min(w - 1, Math.floor(mx + rx));
    out.y0 = Math.max(0, Math.floor(my - ry));
    out.y1 = Math.min(h - 1, Math.floor(my + ry));
    out.op = sigmoid(p[o + 8]);
    out.r = sigmoid(p[o + 5]); out.g = sigmoid(p[o + 6]); out.b = sigmoid(p[o + 7]);
  }

  var S = {};

  /*
   * Forward pass. Front-to-back compositing:
   *   C = sum_i c_i a_i T_i + bg T_final,   T_i = prod_{j<i} (1 - a_j)
   * `scale` renders the same model at a higher resolution (display only).
   */
  function render(model, f, bg, opts) {
    var scale = (opts && opts.scale) || 1;
    var exact = !!(opts && opts.exact);
    var w = f.w, h = f.h, n = model.n, p = model.p;
    var color = f.color, T = f.T, stop = f.stop;
    color.fill(0); T.fill(1); stop.fill(n);
    for (var i = 0; i < n; i++) {
      setup(p, i * P, scale, w, h, S);
      if (S.x0 > S.x1 || S.y0 > S.y1) continue;
      var A = S.A, B2 = 2 * S.B, C = S.C, mx = S.mx, my = S.my, op = S.op;
      var cr = S.r, cg = S.g, cb = S.b;
      for (var y = S.y0; y <= S.y1; y++) {
        var dy = y + 0.5 - my, bdy = B2 * dy, cdy = C * dy * dy;
        // only the pixels of this row that lie inside the 3-sigma ellipse
        var disc = 0.25 * bdy * bdy - A * (cdy - CUT);
        if (disc <= 0) continue;
        var half = Math.sqrt(disc) / A, mid = mx - 0.5 * bdy / A - 0.5;
        var xa = Math.max(S.x0, Math.ceil(mid - half)), xb = Math.min(S.x1, Math.floor(mid + half));
        var idx = y * w + xa;
        for (var x = xa; x <= xb; x++, idx++) {
          var dx = x + 0.5 - mx;
          var q = A * dx * dx + bdy * dx + cdy;
          if (q >= CUT) continue;
          var Ti = T[idx];
          if (Ti < T_MIN) continue;
          var a = op * (exact ? Math.exp(-0.5 * q) : LUT[(q * LUT_S) | 0]);
          if (a < ALPHA_MIN) continue;
          if (a > ALPHA_MAX) a = ALPHA_MAX;
          var wgt = a * Ti, k = idx * 3;
          color[k] += cr * wgt; color[k + 1] += cg * wgt; color[k + 2] += cb * wgt;
          var Tn = Ti * (1 - a);
          T[idx] = Tn;
          if (Tn < T_MIN) stop[idx] = i;
        }
      }
    }
    for (var j = 0, kk = 0; j < w * h; j++, kk += 3) {
      var t = T[j];
      color[kk] += bg[0] * t; color[kk + 1] += bg[1] * t; color[kk + 2] += bg[2] * t;
    }
  }

  /*
   * Loss = mean squared error over pixels and channels. Fills f.dC with
   * dLoss/dC and returns the MSE.
   */
  function loss(f, target) {
    var color = f.color, dC = f.dC, len = color.length, se = 0;
    var k2 = 2 / len;
    for (var i = 0; i < len; i++) {
      var d = color[i] - target[i];
      se += d * d;
      dC[i] = k2 * d;
    }
    return se / len;
  }

  /*
   * Backward pass, walking Gaussians back to front. For each pixel we keep
   *   Tb     = transmittance just after Gaussian i (recovered by division)
   *   behind = colour contributed by everything behind i, background included
   * and use  dC/da_i = c_i T_i - behind_i / (1 - a_i).
   * Gradients are added to model.g (the caller zeroes it).
   */
  function backward(model, f, bg, opts) {
    var exact = !!(opts && opts.exact);
    var w = f.w, h = f.h, n = model.n, p = model.p, G = model.g;
    var dC = f.dC, stop = f.stop, Tb = f.Tb, behind = f.behind;
    Tb.set(f.T);
    for (var j = 0, kk = 0; j < w * h; j++, kk += 3) {
      var t = f.T[j];
      behind[kk] = bg[0] * t; behind[kk + 1] = bg[1] * t; behind[kk + 2] = bg[2] * t;
    }
    for (var i = n - 1; i >= 0; i--) {
      var o = i * P;
      setup(p, o, 1, w, h, S);
      if (S.x0 > S.x1 || S.y0 > S.y1) continue;
      var A = S.A, B = S.B, C = S.C, mx = S.mx, my = S.my, op = S.op;
      var cr = S.r, cg = S.g, cb = S.b;
      var gA = 0, gB = 0, gC = 0, gmx = 0, gmy = 0, gop = 0, gr = 0, gg = 0, gb = 0;
      var touched = false;
      for (var y = S.y0; y <= S.y1; y++) {
        var dy = y + 0.5 - my;
        var disc = B * B * dy * dy - A * (C * dy * dy - CUT);
        if (disc <= 0) continue;
        var half = Math.sqrt(disc) / A, mid = mx - B * dy / A - 0.5;
        var xa = Math.max(S.x0, Math.ceil(mid - half)), xb = Math.min(S.x1, Math.floor(mid + half));
        var idx = y * w + xa;
        for (var x = xa; x <= xb; x++, idx++) {
          if (i > stop[idx]) continue;
          var dx = x + 0.5 - mx;
          var q = A * dx * dx + 2 * B * dx * dy + C * dy * dy;
          if (q >= CUT) continue;
          var gv = exact ? Math.exp(-0.5 * q) : LUT[(q * LUT_S) | 0];
          var a0 = op * gv;
          if (a0 < ALPHA_MIN) continue;
          var clamped = a0 > ALPHA_MAX;
          var a = clamped ? ALPHA_MAX : a0;
          var inv = 1 / (1 - a);
          var Ti = Tb[idx] * inv;           // transmittance in front of Gaussian i
          var k = idx * 3;
          var d0 = dC[k], d1 = dC[k + 1], d2 = dC[k + 2];
          var wgt = a * Ti;
          gr += d0 * wgt; gg += d1 * wgt; gb += d2 * wgt;
          var dLda = d0 * (cr * Ti - behind[k] * inv)
                   + d1 * (cg * Ti - behind[k + 1] * inv)
                   + d2 * (cb * Ti - behind[k + 2] * inv);
          behind[k] += cr * wgt; behind[k + 1] += cg * wgt; behind[k + 2] += cb * wgt;
          Tb[idx] = Ti;
          touched = true;
          if (clamped) continue;
          gop += dLda * gv;
          var dLdq = -0.5 * a * dLda;
          gA += dLdq * dx * dx;
          gB += dLdq * 2 * dx * dy;
          gC += dLdq * dy * dy;
          gmx -= dLdq * (2 * A * dx + 2 * B * dy);
          gmy -= dLdq * (2 * B * dx + 2 * C * dy);
        }
      }
      if (!touched) continue;
      var c = S.c, s = S.s, u = S.u, v = S.v;
      var cc = c * c, ss = s * s, cs = c * s;
      var dLdu = gA * cc + gB * cs + gC * ss;
      var dLdv = gA * ss - gB * cs + gC * cc;
      var dLdth = gA * 2 * cs * (v - u) + gB * (cc - ss) * (u - v) + gC * 2 * cs * (u - v);
      G[o] += gmx;
      G[o + 1] += gmy;
      G[o + 2] += dLdu * -2 * u;
      G[o + 3] += dLdv * -2 * v;
      G[o + 4] += dLdth;
      G[o + 5] += gr * cr * (1 - cr);
      G[o + 6] += gg * cg * (1 - cg);
      G[o + 7] += gb * cb * (1 - cb);
      G[o + 8] += gop * op * (1 - op);
      model.gacc[i] += Math.sqrt(gmx * gmx + gmy * gmy);
      model.gcnt[i] += 1;
    }
  }

  // Per-parameter learning rates: position (px), log-scale, rotation, colour, opacity.
  var LR = [0.35, 0.35, 0.03, 0.03, 0.03, 0.05, 0.05, 0.05, 0.05];

  function adam(model, posDecay) {
    var n = model.n * P, p = model.p, g = model.g, m = model.m, v = model.v;
    var t = ++model.t;
    var b1 = 0.9, b2 = 0.999;
    var c1 = 1 - Math.pow(b1, t), c2 = 1 - Math.pow(b2, t);
    for (var i = 0; i < n; i++) {
      var j = i % P;
      var gi = g[i];
      var mi = m[i] = b1 * m[i] + (1 - b1) * gi;
      var vi = v[i] = b2 * v[i] + (1 - b2) * gi * gi;
      var lr = j < 2 ? LR[j] * posDecay : LR[j];
      p[i] -= lr * (mi / c1) / (Math.sqrt(vi / c2) + 1e-15);
    }
  }

  /*
   * Adaptive density control (3DGS §5.2), with a budget:
   *  - prune Gaussians that became almost transparent or huge;
   *  - among Gaussians whose average positional gradient exceeds `thresh`,
   *    the strongest ones get a copy (small ones, "clone") or are replaced
   *    by two smaller ones sampled from themselves (large ones, "split",
   *    scale / 1.6), until the budget `maxN` is used up.
   */
  function densify(model, o) {
    var n = model.n, p = model.p;
    var keep = new Uint8Array(n), pick = new Uint8Array(n);
    var alive = 0, i;
    for (i = 0; i < n; i++) {
      var base = i * P;
      var opv = sigmoid(p[base + 8]);
      var smax = Math.exp(Math.max(p[base + 2], p[base + 3]));
      keep[i] = (opv >= o.minOpacity && smax <= o.maxScale) ? 1 : 0;
      alive += keep[i];
    }
    var cand = [];
    if (o.grow) {
      for (i = 0; i < n; i++) {
        if (!keep[i] || !model.gcnt[i]) continue;
        var avg = model.gacc[i] / model.gcnt[i];
        if (avg > o.thresh) cand.push([avg, i]);
      }
      cand.sort(function (a, b) { return b[0] - a[0]; });
      var room = Math.min(o.maxN - alive, Math.ceil(alive * o.growFrac) + 4);
      if (room < 0) room = 0;
      if (cand.length > room) cand.length = room;
      for (i = 0; i < cand.length; i++) pick[cand[i][1]] = 1;
    }
    var P0 = p, M0 = model.m, V0 = model.v, G0 = model.gacc, C0 = model.gcnt;
    var np = new Float64Array(model.cap * P), nm = new Float64Array(model.cap * P), nv = new Float64Array(model.cap * P);
    var out = 0, clones = 0, splits = 0, pruned = n - alive;
    var rand = o.rand;
    function copy(src, fresh) {
      var d = out * P, sidx = src * P;
      for (var k = 0; k < P; k++) {
        np[d + k] = P0[sidx + k];
        nm[d + k] = fresh ? 0 : M0[sidx + k];
        nv[d + k] = fresh ? 0 : V0[sidx + k];
      }
      return d;
    }
    for (i = 0; i < n; i++) {
      if (!keep[i]) continue;
      if (out >= model.cap) break;
      if (!pick[i]) { copy(i, false); out++; continue; }
      var bi = i * P;
      var sx = Math.exp(P0[bi + 2]), sy = Math.exp(P0[bi + 3]);
      var gdx = 0, gdy = 0;
      if (Math.max(sx, sy) > o.splitScale) {
        // split: two children sampled from the parent, both 1.6x smaller
        var c = Math.cos(P0[bi + 4]), s = Math.sin(P0[bi + 4]);
        for (var kids = 0; kids < 2 && out < model.cap; kids++) {
          var d = copy(i, true);
          var ex = gauss(rand) * sx, ey = gauss(rand) * sy;
          np[d] += c * ex - s * ey;
          np[d + 1] += s * ex + c * ey;
          np[d + 2] -= Math.log(1.6);
          np[d + 3] -= Math.log(1.6);
          out++;
        }
        splits++;
      } else {
        // clone: keep the original, add a copy nudged down the gradient
        copy(i, false); out++;
        if (out >= model.cap) break;
        gdx = model.g[bi]; gdy = model.g[bi + 1];
        var gl = Math.sqrt(gdx * gdx + gdy * gdy) || 1;
        var d2 = copy(i, true);
        np[d2] -= 0.5 * gdx / gl;
        np[d2 + 1] -= 0.5 * gdy / gl;
        out++;
        clones++;
      }
    }
    model.p = np; model.m = nm; model.v = nv; model.n = out;
    model.gacc = new Float64Array(model.cap);
    model.gcnt = new Uint32Array(model.cap);
    model.g = new Float64Array(model.cap * P);
    return { clones: clones, splits: splits, pruned: pruned, n: out };
  }

  /*
   * Trainer: one model fitting one target image.
   * target: Float32Array(w*h*3) in 0..1.
   */
  function Trainer(target, w, h, cfg) {
    cfg = cfg || {};
    this.w = w; this.h = h; this.target = target;
    this.bg = cfg.bg || [0, 0, 0];
    this.grow = cfg.grow !== false;
    this.maxN = cfg.maxN || 1000;
    this.every = cfg.every || 50;           // densify interval (steps)
    this.stopGrowAt = cfg.stopGrowAt || 2400;
    this.decaySteps = cfg.decaySteps || 3000;
    this.thresh = cfg.thresh != null ? cfg.thresh : 2e-6;
    this.frame = new Frame(w, h);
    this.model = new Model(Math.max(this.maxN, cfg.n0 || 100) + 8);
    this.rand = rng(cfg.seed || 7);
    this.step = 0;
    this.mse = 1;
    this.lastEvent = null;
    this.init(cfg.n0 || 100, cfg.initScale || Math.max(w, h) / 24, cfg.randomColor);
  }

  // Initialise like 3DGS: sparse "points" that take the colour of the target
  // where they land (standing in for coloured SfM points).
  Trainer.prototype.init = function (n0, s0, randomColor) {
    var w = this.w, h = this.h, t = this.target, rand = this.rand;
    for (var i = 0; i < n0; i++) {
      var x = rand() * w, y = rand() * h;
      var k = ((y | 0) * w + (x | 0)) * 3;
      var r = randomColor ? rand() : t[k], g = randomColor ? rand() : t[k + 1], b = randomColor ? rand() : t[k + 2];
      this.model.add(x, y, s0 * (0.7 + 0.6 * rand()), s0 * (0.7 + 0.6 * rand()), rand() * Math.PI,
        0.1 + 0.8 * r, 0.1 + 0.8 * g, 0.1 + 0.8 * b, 0.5);
    }
  };

  Trainer.prototype.stepOnce = function () {
    var m = this.model, f = this.frame;
    render(m, f, this.bg);
    this.mse = loss(f, this.target);
    m.g.fill(0, 0, m.n * P);
    backward(m, f, this.bg);
    var decay = Math.pow(0.1, Math.min(this.step, this.decaySteps) / this.decaySteps);
    adam(m, decay);
    this.step++;
    // With densification off the count stays fixed: no cloning, splitting or pruning.
    if (this.grow && this.step % this.every === 0 && this.step <= this.stopGrowAt) {
      this.lastEvent = densify(m, {
        grow: true, maxN: this.maxN, thresh: this.thresh, growFrac: 0.35,
        splitScale: Math.max(this.w, this.h) / 60, maxScale: Math.max(this.w, this.h) / 3,
        minOpacity: 0.02, rand: this.rand
      });
    }
    return this.mse;
  };

  Trainer.prototype.psnr = function () {
    return 10 * Math.log10(1 / Math.max(this.mse, 1e-10));
  };

  var api = {
    P: P, Model: Model, Frame: Frame, render: render, loss: loss, backward: backward,
    adam: adam, densify: densify, Trainer: Trainer, sigmoid: sigmoid, logit: logit, rng: rng
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Splat2D = api;
})(this);
