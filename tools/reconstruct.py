"""Rebuild the six probes Horizons doesn't have (probes-rebuilt.js) from their dated mission events.

Sources and the values chosen are in probe-events.md. Method (patched conics):

  1. Legs: between consecutive events, the coasting two-body orbit (around the Sun; around Earth for
     Luna 1) that leaves one body's real position on its date and arrives at the next body's real
     position on its date (Horizons positions via the stored data). Found by shooting: adjust the
     departure velocity until the propagated orbit hits the target.
  2. Encounters: inside each body's zone, a hyperbola with the documented closest distance, its
     incoming direction from the arriving leg, bent by the body's gravity (straight line for a comet
     with no known mass). Departures from Earth start at a 200 km parking-orbit perigee.
  3. Legs are re-solved between the hyperbolas' exit and entry points.
  4. Vikings: after capture, ellipses of the published sizes around Mars, in the plane of the
     arrival hyperbola (the real orbits' orientation isn't published in the sources used).

Positions are exact at the encounters (to the documented distance) and approximate in between.
Tracks end at end of mission (John's decision, 2026-10-19).

Run:  python3 tools/reconstruct.py     (after build.py; writes probes-rebuilt.js)
"""
import datetime
import json
import math
import os

import build
import orbit
import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUN, EARTH, MOON, MARS = "10", "399", "301", "499"
KM = 1.0 / orbit.AU_KM
MIN = 1.0 / 1440.0
PARK_KM = 6371.0 + 200.0     # departure perigee: a 200 km parking orbit


def ut(s):
    """UT calendar string -> TDB Julian day (TDB - UT ramps from about 33 s in 1959 to 59 s in 1992)."""
    d = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S" if s.count(":") == 2 else "%Y-%m-%d %H:%M")
    jd = build.cal_to_jd(d.strftime("%Y-%m-%d %H:%M")) + d.second / 86400.0
    return jd + (33.0 + (d.year + d.timetuple().tm_yday / 365.25 - 1959.0) * 0.8) / 86400.0


