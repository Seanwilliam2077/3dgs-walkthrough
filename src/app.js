/* app.js — page behaviour: theme, hero, the three demos, chart, catalogue filter, back-to-overview. */
(function () {
  'use strict';
  var S = window.Splat2D;
  var Scenes = window.Scenes;
  var mm = window.matchMedia ? function (q) { return window.matchMedia(q); } : function () { return { matches: false, addEventListener: function () {} }; };
  var reduceMotion = mm('(prefers-reduced-motion: reduce)').matches;
  var $ = function (id) { return document.getElementById(id); };

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function hexRgb(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.replace(/./g, '$&$&');
    var n = parseInt(hex, 16);
    return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255];
  }
  function rgbCss(c, a) {
    var r = Math.round(c[0] * 255), g = Math.round(c[1] * 255), b = Math.round(c[2] * 255);
    return a == null ? 'rgb(' + r + ',' + g + ',' + b + ')' : 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }
  function hsl(h, s, l) {
    var a = s * Math.min(l, 1 - l);
    var f = function (n) { var k = (n + h / 30) % 12; return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)); };
    return [f(0), f(8), f(4)];
  }
  function fmt(x, d) { return Number(x).toFixed(d); }
  function dpr() { return Math.min(window.devicePixelRatio || 1, 2); }

  // Keep a canvas' backing store in step with its CSS size.
  function fitCanvas(canvas, aspect) {
    var w = Math.max(64, Math.round(canvas.clientWidth * dpr()));
    var h = Math.round(w / aspect);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; return true; }
    return false;
  }

  // Float RGB buffer -> small canvas that can be drawn scaled.
  function toCanvas(rgb, w, h, cache) {
    var c = cache.c || (cache.c = document.createElement('canvas'));
    if (c.width !== w || c.height !== h) { c.width = w; c.height = h; cache.img = null; }
    var ctx = c.getContext('2d');
    var img = cache.img || (cache.img = ctx.createImageData(w, h));
    var d = img.data;
    for (var i = 0, j = 0, k = 0, n = w * h; i < n; i++, j += 3, k += 4) {
      d[k] = rgb[j] * 255; d[k + 1] = rgb[j + 1] * 255; d[k + 2] = rgb[j + 2] * 255; d[k + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    return c;
  }

  function onVisible(el, cb) {
    if (typeof window.IntersectionObserver !== 'function') { cb(true); return; }
    new IntersectionObserver(function (es) { es.forEach(function (e) { cb(e.isIntersecting); }); }, { threshold: 0.15 }).observe(el);
  }

  /* ------------------------------------------------------------------ theme */
  (function theme() {
    var btn = $('theme-toggle');
    var order = ['system', 'light', 'dark'];
    var names = { system: '跟随系统', light: '浅色', dark: '深色' };
    var cur = 'system';
    try { cur = localStorage.getItem('theme') || 'system'; } catch (e) { /* storage blocked */ }
    if (order.indexOf(cur) < 0) cur = 'system';
    function apply(v, save) {
      if (v === 'system') document.documentElement.removeAttribute('data-theme');
      else document.documentElement.setAttribute('data-theme', v);
      btn.querySelector('.label').textContent = names[v];
      btn.setAttribute('aria-label', '配色：' + names[v] + '，点击切换');
      if (save) { try { localStorage.setItem('theme', v); } catch (e) { /* ignore */ } }
      document.dispatchEvent(new Event('themechange'));
    }
    apply(cur, false);
    btn.addEventListener('click', function () { cur = order[(order.indexOf(cur) + 1) % order.length]; apply(cur, true); });
    var q = mm('(prefers-color-scheme: dark)');
    if (q.addEventListener) q.addEventListener('change', function () { document.dispatchEvent(new Event('themechange')); });
  })();

  /* --------------------------------------------------------- WebGL display */
  // Renders a trained model at display resolution. Training stays on the CPU;
  // this only draws. Falls back to upscaling the CPU frame when WebGL2 is missing.
  var GL = (function () {
    var canvas = document.createElement('canvas');
    var gl = null;
    try { gl = canvas.getContext('webgl2', { alpha: false, antialias: false, premultipliedAlpha: true, preserveDrawingBuffer: true }); } catch (e) { gl = null; }
    if (!gl) return null;
    var VS = '#version 300 es\n' +
      'layout(location=0) in vec2 aCorner;\nlayout(location=1) in vec2 aCenter;\nlayout(location=2) in vec3 aConic;\n' +
      'layout(location=3) in vec4 aColor;\nlayout(location=4) in vec2 aExtent;\nuniform vec2 uView;\n' +
      'out vec2 vD;\nflat out vec3 vConic;\nflat out vec4 vColor;\n' +
      'void main(){ vec2 d = aCorner * aExtent; vD = d; vConic = aConic; vColor = aColor;\n' +
      '  vec2 ndc = (aCenter + d) / uView * 2.0 - 1.0; gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0); }';
    var FS = '#version 300 es\nprecision highp float;\n' +
      'in vec2 vD;\nflat in vec3 vConic;\nflat in vec4 vColor;\nout vec4 o;\n' +
      'void main(){ float q = vConic.x*vD.x*vD.x + 2.0*vConic.y*vD.x*vD.y + vConic.z*vD.y*vD.y;\n' +
      '  if (q >= 9.0) discard; float a = min(0.99, vColor.a * exp(-0.5*q)); if (a < 1.0/255.0) discard;\n' +
      '  o = vec4(vColor.rgb * a, a); }';
    function shader(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    }
    var prog = gl.createProgram();
    try {
      gl.attachShader(prog, shader(gl.VERTEX_SHADER, VS));
      gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FS));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    } catch (e) {
      if (window.console) console.warn('WebGL splat renderer unavailable:', e);
      return null;
    }
    var uView = gl.getUniformLocation(prog, 'uView');
    var vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    var inst = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, inst);
    var STRIDE = 11;
    [[1, 2, 0], [2, 3, 2], [3, 4, 5], [4, 2, 9]].forEach(function (l) {
      gl.enableVertexAttribArray(l[0]);
      gl.vertexAttribPointer(l[0], l[1], gl.FLOAT, false, STRIDE * 4, l[2] * 4);
      gl.vertexAttribDivisor(l[0], 1);
    });
    var buf = new Float32Array(STRIDE * 512);
    var sig = S.sigmoid;
    function draw(model, scale, w, h, bg) {
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      var n = model.n, p = model.p, P = S.P, k = 0;
      if (buf.length < n * STRIDE) buf = new Float32Array(n * 2 * STRIDE);
      for (var i = n - 1; i >= 0; i--) {           // back to front for "over" blending
        var o = i * P;
        var sx = Math.exp(p[o + 2]) * scale, sy = Math.exp(p[o + 3]) * scale;
        var c = Math.cos(p[o + 4]), s = Math.sin(p[o + 4]);
        var u = 1 / (sx * sx), v = 1 / (sy * sy);
        buf[k++] = p[o] * scale; buf[k++] = p[o + 1] * scale;
        buf[k++] = c * c * u + s * s * v; buf[k++] = c * s * (u - v); buf[k++] = s * s * u + c * c * v;
        buf[k++] = sig(p[o + 5]); buf[k++] = sig(p[o + 6]); buf[k++] = sig(p[o + 7]); buf[k++] = sig(p[o + 8]);
        buf[k++] = 3 * Math.sqrt(c * c * sx * sx + s * s * sy * sy) + 1;
        buf[k++] = 3 * Math.sqrt(s * s * sx * sx + c * c * sy * sy) + 1;
      }
      gl.viewport(0, 0, w, h);
      gl.clearColor(bg[0], bg[1], bg[2], 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      if (n) {
        gl.useProgram(prog);
        gl.bindVertexArray(vao);
        gl.uniform2f(uView, w, h);
        gl.bindBuffer(gl.ARRAY_BUFFER, inst);
        gl.bufferData(gl.ARRAY_BUFFER, buf.subarray(0, k), gl.DYNAMIC_DRAW);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, n);
      }
      return canvas;
    }
    return { draw: draw };
  })();

  // Draw a model into a visible canvas: GPU if possible, else upscale the CPU frame.
  function paintModel(ctx, model, frame, trainW, bg, cache) {
    var cv = ctx.canvas;
    if (GL) {
      ctx.drawImage(GL.draw(model, cv.width / trainW, cv.width, cv.height, bg), 0, 0);
    } else {
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(toCanvas(frame.color, frame.w, frame.h, cache), 0, 0, cv.width, cv.height);
    }
  }

  // Outline every Gaussian as its 2-sigma ellipse.
  function paintEllipses(ctx, model, scale, bgCss, clear) {
    var cv = ctx.canvas;
    if (clear) { ctx.fillStyle = bgCss; ctx.fillRect(0, 0, cv.width, cv.height); }
    ctx.lineWidth = Math.max(1, dpr() * 0.75);
    for (var i = model.n - 1; i >= 0; i--) {
      var g = model.get(i);
      var rx = 2 * g.sx * scale, ry = 2 * g.sy * scale;
      if (rx < 0.5 && ry < 0.5) continue;
      ctx.beginPath();
      ctx.ellipse(g.x * scale, g.y * scale, Math.max(rx, 0.5), Math.max(ry, 0.5), g.th, 0, Math.PI * 2);
      if (clear) { ctx.fillStyle = rgbCss([g.r, g.g, g.b], 0.18 * g.op); ctx.fill(); }
      ctx.strokeStyle = rgbCss([g.r, g.g, g.b], clear ? 0.9 : 0.75);
      ctx.stroke();
    }
  }

  /* ------------------------------------------------------------------- hero */
  (function hero() {
    var canvas = $('hero-canvas');
    if (!canvas || !S) return;
    var ctx = canvas.getContext('2d');
    var W = 240, H = 80, MAX = 1500;
    var BG = hexRgb('#14110b');
    var showEllipses = false, trainer, cache = {}, visible = true, raf = 0;

    function makeTarget() {
      var c = document.createElement('canvas');
      c.width = W; c.height = H;
      var x = c.getContext('2d');
      x.fillStyle = rgbCss(BG);
      x.fillRect(0, 0, W, H);
      var grad = x.createLinearGradient(44, 0, 196, 0);
      grad.addColorStop(0, '#4fc0ae');
      grad.addColorStop(0.36, '#7fa3d8');
      grad.addColorStop(0.68, '#e3b45f');
      grad.addColorStop(1, '#dd7a4c');
      x.fillStyle = grad;
      x.font = '800 66px ' + cssVar('--font-sans');
      x.textAlign = 'center';
      x.textBaseline = 'middle';
      x.fillText('3DGS', W / 2, H / 2 + 3);
      var d = x.getImageData(0, 0, W, H).data, t = new Float32Array(W * H * 3);
      for (var i = 0, j = 0; i < W * H; i++, j += 3) { t[j] = d[i * 4] / 255; t[j + 1] = d[i * 4 + 1] / 255; t[j + 2] = d[i * 4 + 2] / 255; }
      return t;
    }
    function reset() {
      trainer = new S.Trainer(makeTarget(), W, H, {
        bg: BG, n0: 90, maxN: 1100, every: 40, stopGrowAt: 1400, decaySteps: 1600,
        initScale: 7, randomColor: true, seed: 11
      });
      paint();
    }
    function paint() {
      fitCanvas(canvas, 3);
      if (!GL && !trainer.step) S.render(trainer.model, trainer.frame, trainer.bg);
      paintModel(ctx, trainer.model, trainer.frame, W, hexRgb(cssVar('--stage')), cache);
      if (showEllipses) paintEllipses(ctx, trainer.model, canvas.width / W, null, false);
      $('hero-step').textContent = trainer.step;
      $('hero-n').textContent = trainer.model.n;
      $('hero-psnr').textContent = trainer.step ? fmt(trainer.psnr(), 1) : '–';
    }
    function tick() {
      raf = 0;
      if (!visible || trainer.step >= MAX) return;
      var t0 = performance.now();
      while (performance.now() - t0 < 10 && trainer.step < MAX) trainer.stepOnce();
      paint();
      raf = requestAnimationFrame(tick);
    }
    function start() { if (!raf && !reduceMotion) raf = requestAnimationFrame(tick); }
    function runStill() {
      // Reduced motion: train off-screen in chunks, then show the result once.
      (function chunk() {
        var t0 = performance.now();
        while (performance.now() - t0 < 30 && trainer.step < MAX) trainer.stepOnce();
        if (trainer.step < MAX) setTimeout(chunk, 0); else paint();
      })();
    }
    $('hero-restart').addEventListener('click', function () { reset(); if (reduceMotion) runStill(); else start(); });
    $('hero-ellipses').addEventListener('click', function () {
      showEllipses = !showEllipses;
      this.setAttribute('aria-pressed', String(showEllipses));
      paint();
    });
    document.addEventListener('themechange', paint);
    window.addEventListener('resize', function () { paint(); });
    reset();
    onVisible(canvas, function (v) { visible = v; if (v) start(); });
    if (reduceMotion) runStill(); else start();
  })();

  /* ------------------------------------------------ demo 1: one Gaussian */
  (function single() {
    var canvas = $('single-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var ids = ['g-sx', 'g-sy', 'g-sz', 'g-yaw', 'g-pitch', 'g-op', 'g-hue'];
    var inp = {}, mouse = null;
    ids.forEach(function (id) { inp[id] = $(id); inp[id].addEventListener('input', draw); });
    var ASPECT = 640 / 440;
    var img = null;

    function rotX(a) { var c = Math.cos(a), s = Math.sin(a); return [[1, 0, 0], [0, c, -s], [0, s, c]]; }
    function rotY(a) { var c = Math.cos(a), s = Math.sin(a); return [[c, 0, s], [0, 1, 0], [-s, 0, c]]; }
    function rotZ(a) { var c = Math.cos(a), s = Math.sin(a); return [[c, -s, 0], [s, c, 0], [0, 0, 1]]; }
    function mul(A, B) {
      var R = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
      for (var i = 0; i < 3; i++) for (var j = 0; j < 3; j++) for (var k = 0; k < 3; k++) R[i][j] += A[i][k] * B[k][j];
      return R;
    }
    function T(A) { return [[A[0][0], A[1][0], A[2][0]], [A[0][1], A[1][1], A[2][1]], [A[0][2], A[1][2], A[2][2]]]; }
    var R0 = mul(rotZ(0.45), rotX(0.35));   // the bean's own orientation in the world

    function state() {
      var v = function (id) { return +inp[id].value; };
      $('g-sx-o').textContent = v('g-sx');
      $('g-sy-o').textContent = v('g-sy');
      $('g-sz-o').textContent = v('g-sz');
      $('g-yaw-o').textContent = v('g-yaw') + '°';
      $('g-pitch-o').textContent = v('g-pitch') + '°';
      $('g-op-o').textContent = fmt(v('g-op') / 100, 2);
      $('g-hue-o').textContent = v('g-hue') + '°';
      var Sd = [[v('g-sx'), 0, 0], [0, v('g-sy'), 0], [0, 0, v('g-sz')]];
      var M = mul(R0, Sd);
      var Sigma = mul(M, T(M));                             // R S S^T R^T
      var V = mul(rotX(v('g-pitch') * Math.PI / 180), rotY(v('g-yaw') * Math.PI / 180));
      var Sc = mul(mul(V, Sigma), T(V));                    // W Sigma W^T
      return { Sigma: Sigma, V: V, S2: [Sc[0][0], Sc[0][1], Sc[1][1]], op: v('g-op') / 100, color: hsl(v('g-hue'), 0.78, 0.58) };
    }

    function draw() {
      fitCanvas(canvas, ASPECT);
      var w = canvas.width, h = canvas.height, k = w / 640;
      var st = state();
      var a = st.S2[0] * k * k, b = st.S2[1] * k * k, c = st.S2[2] * k * k;   // screen covariance in device px
      var det = a * c - b * b;
      var A = c / det, B = -b / det, C = a / det;
      var cx = w / 2, cy = h / 2;
      var bg = hexRgb(cssVar('--stage'));
      if (!img || img.width !== w || img.height !== h) img = ctx.createImageData(w, h);
      var d = img.data, col = st.color, op = st.op;
      var rx = 3 * Math.sqrt(a), ry = 3 * Math.sqrt(c);
      var x0 = Math.max(0, Math.floor(cx - rx)), x1 = Math.min(w - 1, Math.ceil(cx + rx));
      var y0 = Math.max(0, Math.floor(cy - ry)), y1 = Math.min(h - 1, Math.ceil(cy + ry));
      var br = bg[0] * 255, bgg = bg[1] * 255, bb = bg[2] * 255;
      for (var i = 0; i < w * h * 4; i += 4) { d[i] = br; d[i + 1] = bgg; d[i + 2] = bb; d[i + 3] = 255; }
      for (var y = y0; y <= y1; y++) {
        var dy = y + 0.5 - cy;
        for (var x = x0; x <= x1; x++) {
          var dx = x + 0.5 - cx;
          var q = A * dx * dx + 2 * B * dx * dy + C * dy * dy;
          if (q >= 9) continue;
          var al = Math.min(0.99, op * Math.exp(-0.5 * q));
          if (al < 1 / 255) continue;
          var o = (y * w + x) * 4;
          d[o] = br + (col[0] * 255 - br) * al;
          d[o + 1] = bgg + (col[1] * 255 - bgg) * al;
          d[o + 2] = bb + (col[2] * 255 - bb) * al;
        }
      }
      ctx.putImageData(img, 0, 0);

      // contours at 1, 2, 3 sigma from the eigen-decomposition of the 2x2 covariance
      var tr = a + c, disc = Math.sqrt(Math.max(0, (a - c) * (a - c) / 4 + b * b));
      var l1 = tr / 2 + disc, l2 = Math.max(1e-9, tr / 2 - disc);
      var ang = 0.5 * Math.atan2(2 * b, a - c);
      ctx.lineWidth = Math.max(1, k);
      [1, 2, 3].forEach(function (s, idx) {
        ctx.beginPath();
        ctx.ellipse(cx, cy, s * Math.sqrt(l1), s * Math.sqrt(l2), ang, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(230,240,242,' + (0.55 - idx * 0.15) + ')';
        ctx.stroke();
      });
      // principal axes
      ctx.beginPath();
      ctx.moveTo(cx - Math.cos(ang) * Math.sqrt(l1) * 3, cy - Math.sin(ang) * Math.sqrt(l1) * 3);
      ctx.lineTo(cx + Math.cos(ang) * Math.sqrt(l1) * 3, cy + Math.sin(ang) * Math.sqrt(l1) * 3);
      ctx.moveTo(cx + Math.sin(ang) * Math.sqrt(l2) * 3, cy - Math.cos(ang) * Math.sqrt(l2) * 3);
      ctx.lineTo(cx - Math.sin(ang) * Math.sqrt(l2) * 3, cy + Math.cos(ang) * Math.sqrt(l2) * 3);
      ctx.strokeStyle = 'rgba(230,240,242,0.25)';
      ctx.stroke();
      // view gizmo: world axes seen from the current camera
      var gx = 46 * k, gy = h - 46 * k, L = 28 * k;
      var axes = [['X', '#ff6b5e', [1, 0, 0]], ['Y', '#52d17c', [0, 1, 0]], ['Z', '#6aa7ff', [0, 0, 1]]];
      ctx.font = Math.round(12 * k) + 'px ' + cssVar('--font-mono');
      axes.forEach(function (ax) {
        var e = ax[2], V = st.V;
        var px = V[0][0] * e[0] + V[0][1] * e[1] + V[0][2] * e[2];
        var py = V[1][0] * e[0] + V[1][1] * e[1] + V[1][2] * e[2];
        ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(gx + px * L, gy - py * L);
        ctx.strokeStyle = ax[1]; ctx.lineWidth = 2 * k; ctx.stroke();
        ctx.fillStyle = ax[1]; ctx.fillText(ax[0], gx + px * (L + 8 * k) - 4 * k, gy - py * (L + 8 * k) + 4 * k);
      });
      if (mouse) {
        ctx.beginPath(); ctx.arc(mouse.x * k, mouse.y * k, 4 * k, 0, Math.PI * 2);
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5 * k; ctx.stroke();
      }

      var s1 = Math.sqrt(l1) / k, s2 = Math.sqrt(l2) / k, deg = ang * 180 / Math.PI;
      var M = st.Sigma, P = function (x) { return (x >= 0 ? ' ' : '') + fmt(x, 0); };
      var pad = function (x) { var t = P(x); return '      '.slice(t.length) + t; };
      var lines = [
        '<b>3D 协方差 Σ</b>（世界坐标，px²）',
        '[' + pad(M[0][0]) + pad(M[0][1]) + pad(M[0][2]) + ' ]',
        '[' + pad(M[1][0]) + pad(M[1][1]) + pad(M[1][2]) + ' ]',
        '[' + pad(M[2][0]) + pad(M[2][1]) + pad(M[2][2]) + ' ]',
        '<b>投影后 Σ′</b>（屏幕，px²）',
        '[' + pad(st.S2[0]) + pad(st.S2[1]) + ' ]',
        '[' + pad(st.S2[1]) + pad(st.S2[2]) + ' ]',
        '屏幕上的椭圆：半轴 <b>' + fmt(s1, 1) + '</b> 与 <b>' + fmt(s2, 1) + '</b> px，朝向 <b>' + fmt(deg, 0) + '°</b>'
      ];
      if (mouse) {
        var mx = mouse.x - 320, my = mouse.y - 220;
        var a2 = st.S2[0], b2 = st.S2[1], c2 = st.S2[2], dt = a2 * c2 - b2 * b2;
        var qq = (c2 * mx * mx - 2 * b2 * mx * my + a2 * my * my) / dt;
        var al2 = qq >= 9 ? 0 : Math.min(0.99, st.op * Math.exp(-0.5 * qq));
        if (al2 < 1 / 255) al2 = 0;
        lines.push('鼠标处：马氏距离² = <b>' + fmt(qq, 2) + '</b>，α = <b>' + fmt(al2, 3) + '</b>' + (qq >= 9 ? '（3σ 外，跳过）' : ''));
      } else {
        lines.push('把鼠标移到画面上，查看该点的 α');
      }
      $('single-readout').innerHTML = lines.join('\n');
    }
    function pos(e) {
      var r = canvas.getBoundingClientRect();
      return { x: (e.clientX - r.left) / r.width * 640, y: (e.clientY - r.top) / r.height * 440 };
    }
    canvas.addEventListener('pointermove', function (e) { mouse = pos(e); draw(); });
    canvas.addEventListener('pointerleave', function () { mouse = null; draw(); });
    document.addEventListener('themechange', draw);
    window.addEventListener('resize', draw);
    draw();
  })();

  /* ---------------------------------------- demo 2: order and blending */
  (function blend() {
    var canvas = $('blend-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var items = [
      { name: '红色高斯', color: hexRgb('#e5484d'), x: 272, y: 196, sx: 78, sy: 46, th: 0.5 },
      { name: '绿色高斯', color: hexRgb('#30a46c'), x: 370, y: 206, sx: 74, sy: 48, th: -0.55 },
      { name: '蓝色高斯', color: hexRgb('#3e63dd'), x: 318, y: 272, sx: 84, sy: 40, th: 0.05 }
    ];
    var order = [0, 1, 2];
    var probe = { x: 318, y: 222 };
    var model = new S.Model(3), frame = null, cache = {};
    var ASPECT = 640 / 440;
    var list = $('blend-order'), table = $('blend-table'), op = $('b-op');

    function build(scale) {
      model.n = 0;
      var o = +op.value / 100;
      order.forEach(function (idx) {
        var it = items[idx];
        model.add(it.x * scale, it.y * scale, it.sx * scale, it.sy * scale, it.th, it.color[0], it.color[1], it.color[2], Math.min(o, 0.995));
      });
    }
    function renderList() {
      list.innerHTML = '';
      order.forEach(function (idx, pos) {
        var it = items[idx];
        var li = document.createElement('li');
        li.innerHTML = '<span class="rank">' + (pos === 0 ? '最前' : pos === order.length - 1 ? '最后' : '第 ' + (pos + 1) + ' 层') + '</span>' +
          '<span class="dot" style="background:' + rgbCss(it.color) + '"></span><span class="name">' + it.name + '</span>';
        var up = document.createElement('button'), dn = document.createElement('button');
        up.className = dn.className = 'icon-btn';
        up.type = dn.type = 'button';
        up.textContent = '↑'; dn.textContent = '↓';
        up.setAttribute('aria-label', it.name + '往前移');
        dn.setAttribute('aria-label', it.name + '往后移');
        up.disabled = pos === 0; dn.disabled = pos === order.length - 1;
        up.addEventListener('click', function () { swap(pos, pos - 1); });
        dn.addEventListener('click', function () { swap(pos, pos + 1); });
        li.appendChild(up); li.appendChild(dn);
        list.appendChild(li);
      });
    }
    function swap(i, j) { var t = order[i]; order[i] = order[j]; order[j] = t; renderList(); draw(); }
    function draw() {
      fitCanvas(canvas, ASPECT);
      var w = canvas.width, h = canvas.height, k = w / 640;
      if (!frame || frame.w !== w || frame.h !== h) frame = new S.Frame(w, h);
      var bg = hexRgb(cssVar('--stage'));
      build(k);
      S.render(model, frame, bg, { exact: true });
      ctx.drawImage(toCanvas(frame.color, w, h, cache), 0, 0);
      // probe
      var px = probe.x * k, py = probe.y * k, r = 9 * k;
      ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5 * k;
      ctx.beginPath(); ctx.moveTo(px - r, py); ctx.lineTo(px + r, py); ctx.moveTo(px, py - r); ctx.lineTo(px, py + r); ctx.stroke();
      ctx.beginPath(); ctx.arc(px, py, 3 * k, 0, Math.PI * 2); ctx.stroke();
      $('b-op-o').textContent = fmt(+op.value / 100, 2);
      explain(bg);
    }
    // Recompute the compositing at the probe, exactly as the renderer does.
    function explain(bg) {
      var T = 1, acc = [0, 0, 0], rows = [], stopped = false;
      var o = Math.min(+op.value / 100, 0.995);
      order.forEach(function (idx, pos) {
        var it = items[idx];
        var sx = it.sx, sy = it.sy, c = Math.cos(it.th), s = Math.sin(it.th);
        var u = 1 / (sx * sx), v = 1 / (sy * sy);
        var dx = probe.x - it.x, dy = probe.y - it.y;
        var q = (c * c * u + s * s * v) * dx * dx + 2 * c * s * (u - v) * dx * dy + (s * s * u + c * c * v) * dy * dy;
        var a = q >= 9 ? 0 : Math.min(0.99, o * Math.exp(-0.5 * q));
        var note = '';
        if (stopped) { a = 0; note = '已提前停止'; }
        else if (q >= 9) note = '3σ 外';
        else if (a < 1 / 255) { a = 0; note = 'α 太小，跳过'; }
        var contrib = a * T;
        rows.push('<tr><td>' + (pos + 1) + '</td><td><span class="swatch" style="background:' + rgbCss(it.color) + '"></span> ' + it.name + '</td>' +
          '<td class="num">' + fmt(a, 3) + '</td><td class="num">' + fmt(T, 3) + '</td><td class="num">' + fmt(contrib, 3) + (note ? ' <span class="muted">' + note + '</span>' : '') + '</td></tr>');
        for (var ch = 0; ch < 3; ch++) acc[ch] += it.color[ch] * contrib;
        T *= (1 - a);
        if (T < 1e-4) stopped = true;
      });
      var fin = [acc[0] + bg[0] * T, acc[1] + bg[1] * T, acc[2] + bg[2] * T];
      rows.push('<tr><td></td><td><span class="swatch" style="background:' + rgbCss(bg) + '"></span> 背景</td><td class="num">—</td><td class="num">' + fmt(T, 3) + '</td><td class="num">' + fmt(T, 3) + '</td></tr>');
      table.innerHTML = '<thead><tr><th>层</th><th>高斯</th><th class="num">α</th><th class="num">到达前的 T</th><th class="num">权重 α·T</th></tr></thead><tbody>' +
        rows.join('') + '</tbody><tfoot><tr><th colspan="2">探针处的最终颜色</th><td colspan="3" class="num"><span class="swatch" style="background:' + rgbCss(fin) + '"></span> RGB ' +
        Math.round(fin[0] * 255) + ', ' + Math.round(fin[1] * 255) + ', ' + Math.round(fin[2] * 255) + '</td></tr></tfoot>';
    }
    function setProbe(e) {
      var r = canvas.getBoundingClientRect();
      probe = { x: Math.max(0, Math.min(639, (e.clientX - r.left) / r.width * 640)), y: Math.max(0, Math.min(439, (e.clientY - r.top) / r.height * 440)) };
      draw();
    }
    var dragging = false;
    canvas.addEventListener('pointerdown', function (e) { dragging = true; canvas.setPointerCapture(e.pointerId); setProbe(e); });
    canvas.addEventListener('pointermove', function (e) { if (dragging) setProbe(e); });
    canvas.addEventListener('pointerup', function () { dragging = false; });
    canvas.style.touchAction = 'none';
    op.addEventListener('input', draw);
    $('b-reverse').addEventListener('click', function () { order.reverse(); renderList(); draw(); });
    $('b-shuffle').addEventListener('click', function () {
      var before = order.join();
      while (order.join() === before) order.sort(function () { return Math.random() - 0.5; });
      renderList(); draw();
    });
    document.addEventListener('themechange', draw);
    window.addEventListener('resize', draw);
    renderList();
    draw();
  })();

  /* --------------------------------------------- demo 3: train in browser */
  (function fitter() {
    var root = $('fitter');
    if (!root || !S) return;
    var TW = 120, TH = 90, MAX = 2000, N0 = 120, BUDGET_MS = 12;
    var cvT = $('fit-target'), cvA = $('fit-a'), cvB = $('fit-b');
    var cT = cvT.getContext('2d'), cA = cvA.getContext('2d'), cB = cvB.getContext('2d');
    var target, bg, A, B, running = false, raf = 0, visible = false, started = false;
    var view = 'render', targetName = 'landscape', upload = null;
    var hist = [], cacheT = {}, cacheA = {}, cacheB = {}, errCache = {}, lastChart = 0, stepMs = 0;
    var log = $('fit-log'), runBtn = $('fit-run');
    var chart = Chart($('fit-chart'), $('fit-tip'), $('fit-table'), $('fit-data'), MAX);

    function textTarget() {
      var c = document.createElement('canvas');
      c.width = TW; c.height = TH;
      var x = c.getContext('2d');
      x.fillStyle = '#f2efe8'; x.fillRect(0, 0, TW, TH);
      x.textAlign = 'center'; x.textBaseline = 'middle';
      x.font = '800 36px ' + cssVar('--font-sans');
      x.fillStyle = '#3b3220'; x.fillText('高斯', TW / 2, 27);
      x.fillStyle = '#b06a3a'; x.fillText('泼溅', TW / 2, 66);
      return readCanvas(c);
    }
    function readCanvas(c) {
      var d = c.getContext('2d').getImageData(0, 0, TW, TH).data, t = new Float32Array(TW * TH * 3);
      for (var i = 0, j = 0; i < TW * TH; i++, j += 3) { t[j] = d[i * 4] / 255; t[j + 1] = d[i * 4 + 1] / 255; t[j + 2] = d[i * 4 + 2] / 255; }
      return t;
    }
    function makeTarget() {
      if (targetName === 'landscape') return Scenes.landscape(TW, TH);
      if (targetName === 'beans') return Scenes.beans(TW, TH);
      if (targetName === 'upload' && upload) return upload;
      return textTarget();
    }
    function reset() {
      target = makeTarget();
      var m = [0, 0, 0];
      for (var i = 0; i < target.length; i++) m[i % 3] += target[i];
      bg = m.map(function (v) { return v / (TW * TH); });
      var budget = +$('fit-budget').value;
      A = new S.Trainer(target, TW, TH, { bg: bg, grow: true, maxN: budget, n0: N0, seed: 5, stopGrowAt: 1500 });
      B = new S.Trainer(target, TW, TH, { bg: bg, grow: false, n0: N0, seed: 5 });
      hist = [{ step: 0, a: null, b: null }];
      chart.set(hist);
      paint(true);
      stats();
      log.textContent = started ? '已重置：两边都从同样的 ' + N0 + ' 个高斯出发。' : log.textContent;
    }
    function stats() {
      $('fit-a-stat').textContent = A.model.n + ' 个 · ' + (A.step ? fmt(A.psnr(), 1) + ' dB' : '–');
      $('fit-b-stat').textContent = B.model.n + ' 个 · ' + (B.step ? fmt(B.psnr(), 1) + ' dB' : '–');
    }
    function paintOne(ctx, tr, cache) {
      var cv = ctx.canvas;
      var stageBg = cssVar('--stage');
      if (!tr.step) S.render(tr.model, tr.frame, tr.bg);
      if (view === 'ellipse') {
        paintEllipses(ctx, tr.model, cv.width / TW, stageBg, true);
      } else if (view === 'error') {
        var f = tr.frame, e = errCache.buf || (errCache.buf = new Float32Array(TW * TH * 3));
        var hot = hexRgb('#e8944f'), base = hexRgb(stageBg);
        for (var i = 0, j = 0; i < TW * TH; i++, j += 3) {
          var d = (Math.abs(f.color[j] - target[j]) + Math.abs(f.color[j + 1] - target[j + 1]) + Math.abs(f.color[j + 2] - target[j + 2])) / 3;
          var t = Math.min(1, d * 5);
          e[j] = base[0] + (hot[0] - base[0]) * t; e[j + 1] = base[1] + (hot[1] - base[1]) * t; e[j + 2] = base[2] + (hot[2] - base[2]) * t;
        }
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(toCanvas(e, TW, TH, cache.err || (cache.err = {})), 0, 0, cv.width, cv.height);
      } else {
        paintModel(ctx, tr.model, tr.frame, TW, tr.bg, cache);
      }
    }
    function paint(all) {
      [cvT, cvA, cvB].forEach(function (c) { fitCanvas(c, 4 / 3); });
      if (all !== false) {
        cT.imageSmoothingEnabled = true;
        cT.imageSmoothingQuality = 'high';
        cT.drawImage(toCanvas(target, TW, TH, cacheT), 0, 0, cvT.width, cvT.height);
      }
      paintOne(cA, A, cacheA);
      paintOne(cB, B, cacheB);
    }
    function record() {
      hist.push({ step: A.step, a: A.psnr(), b: B.psnr() });
    }
    function tick(now) {
      raf = 0;
      if (!running || !visible) return;
      var t0 = performance.now(), n = 0;
      while (performance.now() - t0 < BUDGET_MS && A.step < MAX) {
        A.stepOnce(); B.stepOnce(); n++;
        if (A.step % 10 === 0) record();
        if (A.step % A.every === 0 && A.step <= A.stopGrowAt && A.lastEvent) {
          var ev = A.lastEvent;
          log.textContent = '第 ' + A.step + ' 步（开启增删）：克隆 ' + ev.clones + ' 个，分裂 ' + ev.splits + ' 个，剪掉 ' + ev.pruned + ' 个，现有 ' + ev.n + ' 个。';
        }
      }
      if (n) stepMs = (performance.now() - t0) / n;
      paint(false);
      stats();
      if (now - lastChart > 250 || A.step >= MAX) { chart.set(hist); lastChart = now; }
      if (A.step >= MAX) {
        running = false;
        runBtn.textContent = '再训练一次';
        log.textContent = '训练完成（' + MAX + ' 步）。开启增删：' + A.model.n + ' 个高斯，' + fmt(A.psnr(), 1) + ' dB；关闭增删：' + B.model.n + ' 个，' + fmt(B.psnr(), 1) + ' dB。';
        return;
      }
      if (A.step > A.stopGrowAt && A.step % 50 < 10) {
        log.textContent = '第 ' + A.step + ' 步：增删已停止，只做参数微调。两个模型每步合计约 ' + fmt(stepMs, 1) + ' ms。';
      }
      raf = requestAnimationFrame(tick);
    }
    function play(byUser) {
      if (A.step >= MAX) reset();
      if (byUser) visible = true;   // they are looking at it; don't wait for the observer
      running = true; started = true;
      runBtn.textContent = '暂停';
      if (!raf) raf = requestAnimationFrame(tick);
    }
    function pause() { running = false; runBtn.textContent = '继续训练'; }
    runBtn.addEventListener('click', function () { if (running) pause(); else play(true); });
    $('fit-reset').addEventListener('click', function () { reset(); if (running && !raf) raf = requestAnimationFrame(tick); });
    $('fit-budget').addEventListener('input', function () { $('fit-budget-o').textContent = this.value; });
    $('fit-budget').addEventListener('change', function () { reset(); if (running && !raf) raf = requestAnimationFrame(tick); });
    root.querySelectorAll('[data-target]').forEach(function (b) {
      b.addEventListener('click', function () {
        targetName = b.getAttribute('data-target');
        root.querySelectorAll('[data-target]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        reset();
        if (running && !raf) raf = requestAnimationFrame(tick);
      });
    });
    root.querySelectorAll('[data-view]').forEach(function (b) {
      b.addEventListener('click', function () {
        view = b.getAttribute('data-view');
        root.querySelectorAll('[data-view]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        paint(false);
      });
    });
    $('fit-file').addEventListener('change', function () {
      var file = this.files && this.files[0];
      if (!file) return;
      var url = URL.createObjectURL(file), im = new Image();
      im.onload = function () {
        var c = document.createElement('canvas');
        c.width = TW; c.height = TH;
        var x = c.getContext('2d');
        var s = Math.max(TW / im.width, TH / im.height);
        x.imageSmoothingQuality = 'high';
        x.drawImage(im, (TW - im.width * s) / 2, (TH - im.height * s) / 2, im.width * s, im.height * s);
        upload = readCanvas(c);
        URL.revokeObjectURL(url);
        targetName = 'upload';
        root.querySelectorAll('[data-target]').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        reset();
        play(true);
      };
      im.onerror = function () { log.textContent = '这张图片读不出来，换一张 JPG 或 PNG 试试。'; URL.revokeObjectURL(url); };
      im.src = url;
    });
    document.addEventListener('themechange', function () { paint(); });
    window.addEventListener('resize', function () { paint(); chart.set(hist); });
    reset();
    onVisible(root, function (v) {
      visible = v;
      if (v && !started && !reduceMotion) play();
      else if (v && running && !raf) raf = requestAnimationFrame(tick);
    });
  })();

  /* ------------------------------------------------------ PSNR line chart */
  function Chart(host, tip, table, details, maxStep) {
    var NS = 'http://www.w3.org/2000/svg';
    var data = [];
    var series = [
      { key: 'a', name: '开启增删', color: 'var(--series-1)' },
      { key: 'b', name: '关闭增删', color: 'var(--series-2)' }
    ];
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'PSNR 随训练步数变化的折线图');
    host.appendChild(svg);
    var geo = null;

    function el(name, attrs, parent) {
      var e = document.createElementNS(NS, name);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      (parent || svg).appendChild(e);
      return e;
    }
    function draw() {
      var W = host.clientWidth || 600, H = 240;
      var narrow = W < 520;
      var m = { l: 38, r: narrow ? 84 : 124, t: 12, b: 30 };
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      var vals = [];
      data.forEach(function (d) { if (d.a != null) vals.push(d.a, d.b); });
      var lo = 10, hi = 40;
      if (vals.length) {
        lo = Math.floor((Math.min.apply(null, vals) - 1) / 5) * 5;
        hi = Math.ceil((Math.max.apply(null, vals) + 1) / 5) * 5;
        if (hi - lo < 10) hi = lo + 10;
      }
      var x = function (s) { return m.l + (W - m.l - m.r) * s / maxStep; };
      var y = function (v) { return m.t + (H - m.t - m.b) * (1 - (v - lo) / (hi - lo)); };
      geo = { x: x, y: y, m: m, W: W, H: H };
      for (var v = lo; v <= hi; v += 5) {
        el('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), 'class': v === lo ? 'axis' : 'grid' });
        el('text', { x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end' }).textContent = v;
      }
      for (var s = 0; s <= maxStep; s += 500) {
        el('text', { x: x(s), y: H - 10, 'text-anchor': s === 0 ? 'start' : 'middle' }).textContent = s === maxStep ? s + ' 步' : s;
      }
      var ends = [];
      series.forEach(function (se) {
        var pts = data.filter(function (d) { return d[se.key] != null; });
        if (!pts.length) return;
        el('polyline', {
          points: pts.map(function (d) { return fmt(x(d.step), 1) + ',' + fmt(y(d[se.key]), 1); }).join(' '),
          fill: 'none', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', style: 'stroke:' + se.color
        });
        var last = pts[pts.length - 1];
        ends.push({ se: se, x: x(last.step), y: y(last[se.key]), v: last[se.key] });
      });
      // End labels sit just right of each line's last point. When two labels
      // would overlap they are pulled apart and tied back with short leaders.
      ends.sort(function (a, b) { return a.y - b.y; });
      var ly = ends.map(function (e) { return e.y; });
      if (ends.length === 2 && ly[1] - ly[0] < 30) {
        var mid = (ly[0] + ly[1]) / 2;
        ly = [mid - 15, mid + 15];
      }
      ends.forEach(function (e, i) {
        var lx = e.x + 12;
        if (Math.abs(ly[i] - e.y) > 1) el('line', { x1: e.x + 5, y1: e.y, x2: lx - 2, y2: ly[i] - 4, 'class': 'leader' });
        el('circle', { cx: e.x, cy: e.y, r: 4.5, 'class': 'ring', style: 'fill:' + e.se.color });
        var t = el('text', { x: lx, y: ly[i] - 1, 'class': 'lbl' });
        t.textContent = e.se.name;
        el('text', { x: lx, y: ly[i] + 13 }).textContent = fmt(e.v, 1) + ' dB';
      });
      // hover layer
      var cross = el('line', { y1: m.t, y2: H - m.b, 'class': 'cross', visibility: 'hidden' });
      var dots = series.map(function (se) { return el('circle', { r: 4, 'class': 'ring', style: 'fill:' + se.color, visibility: 'hidden' }); });
      var hit = el('rect', { x: m.l, y: m.t, width: Math.max(0, W - m.l - m.r), height: H - m.t - m.b, fill: 'transparent' });
      function move(ev) {
        if (data.length < 2) return;
        var r = svg.getBoundingClientRect();
        var sx = (ev.clientX - r.left) * W / r.width;
        var step = (sx - m.l) / (W - m.l - m.r) * maxStep;
        var best = data[1], bd = Infinity;
        for (var i = 1; i < data.length; i++) { var dd = Math.abs(data[i].step - step); if (dd < bd) { bd = dd; best = data[i]; } }
        cross.setAttribute('x1', x(best.step)); cross.setAttribute('x2', x(best.step));
        cross.setAttribute('visibility', 'visible');
        series.forEach(function (se, k) {
          dots[k].setAttribute('cx', x(best.step)); dots[k].setAttribute('cy', y(best[se.key]));
          dots[k].setAttribute('visibility', 'visible');
        });
        tip.hidden = false;
        tip.innerHTML = '第 ' + best.step + ' 步<br>' + series.map(function (se) {
          return '<i style="background:' + se.color + '"></i>' + se.name + ' ' + fmt(best[se.key], 2) + ' dB';
        }).join('<br>');
        var box = host.parentNode.getBoundingClientRect();
        tip.style.left = (r.left - box.left + x(best.step) * r.width / W) + 'px';
        tip.style.top = (r.top - box.top + Math.min(y(best.a), y(best.b)) * r.height / H) + 'px';
      }
      function leave() {
        cross.setAttribute('visibility', 'hidden');
        dots.forEach(function (d) { d.setAttribute('visibility', 'hidden'); });
        tip.hidden = true;
      }
      hit.addEventListener('pointermove', move);
      hit.addEventListener('pointerdown', move);
      hit.addEventListener('pointerleave', leave);
    }
    function fillTable() {
      var rows = data.filter(function (d) { return d.a != null && d.step % 100 === 0; });
      table.innerHTML = '<thead><tr><th class="num">步数</th><th class="num">开启增删（dB）</th><th class="num">关闭增删（dB）</th></tr></thead><tbody>' +
        (rows.length ? rows.map(function (d) {
          return '<tr><td class="num">' + d.step + '</td><td class="num">' + fmt(d.a, 2) + '</td><td class="num">' + fmt(d.b, 2) + '</td></tr>';
        }).join('') : '<tr><td colspan="3">还没有数据，先开始训练。</td></tr>') + '</tbody>';
    }
    details.addEventListener('toggle', function () { if (details.open) fillTable(); });
    return {
      set: function (d) {
        data = d;
        draw();
        if (details.open) fillTable();
      }
    };
  }

  /* --------------------------------------------------- catalogue filter */
  (function catalogue() {
    var q = $('q'), star = $('only-star'), count = $('count'), empty = $('empty');
    if (!q) return;
    var cards = [].slice.call(document.querySelectorAll('#modules .card'));
    var lists = [].slice.call(document.querySelectorAll('#modules .cards'));
    var folds = [].slice.call(document.querySelectorAll('#modules details.more'));
    var subsecs = [].slice.call(document.querySelectorAll('#modules .subsec'));
    var mods = [].slice.call(document.querySelectorAll('#modules .module'));
    var chips = [].slice.call(document.querySelectorAll('.dir-chips button'));
    var mod = 'all';
    cards.forEach(function (c) { c._t = c.getAttribute('data-search') || ''; });
    // Remember how the reader left each fold, so clearing a search restores it.
    folds.forEach(function (d) {
      d._user = d.open;
      d.addEventListener('toggle', function () { if (!d._auto) d._user = d.open; d._auto = false; });
    });
    function setOpen(d, open) {
      if (d.open === open) return;
      d._auto = true;
      d.open = open;
    }
    function apply() {
      var terms = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      var searching = terms.length > 0 || star.checked;
      var shown = 0;
      cards.forEach(function (c) {
        var ok = (mod === 'all' || c.getAttribute('data-mod') === mod) &&
          (!star.checked || c.getAttribute('data-star') === '1') &&
          terms.every(function (t) { return c._t.indexOf(t) >= 0; });
        c.hidden = !ok;
        if (ok) shown++;
      });
      lists.forEach(function (l) {
        var any = !!l.querySelector('.card:not([hidden])');
        l.hidden = !any;
        var prev = l.previousElementSibling;
        if (prev && prev.classList.contains('group-title')) prev.hidden = !any;
      });
      folds.forEach(function (d) {
        var any = !!d.querySelector('.card:not([hidden])');
        d.hidden = !any;
        setOpen(d, searching ? any : d._user);
      });
      subsecs.forEach(function (s) { s.hidden = !s.querySelector('.card:not([hidden])'); });
      mods.forEach(function (m) { m.hidden = !m.querySelector('.card:not([hidden])'); });
      count.textContent = '显示 ' + shown + ' / ' + cards.length + ' 篇';
      empty.hidden = shown > 0;
    }
    function reset() {
      q.value = ''; star.checked = false; mod = 'all';
      chips.forEach(function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-mod') === 'all')); });
      apply();
    }
    // Make an in-page target visible before the browser scrolls to it.
    function reveal(el) {
      if (!el) return;
      if (el.closest('#modules') && (el.hidden || el.closest('[hidden]'))) reset();
      var d = el.closest('details');
      if (d && !d.open) { d.open = true; d._user = true; }
    }
    q.addEventListener('input', apply);
    star.addEventListener('change', apply);
    chips.forEach(function (b) {
      b.addEventListener('click', function () {
        mod = b.getAttribute('data-mod');
        chips.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        apply();
      });
    });
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a || a.getAttribute('href').length < 2) return;
      reveal(document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1))));
    });
    function fromHash() {
      var id = decodeURIComponent(location.hash.slice(1));
      var el = id && document.getElementById(id);
      if (el && el.closest('details') && !el.closest('details').open) {
        reveal(el);
        el.scrollIntoView();
      }
    }
    window.addEventListener('hashchange', fromHash);
    apply();
    fromHash();
  })();

  /* ------------------------------------------------ back to the overview */
  (function toTop() {
    var btn = $('to-top'), hub = $('overview');
    if (!btn || !hub) return;
    function set(show) { btn.hidden = !show; }
    if (typeof window.IntersectionObserver === 'function') {
      new IntersectionObserver(function (es) { set(!es[0].isIntersecting); }, { rootMargin: '0px 0px -30% 0px' }).observe(hub);
    } else {
      window.addEventListener('scroll', function () { set(hub.getBoundingClientRect().bottom < 0); }, { passive: true });
    }
  })();

  /* ------------------------------------------------- current section in nav */
  (function navSpy() {
    if (typeof window.IntersectionObserver !== 'function') return;
    var links = {};
    [].forEach.call(document.querySelectorAll('.toc a'), function (a) { links[a.getAttribute('href').slice(1)] = a; });
    var current = null;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var id = e.target.id;
        if (!links[id] || current === id) return;
        if (current && links[current]) links[current].removeAttribute('aria-current');
        links[id].setAttribute('aria-current', 'true');
        current = id;
        var nav = links[id].parentNode, a = links[id];
        if (a.offsetLeft < nav.scrollLeft || a.offsetLeft + a.offsetWidth > nav.scrollLeft + nav.clientWidth) {
          nav.scrollTo({ left: a.offsetLeft - 16, behavior: reduceMotion ? 'auto' : 'smooth' });
        }
      });
    }, { rootMargin: '-40% 0px -55% 0px' });
    Object.keys(links).forEach(function (id) { var s = $(id); if (s) io.observe(s); });
  })();
})();
