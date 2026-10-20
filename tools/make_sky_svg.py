"""Render a static snapshot of the real naked-eye sky (Solar's sky.js, HYG v3) as an SVG background.

Perspective (gnomonic) projection, like a camera: celestial north up, east to the left, as the sky looks from
Earth. Star colors use the website's spectral-class palette (DESIGN-SYSTEM.md), picked by each star's B-V index;
size and opacity follow magnitude, kept dim so it reads as depth behind text.

Usage: python3 make_sky_svg.py <sky.js> <out.svg> <RA hours> <Dec degrees> <horizontal FOV degrees>
"""
import math
import re
import sys

W, H = 2560, 1600
OBLIQ = math.radians(23.4392811)
# website DESIGN-SYSTEM.md stellar palette, by B-V (O, B, A, F, G, K, M)
PALETTE = [(-0.30, "#9bb0ff"), (-0.02, "#aabfff"), (0.30, "#cfd9ff"), (0.58, "#f6f4ff"), (0.81, "#fff2dd"), (1.40, "#ffc070"), (9.0, "#ff9d5c")]


def color(bv):
    for lim, c in PALETTE:
        if bv < lim:
            return c
    return PALETTE[-1][1]


def main():
    src, out, ra_h, dec_d, hfov = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
    v = [float(x) for x in re.search(r"\[(.*)\]", open(src).read()).group(1).split(",")]
    stars = [v[i:i + 5] for i in range(0, len(v), 5)]   # x, y, z (ecliptic J2000), mag, B-V
    # center and celestial-north directions, equatorial -> ecliptic
    def eq2ecl(x, y, z):
        return (x, math.cos(OBLIQ) * y + math.sin(OBLIQ) * z, -math.sin(OBLIQ) * y + math.cos(OBLIQ) * z)
    ra, dec = math.radians(ra_h * 15), math.radians(dec_d)
    c = eq2ecl(math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))
    ncp = eq2ecl(0.0, 0.0, 1.0)
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    unit = lambda a: tuple(x / math.sqrt(dot(a, a)) for x in a)
    east = unit(cross(ncp, c))
    north = cross(c, east)
    f = (W / 2) / math.tan(math.radians(hfov) / 2)
    circles = []
    shown = 0
    for x, y, z, mag, bv in sorted(stars, key=lambda s: -s[3]):   # faint first, bright on top
        s = (x, y, z)
        d = dot(s, c)
        if d <= 0.05:
            continue
        px = W / 2 - f * dot(s, east) / d     # east to the left
        py = H / 2 - f * dot(s, north) / d    # north up
        if not (-20 <= px <= W + 20 and -20 <= py <= H + 20):
            continue
        r = 0.9 + max(0.0, 5.5 - mag) * 0.45
        op = min(0.85, 0.22 + (6.5 - mag) * 0.085)
        col = color(bv)
        if mag < 1.5:   # a soft halo for the brightest
            circles.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#halo)" opacity="%.2f" style="color:%s"/>' % (px, py, r * 4.5, op * 0.5, col))
        circles.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="%s" opacity="%.2f"/>' % (px, py, r, col, op))
        shown += 1
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid slice">\n'
           '<!-- The real naked-eye sky (stars to magnitude 6.5) around RA %.1fh, Dec %+.0f deg, %d deg wide.\n'
           '     Stars: HYG Database v3, David Nash / astronexus, CC BY-SA 4.0 (https://github.com/astronexus/HYG-Database).\n'
           '     This image is a derivative and is likewise CC BY-SA 4.0. -->\n'
           '<defs><radialGradient id="halo"><stop offset="0" stop-color="currentColor" stop-opacity="0.6"/>'
           '<stop offset="1" stop-color="currentColor" stop-opacity="0"/></radialGradient></defs>\n%s\n</svg>\n') % (
        W, H, ra_h, dec_d, hfov, "\n".join(circles))
    open(out, "w").write(svg)
    print("%d stars in view; %s, %.0f KB" % (shown, out, len(svg) / 1024))


if __name__ == "__main__":
    main()