# ---- the six probes (values and sources: probe-events.md) ----------------------------------------------
# event kinds: depart(body, time, perigee km), flyby(body, time, closest km from center),
#              capture(body, time, [(phase start, periapsis km from center, apoapsis km from center), ...]),
#              end(time)
PROBES = [
    {"id": "luna1", "name": "Luna 1", "launch": "1959-01-02", "intdes": "1959-012A", "frame": EARTH,
     "note": "Rebuilt from mission dates: approximate. Passed the Moon, then went into orbit around the Sun.",
     "events": [("depart", EARTH, "1959-01-02 17:11", PARK_KM),             # launch 16:41 + ~30 min to injection
                ("flyby", MOON, "1959-01-04 02:41", 1737.4 + 5995.0),      # ~34 h after launch, 5,995 km up
                ("end", None, "1959-01-05 06:41", None)],                  # contact lost ~62 h after launch
     "endNote": "Contact was lost on 1959-01-05, about 62 hours after launch; tracking ends there."},
    {"id": "mariner4", "name": "Mariner 4", "launch": "1964-11-28", "intdes": "1964-077A", "frame": SUN,
     "note": "Rebuilt from mission dates: approximate. First successful flyby of Mars.",
     "events": [("depart", EARTH, "1964-11-28 15:04:28", PARK_KM),
                ("flyby", MARS, "1965-07-15 01:00:57", 3389.9 + 9846.0),
                ("end", None, "1967-12-21 12:00", None)],
     "endNote": "Communications ended on 1967-12-21; tracking ends there."},
    {"id": "mariner10", "name": "Mariner 10", "launch": "1973-11-03", "intdes": "1973-085A", "frame": SUN,
     "note": "Rebuilt from mission dates: approximate. First gravity assist (Venus) and first visit to Mercury.",
     "events": [("depart", EARTH, "1973-11-03 06:10", PARK_KM),              # launch ~05:45 + ~25 min parking orbit
                ("flyby", "299", "1974-02-05 17:01", 6051.8 + 5768.0),
                ("flyby", "199", "1974-03-29 20:46", 2439.4 + 704.0),
                ("flyby", "199", "1974-09-21 20:59", 2439.4 + 48069.0),
                ("flyby", "199", "1975-03-16 22:39", 2439.4 + 327.0),
                ("end", None, "1975-03-24 12:00", None)],
     "endNote": "Attitude-control gas ran out on 1975-03-24; tracking ends there."},
    {"id": "viking1", "name": "Viking 1", "launch": "1975-08-20", "intdes": "1975-075A", "frame": SUN,
     "note": "Rebuilt from mission dates: approximate. The orbiter; its lander touched down in Chryse Planitia on 1976-07-20. "
             "The orbit's size around Mars is published, its orientation isn't.",
     "events": [("depart", EARTH, "1975-08-20 21:52", PARK_KM),
                ("capture", MARS, "1976-06-19 12:00", [("1976-06-19 12:00", 3389.9 + 1513.0, 3389.9 + 33000.0),
                                                       ("1977-03-11 12:00", 3389.9 + 300.0, 3389.9 + 33943.0),
                                                       ("1979-07-20 12:00", 3389.9 + 357.0, 3389.9 + 33943.0),
                                                       ("1980-08-07 12:00", 3389.9 + 320.0, 3389.9 + 56000.0)]),
                ("end", None, "1980-08-17 12:00", None)],
     "endNote": "Operations ended on 1980-08-17, low on attitude-control gas; tracking ends there."},
    {"id": "viking2", "name": "Viking 2", "launch": "1975-09-09", "intdes": "1975-083A", "frame": SUN,
     "note": "Rebuilt from mission dates: approximate. The orbiter; its lander touched down in Utopia Planitia on 1976-09-03. "
             "The orbit's size around Mars is published, its orientation isn't.",
     "events": [("depart", EARTH, "1975-09-09 19:09", PARK_KM),
                ("capture", MARS, "1976-08-07 12:00", [("1976-08-07 12:00", 3389.9 + 1500.0, 3389.9 + 33000.0),
                                                       ("1976-08-09 12:00", 3389.9 + 1499.0, None),       # 27.3 h orbit
                                                       ("1976-12-20 12:00", 3389.9 + 778.0, None),        # 27.3 h orbit
                                                       ("1977-10-23 12:00", 3389.9 + 302.0, 3389.9 + 33176.0)]),
                ("end", None, "1978-07-25 12:00", None)],
     "endNote": "Turned off on 1978-07-25 after a propulsion leak; tracking ends there.",
     "period_h": 27.3},
    {"id": "giotto", "name": "Giotto", "launch": "1985-07-02", "intdes": "1985-056A", "frame": SUN,
     "note": "Rebuilt from mission dates: approximate. Flew 596 km from Halley's nucleus, then reused Earth's gravity to reach a second comet.",
     "events": [("depart", EARTH, "1985-07-02 12:23", PARK_KM),
                ("flyby", "1P", "1986-03-14 00:03:02", 596.0),
                ("flyby", EARTH, "1990-07-02 12:00", 6371.0 + 22730.0),
                ("flyby", "26P", "1992-07-10 15:19", 200.0),
                ("end", None, "1992-07-23 12:00", None)],
     "endNote": "Operations ended on 1992-07-23; tracking ends there."},
]
COLOR = "#ffd27a"


# ---- vector helpers -------------------------------------------------------------------------------------
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a): n = norm(a); return mul(a, 1.0 / n)


def rotate(v, axis, ang):
    """Rodrigues rotation of v about a unit axis."""
    c, s = math.cos(ang), math.sin(ang)
    return add(add(mul(v, c), mul(cross(axis, v), s)), mul(axis, dot(axis, v) * (1 - c)))


def solve3(J, b):
    """Solve the 3x3 system J x = b (Cramer)."""
    def det(m): return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    d = det(J)
    out = []
    for k in range(3):
        m = [list(r) for r in J]
        for i in range(3):
            m[i][k] = b[i]
        out.append(det(m) / d)
    return tuple(out)


