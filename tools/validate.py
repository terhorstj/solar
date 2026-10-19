"""Check the built data against Horizons at random times that were never stored or used in the build.

Loads bodies.js, moons.js, and probes.js, evaluates each object with the same math the page
uses (orbit.py), and compares with fresh Horizons vectors at random TDB times:

  planets, dwarf planets, small bodies   200 random times, heliocentric
  moons                                   200 random times, relative to the planet
  spacecraft                              200 random times over the span, 60 inside each window
                                          near a body, and 10 around each of up to 25 close passes

Error is measured relative to the body the object is near (the Sun, its planet, or the body
whose zone a probe is inside), which is what the page shows. Tolerance is the build tolerance
times the distance from that body (never below build.FLOOR_KM).

Run:  python3 tools/validate.py      (writes tools/accuracy-report.txt; exit code 1 if anything fails)
"""
import json
import os
import random
import re

import build
import horizons
import orbit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUN = orbit.Ephem.SUN


def load_js_array(path, var):
    text = open(path).read()
    body = text.split("window.SOLAR_DATA.%s = " % var, 1)[1]
    body = body.split("\n];", 1)[0] + "\n]"
    body = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*):", r'\1"\2":', body)
    body = re.sub(r",\s*([\]}])", r"\1", body)
    return json.loads(body)


def sun_gm(path):
    m = re.search(r"window\.SOLAR_DATA_SUN = \{gm:([0-9.eE+-]+)", open(path).read())
    return float(m.group(1))


def to_ephem(objs, eph):
    for o in objs:
        s = o["s"]
        rs = [(s[6 * k], s[6 * k + 1], s[6 * k + 2]) for k in range(len(o["t"]))]
        vs = [(s[6 * k + 3], s[6 * k + 4], s[6 * k + 5]) for k in range(len(o["t"]))]
        cs = [o["centers"][c] for c in o["c"]]
        eph.add(o["id"], o["gm"], o["t"], cs, rs, vs)


def load_all():
    eph = orbit.Ephem()
    eph.set_sun_gm(sun_gm(os.path.join(ROOT, "bodies.js")))
    groups = {}
    for fn, var in (("bodies.js", "bodies"), ("moons.js", "moons"), ("probes.js", "probes"), ("probes-rebuilt.js", "rebuilt")):
        p = os.path.join(ROOT, fn)
        groups[var] = load_js_array(p, var) if os.path.exists(p) else []
        to_ephem(groups[var], eph)
    return eph, groups


