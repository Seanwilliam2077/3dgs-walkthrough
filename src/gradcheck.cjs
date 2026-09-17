// Check the analytic backward pass of splat2d.js against central differences.
// Usage: node src/gradcheck.cjs
'use strict';
const S = require('./splat2d.js');

const W = 24, H = 18;
const rand = S.rng(3);
const bg = [0.2, 0.3, 0.4];

// A random target and a handful of overlapping Gaussians, some of them nearly opaque
// so that early termination and the 0.99 clamp are exercised too.
const target = new Float64Array(W * H * 3).map(() => rand());
const model = new S.Model(16);
for (let i = 0; i < 12; i++) {
  model.add(rand() * W, rand() * H, 1.5 + rand() * 4, 1 + rand() * 3, rand() * Math.PI,
    rand(), rand(), rand(), i % 4 === 0 ? 0.97 : 0.2 + 0.6 * rand());
}

const f = new S.Frame(W, H, Float64Array);
const opts = { exact: true };
function lossAt() {
  S.render(model, f, bg, opts);
  return S.loss(f, target);
}

lossAt();
model.g.fill(0);
S.backward(model, f, bg, opts);
const analytic = Float64Array.from(model.g.subarray(0, model.n * S.P));

const names = ['mx', 'my', 'log sx', 'log sy', 'theta', 'r', 'g', 'b', 'opacity'];
const eps = 1e-6;
const gmax = analytic.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
let worst = 0, worstAt = '', checked = 0, worstAbs = 0;
for (let i = 0; i < model.n * S.P; i++) {
  const keep = model.p[i];
  model.p[i] = keep + eps; const lp = lossAt();
  model.p[i] = keep - eps; const lm = lossAt();
  model.p[i] = keep;
  const numeric = (lp - lm) / (2 * eps);
  const a = analytic[i];
  worstAbs = Math.max(worstAbs, Math.abs(a - numeric));
  // per-component relative error only means something where the gradient is not ~0
  if (Math.max(Math.abs(a), Math.abs(numeric)) < 1e-2 * gmax) continue;
  const rel = Math.abs(a - numeric) / Math.max(Math.abs(a), Math.abs(numeric));
  checked++;
  if (rel > worst) { worst = rel; worstAt = `gaussian ${Math.floor(i / S.P)} ${names[i % S.P]}`; }
}
const normalized = worstAbs / gmax;
console.log(`${model.n * S.P} partial derivatives, largest |gradient| ${gmax.toExponential(2)}`);
console.log(`max |analytic - numeric| / max |gradient| = ${normalized.toExponential(2)}`);
console.log(`max relative error on the ${checked} partials above 1% of the largest: ${worst.toExponential(2)} (${worstAt})`);
if (normalized > 1e-6 || worst > 1e-4) { console.error('FAIL: analytic gradient disagrees with finite differences'); process.exit(1); }
console.log('PASS');