# ---- dynamics -------------------------------------------------------------------------------------------
def prop(r, v, mu, dt):
    """Position and velocity after dt on the conic (velocity by a central difference of one second)."""
    h = 1.0 / 86400.0
    p = orbit.kepler(r, v, mu, dt)
    a = orbit.kepler(r, v, mu, dt - h)
    b = orbit.kepler(r, v, mu, dt + h)
    return p, mul(sub(b, a), 0.5 / h)


def shoot(r1, t1, r2, t2, mu, vguess):
    """Departure velocity at r1 (time t1) whose coasting orbit reaches r2 at t2. Newton on the miss vector."""
    v = vguess
    dt = t2 - t1
    for _ in range(60):
        p = orbit.kepler(r1, v, mu, dt)
        miss = sub(p, r2)
        if norm(miss) < 0.5 * KM:
            return v
        dv = max(norm(v), 1e-9) * 1e-7
        J = [[0.0] * 3 for _ in range(3)]
        for j in range(3):
            e = [0.0, 0.0, 0.0]
            e[j] = dv
            pj = orbit.kepler(r1, add(v, tuple(e)), mu, dt)
            for i in range(3):
                J[i][j] = (pj[i] - p[i]) / dv
        step = solve3(J, mul(miss, -1.0))
        lam = 1.0   # damped: never let a step make the miss worse
        while lam > 1e-4:
            vn = add(v, mul(step, lam))
            if norm(sub(orbit.kepler(r1, vn, mu, dt), r2)) < norm(miss):
                break
            lam *= 0.5
        v = vn
    raise RuntimeError("shooting did not converge (miss %.0f km)" % (norm(miss) / KM))


def lambert(r1, r2, dt, mu, normal):
    """Departure velocity for the single-revolution prograde transfer r1 -> r2 in time dt (universal variables;
    Curtis, Orbital Mechanics for Engineering Students, algorithm 5.2). normal sets which way is prograde."""
    r1n, r2n = norm(r1), norm(r2)
    c = max(-1.0, min(1.0, dot(r1, r2) / (r1n * r2n)))
    dth = math.acos(c)
    if dot(cross(r1, r2), normal) < 0:
        dth = 2 * math.pi - dth
    A = math.sin(dth) * math.sqrt(r1n * r2n / (1 - math.cos(dth)))
    def y(z):
        return r1n + r2n + A * (z * orbit.stumpff_s(z) - 1) / math.sqrt(orbit.stumpff_c(z))
    def F(z):
        yz = y(z)
        return (yz / orbit.stumpff_c(z)) ** 1.5 * orbit.stumpff_s(z) + A * math.sqrt(yz) - math.sqrt(mu) * dt
    hi = 4 * math.pi ** 2 - 1e-6
    lo = -4 * math.pi ** 2
    while y(lo) < 0:          # y must be positive: move the lower end up until it is
        lo = 0.5 * (lo + hi) if lo < -1 else lo + 0.5
    for _ in range(200):      # F increases with z: bisect
        mid = 0.5 * (lo + hi)
        if y(mid) < 0 or F(mid) < 0:
            lo = mid
        else:
            hi = mid
    z = 0.5 * (lo + hi)
    yz = y(z)
    f = 1 - yz / r1n
    g = A * math.sqrt(yz / mu)
    return mul(sub(r2, mul(r1, f)), 1.0 / g)


