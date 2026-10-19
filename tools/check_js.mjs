// Compare the page's evaluator (the EPHEM block in index.html) with tools/orbit.py at random times.
// The Python side is what validate.py checked against Horizons, so agreement here means the page
// shows the validated positions.   Run:  node tools/check_js.mjs
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const html = readFileSync(path.join(ROOT, "index.html"), "utf8");
const ephem = html.split("// EPHEM-BEGIN")[1].split("// EPHEM-END")[0];

const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(readFileSync(path.join(ROOT, "bodies.js"), "utf8"), ctx);
vm.runInContext(readFileSync(path.join(ROOT, "moons.js"), "utf8"), ctx);
vm.runInContext(readFileSync(path.join(ROOT, "probes.js"), "utf8"), ctx);
vm.runInContext(readFileSync(path.join(ROOT, "probes-rebuilt.js"), "utf8"), ctx);
vm.runInContext("const SUNMETA = window.SOLAR_DATA_SUN;\n" + ephem +
  "\nfor (const o of window.SOLAR_DATA.bodies.concat(window.SOLAR_DATA.moons, window.SOLAR_DATA.probes, window.SOLAR_DATA.rebuilt)) ephAdd(o);\nthis.ephPos = ephPos;", ctx);

const objs = ctx.window.SOLAR_DATA.bodies.concat(ctx.window.SOLAR_DATA.moons, ctx.window.SOLAR_DATA.probes, ctx.window.SOLAR_DATA.rebuilt);
let seed = 12345;
const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const samples = [];
for (const o of objs) {
  const t0 = o.t[0], t1 = o.t[o.t.length - 1];
  for (let k = 0; k < 150; k++) samples.push([o.id, t0 + (t1 - t0) * rnd()]);
  for (const t of o.t) samples.push([o.id, t]);                       // exactly on stored states
  for (let k = 0; k + 1 < o.t.length; k++) samples.push([o.id, (o.t[k] + o.t[k + 1]) / 2]);   // segment midpoints
}

const py = `
import json, os, sys
sys.path.insert(0, os.path.join(${JSON.stringify(ROOT)}, "tools"))
import validate
eph, _ = validate.load_all()
print(json.dumps([eph.pos(i, t) for i, t in json.load(sys.stdin)]))
`;
const ref = JSON.parse(execFileSync("python3", ["-c", py], { input: JSON.stringify(samples), maxBuffer: 1 << 28 }));

let worst = 0, worstAt = null, missing = 0;
samples.forEach(([id, t], k) => {
  const p = [0, 0, 0];
  const ok = ctx.ephPos(id, t, p);
  if (!ok || !ref[k]) { if (ok !== !!ref[k]) missing++; return; }
  const d = Math.hypot(p[0] - ref[k][0], p[1] - ref[k][1], p[2] - ref[k][2]);
  if (d > worst) { worst = d; worstAt = [id, t]; }
});
const km = worst * 149597870.7;
console.log(`${samples.length} samples. Max JS vs Python difference: ${worst.toExponential(2)} AU (${km.toFixed(6)} km) at ${worstAt}. Span mismatches: ${missing}.`);
process.exit(km < 0.001 && missing === 0 ? 0 : 1);
