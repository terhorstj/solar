"""Build the page's data files (bodies.js, moons.js, probes.js) from JPL Horizons.

For each object: fetch a reference grid of Horizons state vectors, then keep only as many
states as the evaluator in orbit.py needs to reproduce every reference point within half
its tolerance. Accuracy against samples never used here is checked by validate.py.

  planets, dwarf planets, small bodies   heliocentric, daily reference
  moons                                   relative to their planet, reference every 1/8 orbit
  spacecraft                              heliocentric daily in cruise; near any planet or small
                                          body, relative to it (hourly or finer, 5 minutes near close passes)

Run:  python3 tools/build.py        (first run downloads a lot; later runs use the cache)
"""
import datetime
import hashlib
import json
import math
import os
import re
import sys

import catalog
import horizons
import orbit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUN = orbit.Ephem.SUN

# tolerance = fraction of distance from the body an object is near (the Sun, or its parent / nearby body)
REL_TOL = {"planet": 1e-6, "earth": 1e-6, "dwarf": 1e-6, "small": 1e-5, "moon": 1e-2, "probe": 1e-3,
           "probe_small": 1e-2}   # craft near a dwarf planet or small body: approximate, like the moons
# Earth was once 1e-4 (its center wobbles ~4,700 km monthly around the Earth-Moon barycenter, which costs many
# states to follow), but that error leaked into craft at the edge of Earth's zone, held there to ~1,850 km.
REL_TOL_PLANET, REL_TOL_EARTH, REL_TOL_PROBE = REL_TOL["planet"], REL_TOL["earth"], REL_TOL["probe"]
FIT_VERSION = "v2"   # bump to refit spacecraft (v2: bracketed Kepler solver, Earth at 1e-6)
FLOOR_KM = 0.5           # no tolerance tighter than this (probes hovering a few km from a tiny asteroid)
SAFETY = 0.5             # stored states fit the reference to half the tolerance, so samples between them still pass
REACH = 2.0              # a body-centered state is only used within this many zone radii of that body
SMALL_ZONE_AU = 0.001    # probes within 150,000 km of a dwarf planet or small body are tracked relative to it
FAST_AU_D = 86400.0 / orbit.AU_KM   # 1 km/s in AU/day: close passes faster than this get 5-minute sampling
EARTH_ZONE_MULT = 2.0    # Earth's zone is twice its sphere of influence, to cover craft at the L1 and L2 points
PLANET_IDS = {p[0] for p in catalog.PLANETS}
GAS_GIANTS = {"599", "699", "799", "899"}
# Horizons center codes where "500@<id>" doesn't work: None means subtract heliocentric positions instead
CENTER_CODE = {"2065803": "500@20065803", "67P": "500@1000012", "2162173": None}
# landings on small bodies: tracking ends once the craft settles within this many body radii
SMALL_LANDINGS = {"-93": ("2000433", 1.5), "-226": ("67P", 1.5)}
SMALL_CENTERS = {d[1] for d in catalog.DWARFS + catalog.SMALL}


def probe_rel(c):
    return REL_TOL["probe_small"] if c in SMALL_CENTERS else REL_TOL["probe"]