def lambert_all(r1, r2, dt, mu, normal, max_revs):
    """Every prograde transfer r1 -> r2 in time dt with 0 to max_revs complete revolutions on the way.

    Same universal-variable time equation as lambert(); for N revolutions the root lies in
    z in (4 pi^2 N^2, 4 pi^2 (N+1)^2), where there are usually two (a shorter and a longer orbit)."""
    r1n, r2n = norm(r1), norm(r2)
    c = max(-1.0, min(1.0, dot(r1, r2) / (r1n * r2n)))
    dth = math.acos(c)
    if dot(cross(r1, r2), normal) < 0:
        dth = 2 * math.pi - dth
    A = math.sin(dth) * math.sqrt(r1n * r2n / (1 - math.cos(dth)))
    def y(z):
        return r1n + r2n + A * (z * orbit.stumpff_s(z) - 1) / math.sqrt(orbit.stumpff_c(z))
    def F(z):
        yz = y(z)
        if yz <= 0:
            return None
        return (yz / orbit.stumpff_c(z)) ** 1.5 * orbit.stumpff_s(z) + A * math.sqrt(yz) - math.sqrt(mu) * dt
    out = []
    try:
        out.append(lambert(r1, r2, dt, mu, normal))
    except (ValueError, ZeroDivisionError, OverflowError):
        pass
    for N in range(1, max_revs + 1):
        lo, hi = (2 * math.pi * N) ** 2, (2 * math.pi * (N + 1)) ** 2
        zs = [lo + (hi - lo) * (k + 0.5) / 4000.0 for k in range(4000)]
        fs = [F(z) for z in zs]
        for k in range(len(zs) - 1):
            if fs[k] is None or fs[k + 1] is None or (fs[k] > 0) == (fs[k + 1] > 0):
                continue
            a, b = zs[k], zs[k + 1]
            for _ in range(100):
                m = 0.5 * (a + b)
                fm = F(m)
                if fm is None:
                    break
                if (fm > 0) == (fs[k] > 0):
                    a = m
                else:
                    b = m
            z = 0.5 * (a + b)
            yz = y(z)
            f = 1 - yz / r1n
            g = A * math.sqrt(yz / mu)
            out.append(mul(sub(r2, mul(r1, f)), 1.0 / g))
    return out


class World:
    def __init__(self):
        self.eph, _ = validate.load_all()
        meta = json.load(open(os.path.join(ROOT, "tools", "build-meta.json")))
        self.zone = dict(meta["zones"])
        gm_e, gm_m = self.eph.gm[EARTH], self.eph.gm[MOON]
        moon_a = 384400.0 * KM
        self.zone[MOON] = moon_a * (gm_m / gm_e) ** 0.4     # the Moon's sphere of influence relative to Earth

    def pos(self, b, t):
        return (0.0, 0.0, 0.0) if b == SUN else self.eph.pos(b, t)

    def vel(self, b, t):
        if b == SUN:
            return (0.0, 0.0, 0.0)
        h = 1e-3
        return mul(sub(self.eph.pos(b, t + h), self.eph.pos(b, t - h)), 0.5 / h)

    def gm(self, b):
        return self.eph.gm[b]


def hyperbola(mu, rp, vinf, u_in, u_out_hint, ref, zone):
    """Periapsis state (relative to the body) and the time from periapsis to the zone edge.

    u_in: incoming direction (unit). u_out_hint: the direction the next leg wants (or None). The hyperbola bends
    u_in by the angle its periapsis and speed allow, in the plane of u_in and the hint (or of u_in and ref)."""
    other = u_out_hint if u_out_hint is not None and norm(cross(u_in, u_out_hint)) > 1e-9 else ref
    n = unit(cross(u_in, other))
    if mu <= 0:   # no known gravity: a straight pass
        p_hat = unit(cross(n, u_in))
        return mul(p_hat, rp), mul(u_in, vinf), math.sqrt(max(zone * zone - rp * rp, 0.0)) / vinf, u_in
    e = 1.0 + rp * vinf * vinf / mu
    delta = 2.0 * math.asin(1.0 / e)
    u_out = rotate(u_in, n, delta)
    p_hat = unit(sub(u_in, u_out))
    q_hat = unit(add(u_in, u_out))
    vp = math.sqrt(vinf * vinf + 2.0 * mu / rp)
    a = mu / (vinf * vinf)
    F = math.acosh(max((1.0 + zone / a) / e, 1.0))
    tz = math.sqrt(a ** 3 / mu) * (e * math.sinh(F) - F)
    return mul(p_hat, rp), mul(q_hat, vp), tz, u_out


def luna_perigee(r_moon, v_moon):
    """A 200 km perigee in the Moon's orbital plane, 165 degrees back from where the Moon will be: a near-escape
    orbit from there takes about a day and a half to reach the Moon's distance (Luna 1 took 34 hours)."""
    n = unit(cross(r_moon, v_moon))
    return mul(unit(rotate(r_moon, n, -math.radians(165))), PARK_KM * KM)


