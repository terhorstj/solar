"""Two-body (Kepler) propagation and the piecewise evaluator.

This mirrors the JavaScript in index.html line for line, so the accuracy measured
here is the accuracy the page shows. Units: AU, days, AU^3/day^2.

Evaluator: each object stores states (t, center, r, v). Between two stored states,
the position at time t is a smoothstep blend of a Kepler propagation from each end,
each converted to heliocentric by adding its center's position.
"""
import bisect
import math

AU_KM = 149597870.7
DAY_S = 86400.0


def gm_km3s2_to_au3d2(gm):
    return gm * DAY_S * DAY_S / (AU_KM ** 3)


def stumpff_c(z):
    if z > 1e-6:
        return (1.0 - math.cos(math.sqrt(z))) / z
    if z < -1e-6:
        return (math.cosh(math.sqrt(-z)) - 1.0) / (-z)
    return 0.5 - z / 24.0 + z * z / 720.0


def stumpff_s(z):
    if z > 1e-6:
        s = math.sqrt(z)
        return (s - math.sin(s)) / (s * s * s)
    if z < -1e-6:
        s = math.sqrt(-z)
        return (math.sinh(s) - s) / (s * s * s)
    return 1.0 / 6.0 - z / 120.0 + z * z / 5040.0


def kepler(r0, v0, mu, dt):
    """Position after dt days on the two-body orbit through (r0, v0). Universal variables."""
    if dt == 0.0:
        return (r0[0], r0[1], r0[2])
    if mu <= 0.0:   # no known gravity (a small body with no measured GM): straight-line motion
        return (r0[0] + v0[0] * dt, r0[1] + v0[1] * dt, r0[2] + v0[2] * dt)
    rn = math.sqrt(r0[0] * r0[0] + r0[1] * r0[1] + r0[2] * r0[2])
    rv = r0[0] * v0[0] + r0[1] * v0[1] + r0[2] * v0[2]
    v2 = v0[0] * v0[0] + v0[1] * v0[1] + v0[2] * v0[2]
    smu = math.sqrt(mu)
    alpha = 2.0 / rn - v2 / mu
    # Laguerre's method (n = 5), kept inside a bracket on x. F(x) increases with x and F(0) = -sqrt(mu)*dt,
    # so the root lies on dt's side of 0. A step that leaves the bracket, or an x so large that cosh would
    # overflow (fast escapes starting close to a planet), falls back to halving the bracket.
    x = smu * dt * alpha if alpha > 1e-12 else smu * dt / rn
    k1 = rv / smu
    k2 = 1.0 - alpha * rn
    lo, hi = (0.0, math.inf) if dt > 0 else (-math.inf, 0.0)
    for _ in range(200):
        z = alpha * x * x
        if z < -490000.0:   # sqrt(-z) > 700: far past the root
            if x > 0:
                hi = x
            else:
                lo = x
            x = 0.5 * (lo + hi) if math.isfinite(lo) and math.isfinite(hi) else 0.5 * x
            continue
        c = stumpff_c(z)
        s = stumpff_s(z)
        f = k1 * x * x * c + k2 * x * x * x * s + rn * x - smu * dt
        df = k1 * x * (1.0 - z * s) + k2 * x * x * c + rn
        d2f = k1 * (1.0 - z * c) + k2 * x * (1.0 - z * s)
        if f > 0:
            hi = min(hi, x)
        else:
            lo = max(lo, x)
        disc = math.sqrt(abs(16.0 * df * df - 20.0 * f * d2f))
        dx = 5.0 * f / (df + disc if df >= 0 else df - disc)
        xn = x - dx
        if f == 0.0 or abs(xn - x) <= 1e-13 * max(1.0, abs(xn)):   # converged (checked before the bracket test:
            x = xn                                                  # an exact root sits on the bracket's edge)
            break
        if not (lo < xn < hi):
            if math.isfinite(lo) and math.isfinite(hi):
                xn = 0.5 * (lo + hi)
            else:
                xn = 2.0 * x if (f < 0) == (x > 0) else 0.5 * x   # one side open: step outward, toward the root
        x = xn
    z = alpha * x * x
    fl = 1.0 - x * x / rn * stumpff_c(z)
    gl = dt - x * x * x / smu * stumpff_s(z)
    return (fl * r0[0] + gl * v0[0], fl * r0[1] + gl * v0[1], fl * r0[2] + gl * v0[2])


def smooth(u):
    return u * u * (3.0 - 2.0 * u)


class Ephem:
    """Holds every object's stored states and evaluates heliocentric positions."""

    SUN = "10"

    def __init__(self):
        self.objs = {}  # id -> dict(gm, t[], c[], r[], v[])
        self.gm = {self.SUN: None}

    def set_sun_gm(self, gm):
        self.gm[self.SUN] = gm

    def add(self, oid, gm, times, centers, rs, vs):
        self.gm[oid] = gm
        self.objs[oid] = {"t": list(times), "c": list(centers), "r": list(rs), "v": list(vs)}

    def center_pos(self, cid, t):
        if cid == self.SUN:
            return (0.0, 0.0, 0.0)
        return self.pos(cid, t)

    def _end_pos(self, o, oid, k, t):
        c = o["c"][k]
        mu = self.gm[c] + self.gm[oid]
        p = kepler(o["r"][k], o["v"][k], mu, t - o["t"][k])
        cp = self.center_pos(c, t)
        return (p[0] + cp[0], p[1] + cp[1], p[2] + cp[2])

    def pos(self, oid, t):
        """Heliocentric position, or None outside the object's span."""
        o = self.objs[oid]
        ts = o["t"]
        if t < ts[0] or t > ts[-1]:
            return None
        i = bisect.bisect_right(ts, t) - 1
        if i >= len(ts) - 1:
            return self._end_pos(o, oid, len(ts) - 1, t)
        p0 = self._end_pos(o, oid, i, t)
        p1 = self._end_pos(o, oid, i + 1, t)
        w = smooth((t - ts[i]) / (ts[i + 1] - ts[i]))
        return (p0[0] + (p1[0] - p0[0]) * w, p0[1] + (p1[1] - p0[1]) * w, p0[2] + (p1[2] - p0[2]) * w)