def cal_to_jd(s):
    for fmt in ("%Y-%b-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            d = datetime.datetime.strptime(s, fmt)
            return (d - datetime.datetime(2000, 1, 1, 12)).total_seconds() / 86400.0 + 2451545.0
        except ValueError:
            pass
    raise ValueError(s)


def jd_to_iso(jd):
    return (datetime.datetime(2000, 1, 1, 12) + datetime.timedelta(days=jd - 2451545.0)).strftime("%Y-%m-%d %H:%M")


def vnorm(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def blend_err(eph, ref, i, j, k, gm_self):
    """Error at reference point k for a segment stored as states i..j (same math as Ephem.pos)."""
    try:
        return _blend_err(eph, ref, i, j, k, gm_self)
    except (OverflowError, ValueError, ZeroDivisionError):
        return float("inf")  # a hyperbolic state propagated far too long: not a usable segment


def _blend_err(eph, ref, i, j, k, gm_self):
    t = ref["t"][k]
    ci, cj, ck = ref["c"][i], ref["c"][j], ref["c"][k]
    w = orbit.smooth((t - ref["t"][i]) / (ref["t"][j] - ref["t"][i]))
    pi = orbit.kepler(ref["r"][i], ref["v"][i], eph.gm[ci] + gm_self, t - ref["t"][i])
    pj = orbit.kepler(ref["r"][j], ref["v"][j], eph.gm[cj] + gm_self, t - ref["t"][j])
    if ci == cj == ck:
        # compare in the shared center's frame (exact Horizons truth in that frame)
        m = (pi[0] + (pj[0] - pi[0]) * w, pi[1] + (pj[1] - pi[1]) * w, pi[2] + (pj[2] - pi[2]) * w)
        return vnorm(vsub(m, ref["r"][k]))
    pi = vadd(pi, eph.center_pos(ci, t))
    pj = vadd(pj, eph.center_pos(cj, t))
    m = (pi[0] + (pj[0] - pi[0]) * w, pi[1] + (pj[1] - pi[1]) * w, pi[2] + (pj[2] - pi[2]) * w)
    if ck != SUN:
        # near a body: measure where the object sits relative to that body as the page draws it
        # (the body's own small error is shared, so it cancels)
        return vnorm(vsub(vsub(m, eph.center_pos(ck, t)), ref["r"][k]))
    return vnorm(vsub(m, ref["h"][k]))


def segment(eph, ref, rel_tol, gm_self, zone=None):
    """Greedy: from each kept state, reach as far as possible while every point between stays in tolerance."""
    n = len(ref["t"])
    floor = FLOOR_KM / orbit.AU_KM
    rel = rel_tol if callable(rel_tol) else (lambda c: rel_tol)
    tol = [SAFETY * max(rel(c) * vnorm(r), floor) for r, c in zip(ref["r"], ref["c"])]

    def dist_to(k, c):
        if ref["c"][k] == c:
            return vnorm(ref["r"][k])
        return vnorm(vsub(ref["h"][k], eph.pos(c, ref["t"][k])))

    def ok(i, j):
        for c in {ref["c"][i], ref["c"][j]}:
            if c != SUN and zone is not None:
                for k in range(i + 1, j):
                    if dist_to(k, c) > REACH * zone[c]:
                        return False
        for k in range(i + 1, j):
            if blend_err(eph, ref, i, j, k, gm_self) > tol[k]:
                return False
        return True

    keep = [0]
    i = 0
    while i < n - 1:
        lo, step = i + 1, 1
        while True:
            probe = i + step * 2
            if probe >= n - 1:
                if ok(i, n - 1):
                    lo = n - 1
                    hi = None
                else:
                    hi = n - 1
                break
            if ok(i, probe):
                lo, step = probe, step * 2
            else:
                hi = probe
                break
        if hi is not None:
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if ok(i, mid):
                    lo = mid
                else:
                    hi = mid
        keep.append(lo)
        i = lo
    return keep


def segment_cached(key, eph, ref, rel_tol, gm_self, zone=None):
    """segment(), remembered on disk by object, grid, and tolerance (the moon and orbiter fits take many minutes)."""
    d = os.path.join(horizons.CACHE, "segments")
    os.makedirs(d, exist_ok=True)
    name = key.replace(";", "").replace("=", "").replace("<", "")
    if zone is None and not callable(rel_tol):   # bodies and moons (key format kept so earlier fits still hit)
        tag = "%s_%d_%.6f_%.6f_%g_%g_%g" % (name, len(ref["t"]), ref["t"][0], ref["t"][-1], rel_tol, SAFETY, FLOOR_KM)
    else:                                        # spacecraft: the grid mixes centers, so key on its full contents
        sig = hashlib.sha1(("%s|%s|%s" % (ref["c"], [round(t, 6) for t in ref["t"]],
                                           sorted(zone.items()))).encode()).hexdigest()[:12]
        tag = "%s_%d_%s_fn_%g_%g_%s" % (name, len(ref["t"]), sig, SAFETY, FLOOR_KM, FIT_VERSION)
    path = os.path.join(d, tag + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    keep = segment(eph, ref, rel_tol, gm_self, zone)
    json.dump(keep, open(path, "w"))
    return keep


def soi_radius(eph, pid, gm_sun):
    """Laplace sphere of influence, using the body's mean distance from the Sun over the stored span."""
    o = eph.objs[pid]
    a = sum(vnorm(r) for r in o["r"]) / len(o["r"])
    return a * (max(eph.gm[pid], 0.0) / gm_sun) ** 0.4


def fmt(x):
    return "%.12g" % x


def js_val(v):
    if isinstance(v, str):
        return json.dumps(v)
    if v is None:
        return "null"
    return fmt(v)


def write_js(path, var, header, objects):
    lines = ["// " + h for h in header]
    lines.append("window.SOLAR_DATA = window.SOLAR_DATA || {};")
    lines.append("window.SOLAR_DATA.%s = [" % var)
    for o in objects:
        lines.append("{%s," % ", ".join("%s:%s" % (k, js_val(v)) for k, v in o["meta"]))
        lines.append(" centers:[%s]," % ",".join('"%s"' % c for c in o["centers"]))
        lines.append(" t:[%s]," % ",".join("%.6f" % t for t in o["t"]))
        lines.append(" c:[%s]," % ",".join(str(c) for c in o["c"]))
        lines.append(" s:[%s]}," % ",".join(fmt(x) for x in o["s"]))
    lines.append("];")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def pack(keep, ref, meta):
    centers, cidx, s = [], [], []
    for k in keep:
        c = ref["c"][k]
        if c not in centers:
            centers.append(c)
        cidx.append(centers.index(c))
        s.extend(ref["r"][k])
        s.extend(ref["v"][k])
    return {"meta": meta, "centers": centers, "t": [ref["t"][k] for k in keep], "c": cidx, "s": s}


def store(eph, oid, gm, keep, ref):
    eph.add(oid, gm, [ref["t"][k] for k in keep], [ref["c"][k] for k in keep],
            [ref["r"][k] for k in keep], [ref["v"][k] for k in keep])


def say(report, line):
    report.append(line)
    print(line)
    sys.stdout.flush()


def helio_ref(rows):
    return {"t": [r[0] for r in rows], "r": [r[1] for r in rows], "v": [r[2] for r in rows],
            "h": [r[1] for r in rows], "c": [SUN] * len(rows)}


def body_phys(cmd, sb, did):
    gm_km, rad, _ = horizons.physical(cmd)
    src = "JPL Horizons"
    if sb:
        r2, g2, ref2 = horizons.sbdb_phys(sb)
        if rad is None and r2 is not None:
            rad, src = r2, ref2
        if gm_km is None and g2 is not None:
            gm_km = g2
    if rad is None and did in catalog.RADIUS_KM:
        rad, src = catalog.RADIUS_KM[did]
    return gm_km or 0.0, rad, src


def centered(hid, b, code, center_cmd, w0, w1, step, hel=None):
    """Probe vectors relative to body b on a grid (subtracting heliocentric positions if Horizons has no center code)."""
    if code:
        try:
            return horizons.grid(hid, code, w0, w1, step)
        except RuntimeError:
            pass   # the body's own Horizons coverage doesn't span this window: go year by year below
    out, a = [], w0
    while a < w1 - 1e-9:
        z = min(a + 365.0, w1)
        rows = None
        if code:
            try:
                rows = horizons.grid(hid, code, a, z, step)
            except RuntimeError:
                rows = None
        if rows is None:   # subtract the body's heliocentric position for this stretch
            hh = horizons.grid(hid, "500@10", a, z, step)
            bh = {round(row[0], 6): row for row in horizons.grid(center_cmd[b], "500@10", a, z, step)}
            rows = [(t, vsub(r, bh[round(t, 6)][1]), vsub(v, bh[round(t, 6)][2])) for (t, r, v) in hh if round(t, 6) in bh]
        if out and rows and abs(rows[0][0] - out[-1][0]) < 1e-7:
            rows = rows[1:]
        out.extend(rows)
        a = z
    return out


def main():
    stamp = datetime.date.today().isoformat()
    built_jd = cal_to_jd(stamp)
    t_start, t_stop = cal_to_jd(catalog.START), cal_to_jd(catalog.STOP)
    gm_sun_km, r_sun, _ = horizons.physical(SUN)
    gm_sun = orbit.gm_km3s2_to_au3d2(gm_sun_km)
    eph = orbit.Ephem()
    eph.set_sun_gm(gm_sun)
    report = ["Build report, %s. Range %s to %s." % (stamp, catalog.START, catalog.STOP), ""]
    meta_out = {"built": stamp, "objects": {}, "zones": {}}
    radius = {}

    # ---- planets, dwarf planets, small bodies: heliocentric ----
    bodies_out = []
    entries = [(pid, pid, name, "planet", color, None) for pid, name, color in catalog.PLANETS] + catalog.DWARFS + catalog.SMALL
    for cmd, did, name, kind, color, sb in entries:
        gm_km, rad, rsrc = body_phys(cmd, sb, did)
        gm = orbit.gm_km3s2_to_au3d2(gm_km)
        radius[did] = rad
        rows = horizons.grid(cmd, "500@10", t_start, t_stop, 1440)
        ref = helio_ref(rows)
        tkey = "earth" if did == "399" else ("planet" if kind == "planet" else "dwarf" if kind == "dwarf" else "small")
        keep = segment_cached(did, eph, ref, REL_TOL[tkey], gm)
        store(eph, did, gm, keep, ref)
        bodies_out.append(pack(keep, ref, [("id", did), ("name", name), ("kind", kind), ("gm", gm), ("gmKm", gm_km),
                                           ("radiusKm", rad), ("radiusSrc", rsrc), ("color", color)]))
        meta_out["objects"][did] = {"name": name, "kind": kind, "rel": REL_TOL[tkey]}
        say(report, "%-26s %6d reference -> %5d states (tol %.0e x distance from Sun)" % (name, len(rows), len(keep), REL_TOL[tkey]))

    # ---- moons: relative to their planet ----
    moons_out = []
    report.append("")
    for mid, name, parent, period, color in catalog.MOONS:
        gm_km, rad, _ = horizons.physical(mid)
        gm = orbit.gm_km3s2_to_au3d2(gm_km or 0.0)
        radius[mid] = rad
        step = max(20, int(period * 1440 / 8))
        rows = horizons.grid(mid, "500@" + parent, t_start, t_stop, step)
        ref = {"t": [r[0] for r in rows], "r": [r[1] for r in rows], "v": [r[2] for r in rows],
               "h": [r[1] for r in rows], "c": [parent] * len(rows)}
        keep = segment_cached(mid, eph, ref, REL_TOL["moon"], gm)
        store(eph, mid, gm, keep, ref)
        moons_out.append(pack(keep, ref, [("id", mid), ("name", name), ("kind", "moon"), ("parent", parent), ("gm", gm),
                                          ("gmKm", gm_km or 0.0), ("radiusKm", rad), ("radiusSrc", "JPL Horizons"), ("color", color)]))
        meta_out["objects"][mid] = {"name": name, "kind": "moon", "rel": REL_TOL["moon"], "parent": parent}
        say(report, "%-26s %6d reference -> %5d states (tol %.0e x distance from planet)" % (name, len(rows), len(keep), REL_TOL["moon"]))

    # ---- zones: where a probe is tracked relative to a body instead of the Sun ----
    zone, center_cmd = {}, {}
    for pid, name, color in catalog.PLANETS:
        zone[pid] = soi_radius(eph, pid, gm_sun) * (EARTH_ZONE_MULT if pid == "399" else 1.0)
        center_cmd[pid] = pid
    for cmd, did, name, kind, color, sb in catalog.DWARFS + catalog.SMALL:
        zone[did] = max(soi_radius(eph, did, gm_sun), SMALL_ZONE_AU)
        center_cmd[did] = cmd
    meta_out["zones"] = zone
    names = {did: name for cmd, did, name, kind, color, sb in entries}

    # ---- spacecraft ----
    probes_out = []
    report.append("")
    for hid, name, kind, note in catalog.PROBES:
        print("  working on %s ..." % name)
        sys.stdout.flush()
        cov0, cov1 = horizons.coverage(hid)
        p0 = cal_to_jd(cov0) + 1.0 / 1440 if cov0 else t_start
        p1 = cal_to_jd(cov1) - 1.0 / 1440 if cov1 else t_stop
        try:
            daily = horizons.grid(hid, "500@10", p0, p1, 1440)
        except RuntimeError as err:
            # some spacecraft report their data end only through this error ("... at the ephemeris epoch 2025 JUL 14")
            m = re.search(r"ephemeris epoch (\d{4} [A-Z]{3} \d{2} \d{2}:\d{2})", str(err))
            if not m:
                raise
            p1 = cal_to_jd(datetime.datetime.strptime(m.group(1), "%Y %b %d %H:%M").strftime("%Y-%m-%d %H:%M")) - 1.0
            daily = horizons.grid(hid, "500@10", p0, p1, 1440)
        if daily[-1][0] < p1 - 1e-6:
            daily += horizons.vectors_at(hid, "500@10", [p1])
        # windows near each body, from the daily track (with a margin for one day's relative motion)
        windows = []
        for b in zone:
            near, prev = [], None
            for (t, r, v) in daily:
                bp = eph.pos(b, t)
                if bp is None:
                    prev = None
                    continue
                d = vnorm(vsub(r, bp))
                margin = vnorm(vsub(vsub(r, prev[0]), vsub(bp, prev[1]))) * 1.2 if prev is not None else 0.0
                if d < zone[b] + margin:
                    near.append(t)
                prev = (r, bp)
            groups = []
            for t in near:
                if groups and t - groups[-1][1] <= 1.01:
                    groups[-1][1] = t
                else:
                    groups.append([t, t])
            for a, z in groups:
                windows.append((b, max(a - 1.5, p0), min(z + 1.5, p1)))
        ref_rows = {round(t, 6): (r, v, SUN, r, v) for (t, r, v) in daily}
        meta_windows, meta_minima = [], []
        for b, w0, w1 in windows:
            gmb = eph.gm[b]
            dists = sorted(vnorm(vsub(r, eph.pos(b, t))) for (t, r, v) in daily if w0 <= t <= w1) or [zone[b]]
            dmed = dists[len(dists) // 2]
            step = 60
            if gmb > 0:   # resolve orbits around the body: about 12 points per orbit, between 5 and 60 minutes
                period_min = 2 * math.pi * math.sqrt(dmed ** 3 / gmb) * 1440
                step = int(min(60, max(5, period_min / 12)))
            code = CENTER_CODE.get(b, "500@" + b)
            hel = horizons.grid(hid, "500@10", w0, w1, step)
            cen = centered(hid, b, code, center_cmd, w0, w1, step, hel)
            cmap = {round(row[0], 6): row for row in cen}
            for k in [k for k in ref_rows if w0 <= k <= w1 and ref_rows[k][2] == SUN]:
                del ref_rows[k]
            for (t, r, v) in hel:
                key = round(t, 6)
                c = cmap.get(key)
                if c is None:
                    continue
                old = ref_rows.get(key)
                if vnorm(c[1]) < zone[b]:
                    if old is None or old[2] == SUN or vnorm(c[1]) / zone[b] < vnorm(old[3]) / zone[old[2]]:
                        ref_rows[key] = (r, v, b, c[1], c[2])
                elif old is None:
                    ref_rows[key] = (r, v, SUN, r, v)
            # close passes: local minima of distance; refine to 5 minutes for half a day each side
            rb = radius.get(b) or 1.0
            thresh = 30 * rb / orbit.AU_KM if b in PLANET_IDS else zone[b]
            ds = [vnorm(row[1]) for row in cen]
            for k in range(1, len(cen) - 1):
                # only fast passes (flybys, an orbiter's periapsis) need refining; a craft creeping around or
                # sitting on a small body moves slowly, and its hourly track is already fine
                spd = vnorm(cen[k][2])
                # slower close passes also count near a body with no known gravity (Hera at Didymos): there the
                # window's step can't be sized to an orbit, so it stays hourly
                fast = spd > FAST_AU_D or (gmb <= 0 and spd > 0.2 * FAST_AU_D and ds[k] < 2000.0 / orbit.AU_KM)
                if ds[k] <= ds[k - 1] and ds[k] <= ds[k + 1] and ds[k] < thresh and fast:
                    tca = cen[k][0]
                    meta_minima.append((b, tca))
                    if step <= 10:
                        continue
                    f0, f1 = max(tca - 0.5, w0), min(tca + 0.5, w1)
                    for (t, r, v) in centered(hid, b, code, center_cmd, f0, f1, 5):
                        if vnorm(r) < zone[b]:
                            ref_rows[round(t, 6)] = (None, None, b, r, v)
            meta_windows.append((b, w0, w1))
        ts = sorted(ref_rows)
        # refined points carry no heliocentric truth; derive it from the body's stored track
        # (only used where a segment mixes centers, at most a few points per pass)
        for t in ts:
            r, v, c, rc, vc = ref_rows[t]
            if r is None:
                ref_rows[t] = (vadd(rc, eph.pos(c, t)), None, c, rc, vc)
        # where tracking ends: settling inside a planet's radius (entry, impact, or landing) or onto a small body.
        # "Settling" = every point of the next two days (or to the end of the data) stays inside, so brief low
        # passes (MESSENGER's last months) and launch pads (the first point can sit at Earth's surface) don't count.
        def settled(k, b, lim):
            tk = ts[k]
            n = 0
            for t in ts[k:]:
                if t > tk + 2.0:
                    break
                r_, v_, c_, rc_, vc_ = ref_rows[t]
                if c_ != b or vnorm(rc_) >= lim:
                    return False
                n += 1
            return n >= 2 or ts[k] == ts[-1]
        end_note, cut = None, None
        # planets: the first moment inside the mean radius, after launch day. Horizons keeps propagating past an
        # impact, so the track runs on through the planet; "settled" can't be required there. Small bodies are
        # too lumpy for a single radius, so a landing there must settle (and their tracks stop at the surface).
        small_rule = SMALL_LANDINGS.get(hid)
        for k, t in enumerate(ts):
            c = ref_rows[t][2]
            d = vnorm(ref_rows[t][3])
            hit = False
            if c in PLANET_IDS and radius.get(c) and t > ts[0] + 1.0 and (
                    d * orbit.AU_KM < radius[c] or      # entry or impact (the track runs on through the planet)
                    (d * orbit.AU_KM < radius[c] * 1.01 + 1.0 and settled(k, c, (radius[c] * 1.01 + 1.0) / orbit.AU_KM))):
                hit = True                              # ...or a landing (sites can sit above the mean radius)
            elif small_rule and c == small_rule[0] and d * orbit.AU_KM < radius[c] * small_rule[1] and \
                    settled(k, c, radius[c] * small_rule[1] / orbit.AU_KM):
                hit = True
            if hit:
                cut = t
                verb = "Entered" if c in GAS_GIANTS else "Reached the surface of"
                end_note = "%s %s on %s; tracking ends there." % (verb, names[c], jd_to_iso(t)[:10])
                break
        if hid in catalog.END_AT_CLOSEST:
            b = catalog.END_AT_CLOSEST[hid]
            near_b = [t for t in ts if ref_rows[t][2] == b]
            for k in range(1, len(near_b) - 1):   # it stops closing in: end on the last point before that
                if vnorm(ref_rows[near_b[k + 1]][3]) >= vnorm(ref_rows[near_b[k]][3]) * 0.99:
                    cut = near_b[k - 1]   # near_b[k] already rides along with the target after the impact
                    end_note = "Crashed into its target on %s, as planned; tracking ends there." % jd_to_iso(near_b[k - 1])[:10]
                    break
        if hid in catalog.END_AT:
            when, end_note = catalog.END_AT[hid]
            cut = cal_to_jd(when) + 69.184 / 86400.0   # UTC -> TDB (about 69 s in 2015)
        if cut is not None:
            ts = [t for t in ts if t <= cut]
        ref = {"t": ts, "h": [ref_rows[t][0] for t in ts], "c": [ref_rows[t][2] for t in ts],
               "r": [ref_rows[t][3] for t in ts], "v": [ref_rows[t][4] for t in ts]}
        # jumps: consecutive reference points (same frame, at most a day apart) whose straight-line move disagrees
        # badly with the craft's own stated velocity at both ends. Burns, landings, and continuous thrust don't do
        # that; a jump in Horizons' own track does (Psyche, 2027-02-01). The validator skips samples inside these.
        seams = []
        for k in range(len(ts) - 1):
            if ref["c"][k] != ref["c"][k + 1] or ts[k + 1] - ts[k] > 1.01:
                continue
            dt = ts[k + 1] - ts[k]
            avg = [(ref["v"][k][i] + ref["v"][k + 1][i]) * 0.5 for i in range(3)]
            d = vnorm([ref["r"][k + 1][i] - ref["r"][k][i] - avg[i] * dt for i in range(3)])
            tol = max(probe_rel(ref["c"][k]) * vnorm(ref["r"][k + 1]), FLOOR_KM / orbit.AU_KM)
            if d > 0.5 * vnorm(avg) * dt and d > 3 * tol:
                seams.append((ts[k], ts[k + 1]))
        keep = segment_cached(hid, eph, ref, probe_rel, 0.0, zone)
        store(eph, hid, 0.0, keep, ref)
        intdes = horizons.intl_designator(hid)
        launch = horizons.launch_date(intdes)
        probes_out.append(pack(keep, ref, [
            ("id", hid), ("name", name), ("kind", kind), ("gm", 0.0), ("launch", launch), ("intdes", intdes),
            ("dataStart", jd_to_iso(ts[0])[:10]), ("dataEnd", jd_to_iso(ts[-1])[:10]),
            ("note", note), ("endNote", end_note), ("color", catalog.PROBE_COLOR[kind])]))
        by_c = {}
        for k in keep:
            by_c[ref["c"][k]] = by_c.get(ref["c"][k], 0) + 1
        meta_out["objects"][hid] = {"name": name, "kind": kind, "rel": REL_TOL["probe"], "windows": meta_windows,
                                    "minima": meta_minima, "t0": ts[0], "t1": ts[-1], "seams": seams}
        say(report, "%-26s %6d reference -> %5d states; near: %s%s%s" % (
            name, len(ts), len(keep), ", ".join("%s:%d" % (names.get(c, "Sun"), n) for c, n in sorted(by_c.items())),
            ("; " + end_note) if end_note else "",
            ("; %d jump(s) in Horizons' track: %s" % (len(seams), ", ".join(jd_to_iso(a)[:10] for a, b in seams[:4]))) if seams else ""))

    header_common = [
        "Source: JPL Horizons (https://ssd.jpl.nasa.gov/horizons/), retrieved %s. Physical data: Horizons, JPL SBDB, and the" % stamp,
        "published values cited in each object's radiusSrc. Launch dates: CelesTrak SATCAT.",
        "Frame: ecliptic J2000 (ICRF), heliocentric unless a state's center says otherwise. Units: AU, AU/day, TDB Julian days.",
        "Each object: t[] state times, c[] index into centers[] (Horizons IDs, '10' = Sun), s[] = x,y,z,vx,vy,vz per state.",
        "Positions between states: Kepler propagation from each neighboring state, smoothstep-blended (see tools/orbit.py).",
        "Generated by tools/build.py. Do not edit by hand.",
    ]
    sun_meta = "window.SOLAR_DATA_SUN = {gm:%s, gmKm:%s, radiusKm:%s};\nwindow.SOLAR_DATA_META = {built:%s, builtJd:%s};" % (
        fmt(gm_sun), fmt(gm_sun_km), fmt(r_sun), json.dumps(stamp), fmt(built_jd))
    write_js(os.path.join(ROOT, "bodies.js"), "bodies", ["bodies.js: Sun, planets, dwarf planets, small bodies."] + header_common, bodies_out)
    with open(os.path.join(ROOT, "bodies.js"), "a") as f:
        f.write(sun_meta + "\n")
    write_js(os.path.join(ROOT, "moons.js"), "moons", ["moons.js: moons, stored relative to their planets."] + header_common, moons_out)
    write_js(os.path.join(ROOT, "probes.js"), "probes", ["probes.js: spacecraft."] + header_common, probes_out)
    with open(os.path.join(ROOT, "tools", "build-meta.json"), "w") as f:
        json.dump(meta_out, f, indent=1)
    report.append("")
    for fn in ("bodies.js", "moons.js", "probes.js"):
        report.append("%s: %.0f KB" % (fn, os.path.getsize(os.path.join(ROOT, fn)) / 1024))
    with open(os.path.join(ROOT, "tools", "build-report.txt"), "w") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report[-4:]))


if __name__ == "__main__":
    main()