def reconstruct(W, P):
    frame = P["frame"]
    mu_c = W.gm(frame) + 0.0
    ev = [(k, b, ut(t), x) for (k, b, t, x) in P["events"]]
    rel = lambda b, t: sub(W.pos(b, t), W.pos(frame, t))           # body position in the leg frame
    relv = lambda b, t: sub(W.vel(b, t), W.vel(frame, t))
    report = []

    # pass 1: legs from body center to body center, to learn the arrival and departure directions
    targets = [i for i, e in enumerate(ev) if e[0] in ("depart", "flyby", "capture")]
    vdep, varr = {}, {}
    for a, b in zip(targets, targets[1:]):
        ta, tb = ev[a][2], ev[b][2]
        ra, rb = rel(ev[a][1], ta), rel(ev[b][1], tb)
        if frame != SUN and a not in varr:
            ra = luna_perigee(rb, relv(ev[b][1], tb))   # Luna 1 leaves from its perigee
        normal = cross(ra, relv(ev[b][1], tb)) if frame != SUN else (0.0, 0.0, 1.0)
        cands = []
        max_revs = int((tb - ta) / 60.0) if a in varr else 0   # the shortest plausible orbit here is about 60 days
        for g in lambert_all(ra, rb, tb - ta, mu_c, normal, max_revs):
            try:
                cands.append(shoot(ra, ta, rb, tb, mu_c, g))
            except (RuntimeError, ValueError, ZeroDivisionError, OverflowError):
                pass
        if a in varr:   # the transfer that keeps looping like the arriving orbit (multi-revolution legs)
            try:
                cands.append(shoot(ra, ta, rb, tb, mu_c, varr[a]))
            except (RuntimeError, ValueError, ZeroDivisionError, OverflowError):
                pass
        if not cands:
            raise RuntimeError("%s: no transfer found from %s to %s" % (P["name"], ev[a][1], ev[b][1]))
        if a in varr:   # an unpowered flyby leaves at the speed it arrived: pick the leg that matches best
            bv = relv(ev[a][1], ta)
            vin = norm(sub(varr[a], bv))
            v = min(cands, key=lambda c: abs(norm(sub(c, bv)) - vin))
        else:
            v = cands[0]
        vdep[a] = v
        varr[b] = prop(ra, v, mu_c, tb - ta)[1]
    # pass 2: hyperbolas at each body
    hyp = {}
    for i in targets:
        kind, body, t, x = ev[i]
        bv = relv(body, t)
        sun_dir = unit(mul(W.pos(body, t), -1.0)) if body != SUN else (0, 0, 1)
        mu_b = W.gm(body)
        zone = W.zone.get(body, 0.001)
        if kind == "depart":
            vout = sub(vdep[i], bv) if frame == SUN else None
            if frame != SUN:   # Luna 1: its legs are already Earth-centered; the first leg starts at the perigee
                hyp[i] = None
                continue
            u_out = unit(vout)
            vinf = norm(vout)
            # run the departure hyperbola backward: a hyperbola whose outgoing asymptote is u_out
            n = unit(cross(u_out, sun_dir))
            e = 1.0 + x * KM * vinf * vinf / mu_b
            u_in = rotate(u_out, n, -2.0 * math.asin(1.0 / e))
            rp, vp, tz, _ = hyperbola(mu_b, x * KM, vinf, u_in, u_out, sun_dir, zone)
            hyp[i] = (rp, vp, tz, body, t)
            report.append("  leave %-8s v_inf %.2f km/s" % (body, vinf / KM / 86400))
        else:
            vin = sub(varr[i], bv)
            vout = sub(vdep[i], bv) if i in vdep else None
            u_out_hint = unit(vout) if vout is not None else None
            vinf = 0.5 * (norm(vin) + norm(vout)) if vout is not None else norm(vin)
            rp_km = x[0][1] if kind == "capture" else x
            rp, vp, tz, u_out = hyperbola(mu_b, rp_km * KM, vinf, unit(vin), u_out_hint, sun_dir, zone)
            if kind == "capture":
                rp, vp, tz, _ = hyperbola(mu_b, x[0][1] * KM, vinf, unit(vin), None, sun_dir, zone)
            hyp[i] = (rp, vp, tz, body, t)
            if vout is not None:
                ang = math.degrees(math.acos(max(-1, min(1, dot(unit(vin), unit(vout))))))
                bend = math.degrees(math.acos(max(-1, min(1, dot(unit(vin), u_out)))))
                report.append("  pass %-8s v_inf in %.3f, out %.3f km/s; legs need a %.1f deg turn, the pass gives %.1f deg" % (
                    body, norm(vin) / KM / 86400, norm(vout) / KM / 86400, ang, bend))
            else:
                report.append("  %s %-8s v_inf %.2f km/s" % ("capture at" if kind == "capture" else "last pass", body, vinf / KM / 86400))
            if vout is None and kind == "flyby":   # last flyby: continue on the bent asymptote
                hyp[i] = (rp, vp, tz, body, t, mul(u_out, vinf))

    # pass 3: assemble states. Legs run between hyperbola exit and entry points (re-solved); each hyperbola is
    # stored relative to its body. Neighboring states of different kinds sit a minute apart.
    states = []   # (t, center, r, v)
    def add_state(t, c, r, v):
        if states and t <= states[-1][0] + 1e-9:
            t = states[-1][0] + 1e-6
        states.append((t, c, r, v))

    def hyp_state(i, dt):
        rp, vp, tz, body, t = hyp[i][:5]
        return prop(rp, vp, W.gm(body), dt)

    first = targets[0]
    if hyp[first] is None:   # Luna 1: Earth-centered from the perigee
        nb, nt = ev[targets[1]][1], ev[targets[1]][2]
        start = (ev[first][2], luna_perigee(rel(nb, nt), relv(nb, nt)), vdep[first])
    else:
        rp, vp, tz, body, t = hyp[first][:5]
        add_state(t, body, rp, vp)                                  # perigee at injection
        r_ex, v_ex = hyp_state(first, tz - MIN)
        add_state(t + tz - MIN, body, r_ex, v_ex)
        r_ex, v_ex = hyp_state(first, tz)
        start = (t + tz, add(rel(body, t + tz), r_ex), vdep[first])   # search from the center-to-center leg
    for i in targets[1:]:
        kind, body, t, x = ev[i]
        rp, vp, tz, _, _ = hyp[i][:5]
        r_en, v_en = hyp_state(i, -tz)
        t_en = t - tz
        target = add(rel(body, t_en), r_en)
        t0, r0, vguess = start
        # exact transfers (any number of loops), taking the one nearest the center-to-center leg from pass 1
        normal = cross(r0, relv(body, t_en)) if frame != SUN else (0.0, 0.0, 1.0)
        cands = lambert_all(r0, target, t_en - t0, mu_c, normal, int((t_en - t0) / 60.0))
        cands = [c for c in cands if norm(sub(orbit.kepler(r0, c, mu_c, t_en - t0), target)) < 5 * KM]
        if not cands:
            raise RuntimeError("%s, leg to %s (%s): no transfer found" % (P["name"], body, build.jd_to_iso(t_en)))
        v0 = min(cands, key=lambda c: norm(sub(c, vguess)))
        add_state(t0, frame, r0, v0)
        r1, v1 = prop(r0, v0, mu_c, t_en - t0)
        add_state(t_en, frame, r1, v1)
        add_state(t_en + MIN, body, *hyp_state(i, -tz + MIN))
        if kind == "capture":
            add_state(t - 10 * MIN, body, *hyp_state(i, -10 * MIN))
            p_hat, q_hat = unit(rp), unit(vp)
            mu_b = W.gm(body)
            phases = x
            end_t = ev[-1][2]
            tk = t
            for k, (ts, rpk, rak) in enumerate(phases):
                if rak is None:   # size given by period
                    a = (mu_b * (P["period_h"] / 24.0 / (2 * math.pi)) ** 2) ** (1.0 / 3.0)
                    rak = (2 * a - rpk * KM) / KM
                rpk, rak = rpk * KM, rak * KM
                a = 0.5 * (rpk + rak)
                # every phase starts at a periapsis passage, so the switch between ellipses only moves the craft
                # by the change in periapsis distance (the real burns' timing isn't in the sources)
                r_k, v_k = mul(p_hat, rpk), mul(q_hat, math.sqrt(mu_b * (2 / rpk - 1 / a)))
                add_state(tk, body, r_k, v_k)
                period = 2 * math.pi * math.sqrt(a ** 3 / mu_b)
                if k + 1 < len(phases):   # the periapsis passage nearest the documented date of the next change
                    t_next = tk + round((ut(phases[k + 1][0]) - tk) / period) * period
                else:
                    t_next = end_t
                add_state(t_next - MIN, body, *prop(r_k, v_k, mu_b, t_next - MIN - tk))
                tk = t_next
            return states, report
        add_state(t, body, rp, vp)
        r_ex, v_ex = hyp_state(i, tz - MIN)
        add_state(t + tz - MIN, body, r_ex, v_ex)
        r_ex, v_ex = hyp_state(i, tz)
        nxt = vdep[i] if i in vdep else add(relv(body, t + tz), v_ex)   # center-to-center leg as the starting guess
        start = (t + tz, add(rel(body, t + tz), r_ex), nxt)
        if i not in vdep:   # last pass: coast on the bent asymptote (no next target to aim for)
            start = (t + tz, start[1], add(relv(body, t + tz), v_ex))
    # coast to end of mission
    t0, r0, v0 = start
    t_end = ev[-1][2]
    add_state(t0, frame, r0, v0)
    add_state(t_end, frame, *prop(r0, v0, mu_c, t_end - t0))
    return states, report