def main():
    random.seed(20261018)
    eph, g = load_all()
    meta = json.load(open(os.path.join(ROOT, "tools", "build-meta.json")))
    zone = meta["zones"]
    body_cmd = {}
    for cmd, did, *_ in build.catalog.DWARFS + build.catalog.SMALL:
        body_cmd[did] = cmd
    for pid, *_ in build.catalog.PLANETS:
        body_cmd[pid] = pid
    floor = build.FLOOR_KM / orbit.AU_KM
    names_all = {o["id"]: o["name"] for grp in g.values() for o in grp}
    out = ["Accuracy report: built data vs fresh Horizons samples at random times never used in the build.",
           "err = position error relative to the body the object is near (the Sun, its planet, or the body whose zone a",
           "probe is inside), which is what the page shows. tol = build tolerance x distance from that body.", ""]
    all_ok = True

    def truth_rel(oid, center, times):
        """Horizons vectors of oid relative to center at the given times."""
        oid = body_cmd.get(oid, oid)   # small bodies are fetched with the same command the build used ("433;" etc.)
        if center == SUN:
            return {round(t, 6): r for (t, r, v) in horizons.vectors_at(oid, "500@10", times)}
        code = build.CENTER_CODE.get(center, "500@" + center)
        if code:
            try:
                return {round(t, 6): r for (t, r, v) in horizons.vectors_at(oid, code, times)}
            except RuntimeError:
                pass   # outside the center body's own coverage: subtract heliocentric positions instead
        a = {round(t, 6): r for (t, r, v) in horizons.vectors_at(oid, "500@10", times)}
        b = {round(t, 6): r for (t, r, v) in horizons.vectors_at(body_cmd[center], "500@10", times)}
        return {k: build.vsub(a[k], b[k]) for k in a if k in b}

    def check(o, rel, times, label, fixed_center=None):
        nonlocal all_ok
        oid = o["id"]
        seams = meta["objects"].get(oid, {}).get("seams", [])
        in_seam = [t for t in times if any(a <= t <= b for a, b in seams)]
        times = [t for t in times if eph.pos(oid, t) is not None and t not in in_seam]
        if not times:
            return
        # the body each sample is near, judged from the stored tracks
        near = {}
        for t in times:
            if fixed_center:
                near[t] = fixed_center
                continue
            m = eph.pos(oid, t)
            best, bd = SUN, None
            for b, zr in zone.items():
                bp = eph.pos(b, t)
                if bp is None or b == oid:
                    continue
                d = build.vnorm(build.vsub(m, bp))
                if d < zr and (bd is None or d / zr < bd):
                    best, bd = b, d / zr
            near[t] = best
        # confirm each sample's body with Horizons' own distance, as the build does: a sample the stored tracks
        # put just inside a zone but that truly lies just outside is judged relative to the Sun
        if not fixed_center:
            for c in set(near.values()) - {SUN}:
                sub = sorted(t for t in times if near[t] == c)
                tr = truth_rel(oid, c, sub)
                for t in sub:
                    rt = tr.get(round(t, 6))
                    if rt is not None and build.vnorm(rt) >= zone[c]:
                        near[t] = SUN
        worst, worst_ratio, fails, n, worst_at = 0.0, 0.0, 0, 0, ""
        for c in set(near.values()):
            sub = sorted(t for t in times if near[t] == c)
            tr = truth_rel(oid, c, sub)
            for t in sub:
                rt = tr.get(round(t, 6))
                if rt is None:
                    continue
                m = eph.pos(oid, t)
                mr = m if c == SUN else build.vsub(m, eph.pos(c, t))
                err = build.vnorm(build.vsub(mr, rt))
                rr = rel(c) if callable(rel) else rel
                tol = max(rr * build.vnorm(rt), floor)
                worst = max(worst, err)
                if err / tol > worst_ratio:
                    worst_ratio, worst_at = err / tol, "%s vs %s" % (build.jd_to_iso(t), names_all.get(c, "Sun"))
                fails += err > tol
                n += 1
        all_ok = all_ok and fails == 0
        out.append("%-26s %-30s n=%4d  max err %11.1f km  err/tol %.3f  over: %d%s%s" % (
            o["name"], label, n, worst * orbit.AU_KM, worst_ratio, fails, ("   worst at " + worst_at) if fails else "",
            ("   (%d skipped: inside a jump in Horizons' own track; see build-report.txt)" % len(in_seam)) if in_seam else ""))
        print(out[-1])

    for o in g["bodies"]:
        rel = meta["objects"][o["id"]]["rel"]
        check(o, rel, sorted(random.uniform(o["t"][0], o["t"][-1]) for _ in range(200)), "random over span", SUN)
    for o in g["moons"]:
        check(o, meta["objects"][o["id"]]["rel"], sorted(random.uniform(o["t"][0], o["t"][-1]) for _ in range(200)),
              "random, vs planet", o["parent"])
    names = {o["id"]: o["name"] for o in g["bodies"]}
    for o in g["probes"]:
        mo = meta["objects"][o["id"]]
        t0, t1 = o["t"][0], o["t"][-1]
        rel = build.probe_rel
        check(o, rel, sorted(random.uniform(t0, t1) for _ in range(200)), "random over span")
        for b, w0, w1 in mo["windows"]:
            w0, w1 = max(w0, t0), min(w1, t1)
            if w1 > w0:
                check(o, rel, sorted(random.uniform(w0, w1) for _ in range(60)), "near " + names.get(b, b))
        minima = [m for m in mo["minima"] if t0 <= m[1] <= t1]
        if minima:
            pick = random.sample(minima, min(25, len(minima)))
            ts = sorted(random.uniform(max(tm - 0.5, t0), min(tm + 0.5, t1)) for _, tm in pick for _ in range(10))
            check(o, rel, ts, "close passes (%d of %d)" % (len(pick), len(minima)))

    out.append("")
    out.append("Spot checks (heliocentric distance):")
    built_jd = build.cal_to_jd(meta["built"])
    for pid, jd, label, expect in (("399", 2446066.5, "1985-01-01", "about 1 AU"),
                                   ("599", 2446066.5, "1985-01-01", "about 5.2 AU (4.95 to 5.46 over its orbit)"),
                                   ("-31", built_jd, meta["built"], "compare with NASA's published figure")):
        p = eph.pos(pid, jd)
        nm = names.get(pid) or [o["name"] for o in g["probes"] if o["id"] == pid][0]
        if p:
            d = build.vnorm(p)
            out.append("  %-10s %s  %.4f AU = %.3f billion km  (expected %s)" % (nm, label, d, d * orbit.AU_KM / 1e9, expect))
    out.append("")
    out.append("RESULT: " + ("all points within tolerance" if all_ok else "SOME POINTS OVER TOLERANCE"))
    with open(os.path.join(ROOT, "tools", "accuracy-report.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out[-6:]))
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
