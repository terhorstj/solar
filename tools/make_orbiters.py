"""Build orbiters.js: the Earth-orbiters drawn as rings around Earth (sources: earth-orbiters.md).

  current (still in orbit)   CelesTrak elements fetched at build time: size, shape, tilt, and orientation,
                             plus where the object is along its orbit at the elements' date
  historical (reentered)     published first and final orbits; the page shrinks the ring from one to the
                             other over the object's lifetime. Position along the orbit is unknown.

The page turns these into positions with orbit.js-style math in index.html (ORBITERS block): two-body
motion plus the secular drift from Earth's equatorial bulge (J2), see orbiter_pos() below, which mirrors it.

Run:  python3 tools/make_orbiters.py
"""
import datetime
import json
import math
import os
import urllib.request

import build
import horizons

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GP = "https://celestrak.org/NORAD/elements/gp.php"
MU_E = 398600.4418      # km^3/s^2 (WGS-84)
RE = 6378.137           # km, Earth's equatorial radius
J2 = 1.08262668e-3
TDB_MINUS_UTC_S = 69.184   # 37 leap seconds + 32.184 s, valid since 2017

CURRENT = [   # NORAD id, name, color
    (25544, "ISS", "#e8f2ff"),
    (20580, "Hubble", "#c9e4ff"),
    (48274, "Tiangong", "#ffd9c9"),
    (25867, "Chandra", "#d9d0ff"),
    (5, "Vanguard 1", "#cfe8d4"),
    (340, "Telstar 1", "#e6e0c8"),
]
HISTORICAL = [   # NORAD id, name, color, first orbit (perigee, apogee km altitude), inclination deg, note
    (2, "Sputnik 1", "#ffcfb0", (215.0, 939.0), 65.1, "First orbit from memory (consistent with its documented 96-minute period)."),
    (4, "Explorer 1", "#c8e0c0", (358.0, 2550.0), 33.15, "First orbit from memory."),
    (6633, "Skylab", "#e0d8c0", (434.0, 442.0), 50.0, "First orbit from NSSDCA."),
    (16609, "Mir", "#d8d0e8", (350.0, 375.0), 51.64, "Typical orbit from memory; Mir was reboosted many times."),
]


def fetch_gp(norad):
    """Current elements, always fresh (not from the cache)."""
    url = GP + "?CATNR=%d&FORMAT=json" % norad
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())[0]


def iso_to_jd_utc(s):
    d = datetime.datetime.fromisoformat(s.replace("Z", ""))
    return (d - datetime.datetime(2000, 1, 1, 12)).total_seconds() / 86400.0 + 2451545.0


