"""JPL Horizons, JPL SBDB, and CelesTrak SATCAT access, with a local cache so reruns don't refetch.

Vectors are heliocentric (Sun body center) or body-centered, ecliptic J2000 (ICRF), in AU
and AU/day, with times in TDB Julian days.

The cache lives outside the project folder (it grows to hundreds of MB):
~/Library/Caches/solar-explorer/, or $SOLAR_CACHE if set.
"""
import hashlib
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

API = "https://ssd.jpl.nasa.gov/api/horizons.api"
SBDB = "https://ssd-api.jpl.nasa.gov/sbdb.api"
SATCAT = "https://celestrak.org/satcat/records.php"
CACHE = os.environ.get("SOLAR_CACHE") or os.path.expanduser("~/Library/Caches/solar-explorer")
MAX_STEPS = 40000   # Horizons caps a single response; longer grids are split into chunks


def _get_json(url, params):
    os.makedirs(CACHE, exist_ok=True)
    if url == API:   # key format kept from the first version, so existing cached responses still hit
        key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:20]
    else:
        key = hashlib.sha1((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:24]
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(full, timeout=180) as r:
                d = json.loads(r.read().decode())
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(4 * (attempt + 1))
    time.sleep(0.2)  # be polite
    with open(path, "w") as f:
        json.dump(d, f)
    return d


def _get(params):
    return _get_json(API, params)


def _q(s):
    return "'" + s + "'"


def _vec_params(command, center):
    return {
        "format": "json", "COMMAND": _q(command), "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS", "CENTER": _q(center), "REF_PLANE": "ECLIPTIC", "REF_SYSTEM": "ICRF",
        "OUT_UNITS": "AU-D", "VEC_TABLE": "2", "CSV_FORMAT": "YES", "VEC_LABELS": "NO",
    }


def vectors(command, center, start, stop, step):
    """One grid request. start/stop are 'JD...' or calendar strings; step like '1 d', '1 h', '5 m'."""
    p = _vec_params(command, center)
    p.update({"START_TIME": _q(start), "STOP_TIME": _q(stop), "STEP_SIZE": _q(step)})
    return parse_vectors(_get(p))


def grid(command, center, jd0, jd1, step_min):
    """State vectors every step_min minutes from jd0 to jd1 (TDB), split into chunks Horizons accepts."""
    span = step_min / 1440.0 * MAX_STEPS
    out, a = [], jd0
    while a < jd1 - 1e-9:
        b = min(a + span, jd1)
        rows = vectors(command, center, "JD%.6f" % a, "JD%.6f" % b, "%d m" % step_min)
        if out and rows and abs(rows[0][0] - out[-1][0]) < 1e-7:
            rows = rows[1:]
        out.extend(rows)
        a = b
    return out


def vectors_at(command, center, jds):
    """State vectors at a list of TDB Julian days (TLIST), in chunks."""
    out = []
    for i in range(0, len(jds), 60):
        chunk = jds[i:i + 60]
        p = _vec_params(command, center)
        p.update({"TLIST_TYPE": "JD", "TIME_TYPE": "TDB", "TLIST": " ".join("%.6f" % j for j in chunk)})
        out.extend(parse_vectors(_get(p)))
    return out


def parse_vectors(d):
    text = d.get("result", "")
    if "$$SOE" not in text:
        raise RuntimeError("Horizons returned no ephemeris:\n" + (d.get("error") or text[-1500:]))
    body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = []
    for line in body.strip().splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) < 8:
            continue
        rows.append((float(f[0]), (float(f[2]), float(f[3]), float(f[4])), (float(f[5]), float(f[6]), float(f[7]))))
    return rows


def coverage(command):
    """(start, stop) calendar strings of a spacecraft's Horizons coverage inside 1957-2035; None = covered."""
    out = []
    for a, b in (("1957-10-04", "1957-10-05"), ("2035-12-30", "2035-12-31")):
        p = _vec_params(command, "500@10")
        p.update({"START_TIME": _q(a), "STOP_TIME": _q(b), "STEP_SIZE": _q("1 d")})
        d = _get(p)
        text = d.get("result", "") + (d.get("error") or "")
        m = re.search(r"(?:prior to|after) A\.D\. (\d{4}-[A-Z]{3}-\d{2} \d{2}:\d{2}:\d{2})", text)
        out.append(m.group(1) if m else None)
    return out


_NUM = r"((?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)"


def physical(command):
    """GM (km^3/s^2) and mean radius (km) parsed from the Horizons object-data header (None if absent)."""
    d = _get({"format": "json", "COMMAND": _q(command), "OBJ_DATA": "YES", "MAKE_EPHEM": "NO"})
    text = d.get("result", "")
    gm = None
    for pat in (r"GM[ ,]*\(?km\^?3/s\^?2\)?\s*=\s*" + _NUM, r"GM, km\^3 s\^-2\s*=\s*" + _NUM,
                r"GM \(planet\) km\^3/s\^2\s*=\s*" + _NUM, r"GM \(km\^3/s\^2\)\s*=\s*" + _NUM, r"\bGM=\s*" + _NUM):
        m = re.search(pat, text)
        if m:
            gm = float(m.group(1))
            break
    rad = None
    m = re.search(r"Radius \(km[^=\n]*=\s*" + _NUM + r"\s*x\s*" + _NUM + r"\s*x\s*" + _NUM, text)
    if m:   # triaxial: volume-equivalent radius
        rad = (float(m.group(1)) * float(m.group(2)) * float(m.group(3))) ** (1.0 / 3.0)
    else:
        for pat in (r"[Vv]ol\.? [Mm]ean [Rr]adius[^=\n]*=\s*" + _NUM, r"[Mm]ean [Rr]adius[^=\n]*=\s*" + _NUM,
                    r"\bRadius \(km[^=\n]*=\s*" + _NUM, r"\bRAD=\s*" + _NUM):
            m = re.search(pat, text)
            if m:
                rad = float(m.group(1))
                break
    return gm, rad, text


def sbdb_phys(designation):
    """Radius (km), GM (km^3/s^2), and the radius reference from JPL's Small-Body Database (None where absent)."""
    d = _get_json(SBDB, {"sstr": designation, "phys-par": "1"})
    rad = gm = ref = None
    for p in d.get("phys_par", []):
        if p.get("name") == "diameter" and p.get("value"):
            rad, ref = float(p["value"]) / 2.0, "JPL SBDB: " + (p.get("ref") or "")
        if p.get("name") == "GM" and p.get("value"):
            gm = float(p["value"])
    return rad, gm, ref


_MB = None


def intl_designator(hid):
    """International designator (e.g. 1977-084A) for a Horizons spacecraft ID, from Horizons' body list."""
    global _MB
    if _MB is None:
        _MB = _get({"format": "json", "COMMAND": _q("MB")}).get("result", "")
    for line in _MB.splitlines():
        f = line.split()
        if f and f[0] == hid:
            m = re.search(r"(\d{4}-\d{3}[A-Z]{1,3})\b", line)   # long names run straight into this column
            return m.group(1) if m else None
    return None


def launch_date(intdes):
    """Launch date (YYYY-MM-DD) from CelesTrak's satellite catalog, by international designator."""
    if not intdes:
        return None
    try:   # by launch number: every object from one launch shares its launch date
        d = _get_json(SATCAT, {"INTDES": intdes[:8], "FORMAT": "json"})
    except Exception:
        return None   # CelesTrak sometimes answers with plain text instead of JSON; the card then shows no launch date
    return d[0]["LAUNCH_DATE"] if isinstance(d, list) and d else None