def main():
    W = World()
    out = []
    lines = ["Reconstruction report, %s. Values and sources: probe-events.md." % datetime.date.today().isoformat(), ""]
    for P in PROBES:
        states, report = reconstruct(W, P)
        centers = []
        for s in states:
            if s[1] not in centers:
                centers.append(s[1])
        flat = []
        for t, c, r, v in states:
            flat.extend(r)
            flat.extend(v)
        meta = [("id", P["id"]), ("name", P["name"]), ("kind", "probe"), ("gm", 0.0), ("launch", P["launch"]),
                ("intdes", P["intdes"]), ("dataStart", build.jd_to_iso(states[0][0])[:10]),
                ("dataEnd", build.jd_to_iso(states[-1][0])[:10]), ("note", P["note"]), ("endNote", P["endNote"]),
                ("color", COLOR), ("rebuilt", "yes")]
        out.append({"meta": meta, "centers": centers, "t": [s[0] for s in states],
                    "c": [centers.index(s[1]) for s in states], "s": flat})
        lines.append("%s: %d states" % (P["name"], len(states)))
        lines.extend(report)
        # Luna 1 check: its heliocentric orbit once free of Earth (NSSDCA-era figure: period about 450 days)
        if P["id"] == "luna1":
            t, c, r, v = states[-1]
            vinf = math.sqrt(max(dot(v, v) - 2 * W.gm(EARTH) / norm(r), 0.0))
            vh = add(W.vel(EARTH, t), mul(unit(v), vinf))
            rh = W.pos(EARTH, t)
            a = 1.0 / (2.0 / norm(rh) - dot(vh, vh) / W.gm(SUN))
            lines.append("  check: heliocentric period once clear of Earth about %.0f days (expected about 450)" % (
                2 * math.pi * math.sqrt(a ** 3 / W.gm(SUN))))
    build.write_js(os.path.join(ROOT, "probes-rebuilt.js"), "rebuilt", [
        "probes-rebuilt.js: probes Horizons doesn't have, rebuilt from dated mission events (approximate).",
        "Event dates: NASA NSSDCA and NASA mission pages, or best guesses where marked; see probe-events.md.",
        "Body positions: JPL Horizons (via bodies.js and moons.js). Method: patched conics; see tools/reconstruct.py.",
        "Format as probes.js. Generated by tools/reconstruct.py on %s. Do not edit by hand." % datetime.date.today().isoformat()], out)
    with open(os.path.join(ROOT, "tools", "reconstruct-report.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