def main():
    stamp = datetime.date.today().isoformat()
    out = []
    lines = ["Orbiters report, %s." % stamp]
    for norad, name, color in CURRENT:
        g = fetch_gp(norad)
        sat = horizons._get_json(horizons.SATCAT, {"CATNR": str(norad), "FORMAT": "json"})[0]
        n = g["MEAN_MOTION"] * 2 * math.pi            # rad/day
        a = (MU_E * 86400.0 ** 2 / n ** 2) ** (1.0 / 3.0)
        epoch = iso_to_jd_utc(g["EPOCH"]) + TDB_MINUS_UTC_S / 86400.0
        o = {"id": "sat%d" % norad, "name": name, "norad": norad, "intdes": sat["OBJECT_ID"], "launch": sat["LAUNCH_DATE"],
             "decay": None, "color": color, "kind": "orbiter",
             "cur": {"epoch": epoch, "epochUtc": g["EPOCH"][:19], "n": n, "ndot": g["MEAN_MOTION_DOT"] * 2 * math.pi,
                     "a": a, "e": g["ECCENTRICITY"], "i": g["INCLINATION"], "raan": g["RA_OF_ASC_NODE"],
                     "argp": g["ARG_OF_PERICENTER"], "M0": g["MEAN_ANOMALY"]}}
        out.append(o)
        lines.append("%-11s elements %s UTC: %.0f x %.0f km, %.2f deg" % (name, g["EPOCH"][:19], a * (1 - g["ECCENTRICITY"]) - RE,
                                                                      a * (1 + g["ECCENTRICITY"]) - RE, g["INCLINATION"]))
    for norad, name, color, first, inc, note in HISTORICAL:
        sat = horizons._get_json(horizons.SATCAT, {"CATNR": str(norad), "FORMAT": "json"})[0]
        # a decaying ring never grows: the final size is capped at the first (Sputnik 1's last catalog
        # apogee, 1,080 km, is higher than its first, 939 km)
        rp1, ra1 = min(float(sat["PERIGEE"]), first[0]), min(float(sat["APOGEE"]), first[1])
        out.append({"id": "sat%d" % norad, "name": name, "norad": norad, "intdes": sat["OBJECT_ID"], "launch": sat["LAUNCH_DATE"],
                    "decay": sat["DECAY_DATE"], "color": color, "kind": "orbiter", "note": note,
                    "hist": {"rp0": first[0] + RE, "ra0": first[1] + RE, "rp1": rp1 + RE, "ra1": ra1 + RE, "i": inc}})
        lines.append("%-11s %s to %s: %.0f x %.0f km shrinking to %.0f x %.0f km, %.2f deg" % (
            name, sat["LAUNCH_DATE"], sat["DECAY_DATE"], first[0], first[1], rp1, ra1, inc))
    with open(os.path.join(ROOT, "orbiters.js"), "w") as f:
        f.write("// orbiters.js: Earth-orbiters for Solar System Explorer, drawn as rings around Earth (approximate).\n")
        f.write("// Current objects: CelesTrak GP elements fetched %s (https://celestrak.org). Launch and reentry dates: CelesTrak SATCAT.\n" % stamp)
        f.write("// Historical first orbits: NSSDCA (Skylab) or memory, see earth-orbiters.md. Distances in km, angles in degrees,\n")
        f.write("// mean motion n in rad/day (ndot: TLE convention, half the rate of change), epoch in TDB Julian days.\n")
        f.write("// Generated by tools/make_orbiters.py. Do not edit by hand.\n")
        f.write("window.SOLAR_DATA = window.SOLAR_DATA || {};\n")
        f.write("window.SOLAR_DATA.orbiters = %s;\n" % json.dumps(out, indent=0))
    with open(os.path.join(ROOT, "tools", "orbiters-report.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---- the page's math for a current orbiter, mirrored here so it can be checked against Horizons ----
def orbiter_pos(c, t):
    """Geocentric position (km, ecliptic J2000) at TDB Julian day t: Kepler + J2 secular drift of node,
    perigee, and mean anomaly, from the elements' epoch. Equator of date is treated as the J2000 equator."""
    dt = t - c["epoch"]
    n, a, e = c["n"], c["a"], c["e"]
    i = math.radians(c["i"])
    p = a * (1 - e * e)
    k = 1.5 * J2 * (RE / p) ** 2 * n
    raan = math.radians(c["raan"]) - k * math.cos(i) * dt
    argp = math.radians(c["argp"]) + 0.5 * k * (5 * math.cos(i) ** 2 - 1) * dt
    # the published (Kozai) mean motion already includes the bulge's effect on the period: no J2 term here
    M = math.radians(c["M0"]) + n * dt + c["ndot"] * dt * dt
    E = M
    for _ in range(30):
        E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    xo, yo = a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    co, so, cw, sw, ci, si = math.cos(raan), math.sin(raan), math.cos(argp), math.sin(argp), math.cos(i), math.sin(i)
    x = (co * cw - so * sw * ci) * xo + (-co * sw - so * cw * ci) * yo
    y = (so * cw + co * sw * ci) * xo + (-so * sw + co * cw * ci) * yo
    z = (sw * si) * xo + (cw * si) * yo
    eps = math.radians(23.4392811)
    return (x, math.cos(eps) * y + math.sin(eps) * z, -math.sin(eps) * y + math.cos(eps) * z)


if __name__ == "__main__":
    main()
