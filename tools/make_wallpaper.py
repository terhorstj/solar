"""Render a two-monitor desktop wallpaper of the real sky: one wide view split into a left and a right image.

Same look as the website snapshots (make_sky_svg.py): the site's spectral-class palette by B-V, size and
opacity by magnitude, on the site's near-black. One continuous stereographic projection spans both screens
plus the bezel gap between them, so a constellation that crosses the seam stays straight across the
physical gap. Stereographic rather than gnomonic because the view is ~150 degrees wide: gnomonic stretches
the edges badly past about 100 degrees.

Stars come from Star Explorer's stars.js (HYG v3, CC BY-SA 4.0), which goes fainter than Solar's sky.js.
Writes <out>-left.svg and <out>-right.svg, then <out>-left.png and <out>-right.png via headless Chrome.

Usage: python3 make_wallpaper.py <stars.js> <out prefix> <RA hours> <Dec deg> [--hfov 150] [--gap 218]
       [--mag 7.0] [--size 5120x2880] [--svg-only]
"""
import argparse
import json
import math
import os
import subprocess
import tempfile

PALETTE = [(-0.30, "#9bb0ff"), (-0.02, "#aabfff"), (0.30, "#cfd9ff"), (0.58, "#f6f4ff"), (0.81, "#fff2dd"), (1.40, "#ffc070"), (9.0, "#ff9d5c")]
BG = "#02040a"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def color(bv):
    for lim, c in PALETTE:
        if bv < lim:
            return c
    return PALETTE[-1][1]


def load_hyg(path):
    text = open(path).read()
    cols = json.loads(text.split("window.HYG_COLS=", 1)[1].split(";", 1)[0].replace("'", '"'))
    body = text.split("window.HYG_STARS=", 1)[1].strip().rstrip(";")
    return cols, json.loads(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("ra", type=float)
    ap.add_argument("dec", type=float)
    ap.add_argument("--hfov", type=float, default=150.0, help="degrees across both screens and the gap")
    ap.add_argument("--gap", type=int, default=218, help="pixels hidden behind the bezels between the screens")
    ap.add_argument("--mag", type=float, default=7.0)
    ap.add_argument("--size", default="5120x2880")
    ap.add_argument("--scale", type=float, default=2.0, help="star size multiplier (2 = the website's look on a Retina screen)")
    ap.add_argument("--svg-only", action="store_true")
    a = ap.parse_args()
    W, H = (int(v) for v in a.size.split("x"))
    WT = 2 * W + a.gap

    dot = lambda p, q: p[0] * q[0] + p[1] * q[1] + p[2] * q[2]
    cross = lambda p, q: (p[1] * q[2] - p[2] * q[1], p[2] * q[0] - p[0] * q[2], p[0] * q[1] - p[1] * q[0])
    unit = lambda p: tuple(v / math.sqrt(dot(p, p)) for v in p)
    ra, dec = math.radians(a.ra * 15), math.radians(a.dec)
    c = (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))
    east = unit(cross((0.0, 0.0, 1.0), c))
    north = cross(c, east)
    f = (WT / 2) / (2 * math.tan(math.radians(a.hfov) / 4))   # stereographic: r = 2 f tan(theta / 2)

    cols, rows = load_hyg(a.src)
    ci = {k: i for i, k in enumerate(cols)}
    screens = {"left": [], "right": []}
    named = []
    for r in sorted(rows, key=lambda r: -r[ci["mag"]]):   # faint first, bright on top
        mag = r[ci["mag"]]
        if r[ci["id"]] == 0 or mag > a.mag:
            continue
        s = unit((r[ci["x"]], r[ci["y"]], r[ci["z"]]))
        cosd = dot(s, c)
        if cosd <= -0.5:
            continue
        k = 2 * f / (1 + cosd)
        x = WT / 2 - k * dot(s, east)    # east to the left, as the sky looks from Earth
        y = H / 2 - k * dot(s, north)
        if not -30 <= y <= H + 30:
            continue
        bv = r[ci["ci"]] if r[ci["ci"]] not in ("", None) else 0.65
        rad = (0.9 + max(0.0, 5.5 - mag) * 0.45) * a.scale
        op = max(0.12, min(0.85, 0.22 + (6.5 - mag) * 0.085))
        col = color(bv)
        for name, x0 in (("left", 0), ("right", W + a.gap)):
            px = x - x0
            if -30 <= px <= W + 30:
                if mag < 1.5:
                    screens[name].append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#halo)" opacity="%.2f" style="color:%s"/>' % (px, y, rad * 4.5, op * 0.5, col))
                screens[name].append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="%s" opacity="%.2f"/>' % (px, y, rad, col, op))
                if mag < 2.0 and r[ci["proper"]]:
                    named.append((mag, r[ci["proper"]], name, px, y))

    for mag, name, scr, px, y in sorted(named):
        print("  %-12s mag %5.2f  %-5s  x %5.0f  y %5.0f" % (name, mag, scr, px, y))
    paths = []
    for name, circles in screens.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
               '<!-- The real sky around RA %.1fh, Dec %+.0f deg (%s screen of a %d-degree two-screen view), stars to magnitude %.1f.\n'
               '     Stars: HYG Database v3, David Nash / astronexus, CC BY-SA 4.0 (https://github.com/astronexus/HYG-Database).\n'
               '     This image is a derivative and is likewise CC BY-SA 4.0. -->\n'
               '<defs><radialGradient id="halo"><stop offset="0" stop-color="currentColor" stop-opacity="0.6"/>'
               '<stop offset="1" stop-color="currentColor" stop-opacity="0"/></radialGradient></defs>\n'
               '<rect width="100%%" height="100%%" fill="%s"/>\n%s\n</svg>\n') % (W, H, W, H, a.ra, a.dec, name, a.hfov, a.mag, BG, "\n".join(circles))
        p = "%s-%s.svg" % (a.out, name)
        open(p, "w").write(svg)
        paths.append(p)
        print("%s: %d stars" % (p, len(circles)))
    if a.svg_only:
        return
    for p in paths:
        png = p[:-4] + ".png"
        with tempfile.TemporaryDirectory() as prof:
            subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
                            "--window-size=%d,%d" % (W, H), "--user-data-dir=" + prof, "--screenshot=" + os.path.abspath(png),
                            "file://" + os.path.abspath(p)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        print("%s: %.1f MB" % (png, os.path.getsize(png) / 1e6))


if __name__ == "__main__":
    main()
