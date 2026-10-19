# Solar System Explorer

*A navigable 3D model of the solar system at real positions, with a time slider from 1957 to 2035.*

Positions come from NASA JPL's Horizons system, not from guesses or idealized orbits. Distances are true. Sizes are enlarged when you're far away so you can see things, and become true scale when you zoom in close. A sibling project to [UNCHARTED](../uncharted/) and [Star Explorer](../uncharted/starmap-real/), with the same look and camera.

It's one self-contained `index.html` plus sibling data files. No build step for the page, no framework, no server.

**Status: in development.** The Sun, the 8 planets, 21 moons, 5 dwarf planets, 9 visited asteroids and comets, and 40 spacecraft, from Sputnik's launch (1957-10-04) through 2035. Behind it all is the real naked-eye sky. Still to come: the Earth-orbiters. The full object list is in [`objects.md`](objects.md) and the plan is in [`PLAN.md`](PLAN.md).

## Run it

Open **`index.html`**: double-click it or drag it into a browser. It runs fully offline. Keep `bodies.js`, `moons.js`, `probes.js`, `probes-rebuilt.js`, and `sky.js` next to it. It opens on today's date.

## Controls

| | |
|---|---|
| **Drag** | look around |
| **Scroll / PgUp, PgDn** | zoom |
| **Click** an object or its label | fly there; the camera then follows it as time moves |
| **Right-click**, or **long-press** on a touch screen | inspect it in the panel without flying |
| **Search** | find any object by name (arrow keys, Enter, Esc) |
| **◎ SUN** | fly to the Sun |
| **⤢ RESET** | fly back to the opening overview |
| **◀ ❚❚ ▶** | play backward, pause, play forward (space bar toggles play) |
| **Speed chips** | 1 hour, 1 day, 1 week, 1 month, or 1 year per second |
| **NOW** | jump to today |
| **Show** panel | turn planets, moons, dwarf planets, asteroids and comets, or spacecraft on and off |

Leave it untouched for a couple of minutes and the view begins, very slowly, to turn.

## What you see

- **Scale.** Distances are always true. Each body is drawn at whichever is larger: its true size, or a minimum size on screen (4 to 16 pixels across, larger for bigger bodies). Far out, everything is enlarged enough to see. Zoomed in, bodies reach true scale, so a probe flying past a planet is shown where it really was relative to that planet. The badge under the title says which you're seeing for the body you're focused on: "Sizes enlarged" or "True scale." Spacecraft are fixed-size markers at any zoom.
- **The sky** behind everything is the real one: the 8,713 stars of magnitude 6.5 or brighter (everything visible to the naked eye), in their true directions and colors, so constellations are where they belong. The stars sit at infinity, so they never shift as you move, and they aren't labeled or clickable.
- **Moons** are hidden while they would sit inside their planet's enlarged disc, and appear as you zoom in.
- **Orbit lines** show each planet's, dwarf planet's, small body's, and moon's current orbit, drawn through its exact position. A moon's orbit appears once it's big enough on screen to read.
- **Spacecraft trails.** The craft you've selected or are following shows its full path so far. Every other craft shows a faint tail covering its last year.
- **Predictions.** Horizons continues many spacecraft past today (for example Voyager 1 to 2035). Positions after the date the data was built (2026-10-18) are predictions: the card says "Predicted position," the time bar says so, and that part of a trail is dashed.
- **Rebuilt probes.** Six early probes aren't in Horizons: Luna 1, Mariner 4, Mariner 10, Viking 1 and 2, and Giotto. Their paths are rebuilt from their dated mission events (see `probe-events.md`): coasting orbit legs that arrive at each target body's real position on the documented date, joined by curved passes at the documented closest distances. They're exact at each encounter and approximate in between, and their cards say "Reconstructed." The Vikings orbit Mars on ellipses of the published sizes, but the orbits' orientation isn't published, so it's approximate.
- **Where tracking ends.** A craft disappears at the end of its data. When the end is an event, the card says so: entering Jupiter (Galileo) or Saturn (Cassini), crashing into Mercury (MESSENGER), landing (Curiosity, Perseverance, NEAR on Eros, Rosetta on its comet), or DART's impact.

## Data and accuracy

**Sources.** Positions, masses, and most radii: JPL Horizons (https://ssd.jpl.nasa.gov/horizons/), state vectors (position and velocity), ecliptic J2000, retrieved 2026-10-18. Small-body radii and masses Horizons lacks: JPL's Small-Body Database. Launch dates: CelesTrak's satellite catalog. Four radii neither source has (Haumea, Makemake, Eris, Arrokoth) are published values cited in `tools/catalog.py`.

**How positions are stored.** Each object stores a set of position-and-velocity snapshots. Between two snapshots, the page runs a two-body orbit forward from each one and blends the two results smoothly. Moons are stored relative to their planet. Spacecraft are stored relative to the Sun in cruise, and relative to a body when near it: inside a planet's sphere of influence (twice that for Earth, to cover craft at the L1 and L2 points), or within 150,000 km of a dwarf planet or small body. That makes a flyby one clean hyperbola instead of hundreds of samples. The data scripts choose the snapshots automatically against a dense Horizons grid: daily for planets and spacecraft in cruise, every eighth of an orbit for moons, hourly or finer near a body, and every 5 minutes around each fast close pass.

**Tolerances** (as a share of the distance from the body an object is near):

- Planets and dwarf planets: 0.0001% (for example about 150 km for Earth and Mars, 750 km for Jupiter). Earth's center wobbles about 4,700 km every month around the Earth-Moon center of mass, so following it at this tolerance means storing Earth daily (about 3 MB). A looser Earth let its error leak into craft passing near it.
- Asteroids and comets: 0.001%.
- Moons: 1% of their distance from their planet. Approximate is fine for moons, and 0.1% would have taken about ten times the data.
- Spacecraft: 0.1% of their distance from the body they're near, or 1% near a dwarf planet or small body (Dawn at Vesta and Ceres, Rosetta, NEAR, Hayabusa2, OSIRIS-REx, DART, Hera). Never tighter than 0.5 km.

**Measured accuracy.** `tools/validate.py` compares the stored data with fresh Horizons positions at random times never used in the build: 200 per object, plus 60 inside each window near a body and 10 around each of up to 25 close passes per craft. Every object passes except, in the latest run, one sample of Apollo 8 behind the Moon (1.28 times tolerance). Which marginal sample shows up depends on the random draw; an earlier run caught one of Hera's instead. Both cases are explained under Known limits. Results are in [`tools/accuracy-report.txt`](tools/accuracy-report.txt). The page's own math is checked against the Python by `tools/check_js.mjs`: across 342,000 samples they agree to within a few millimeters.

**Known limits.**

- **Older planet positions in mission tracks.** Some spacecraft trajectories in Horizons were reconstructed against older planet positions than the ones Horizons now uses for the planets themselves. At the Voyager flybys the two disagree by up to about 13,600 km (at Neptune). This app keeps each probe's position relative to the body it's passing, which is what you see up close.
- **Hayabusa2 at Ryugu.** Horizons can't center on Ryugu, so Hayabusa2 is placed there by subtracting the two heliocentric positions. Horizons' Ryugu and Hayabusa2 solutions disagree by about 15 to 20 km, which its card notes.
- **Moon flybys.** Probes are never stored relative to moons, so Cassini's Titan flybys and the Apollo passes behind the Moon are only as accurate as the tolerance relative to the planet (about 400 km for Apollo at the Moon). Tracking craft relative to the Moon was tried and reverted: the Moon itself is stored only to about 3,800 km (1%), and that error leaked into every craft tracked against it.
- **Jumps in Horizons' own tracks.** A few spacecraft tracks in Horizons jump in position between two samples, which no smooth path can follow. The largest is Psyche on 2027-02-01, a jump of about 1.6 million km in Horizons' predicted track. The build lists them in `tools/build-report.txt`, and the validator skips samples inside them.
- **Engine burns between samples.** Near a planet or small body the build samples hourly or finer, so a burn between samples is smoothed over. The one case the validator catches is Hera's predicted braking burn at Didymos on 2026-10-28: for the hour before it, Hera is drawn up to about 2 km off at 120 km from Didymos.
- **Times** are in TDB, the time scale Horizons uses, which runs about a minute ahead of UTC. The date readout shows TDB as-is.

**Data size.** About 20 MB of data files: bodies.js 5 MB (mostly Earth), moons.js 9 MB (mostly the fast inner moons Mimas, Enceladus, and Phobos), probes.js 6 MB (mostly Dawn's years circling Ceres).

## Rebuilding the data

The scripts use only Python's standard library. Downloads and fits are cached in `~/Library/Caches/solar-explorer/` (outside the project folder, because the cache grows to about 3 GB). A rebuild from a warm cache takes minutes; the first build took several hours, mostly downloads.

```
python3 tools/build.py       # fetch, choose snapshots, write bodies.js, moons.js, probes.js
python3 tools/reconstruct.py # rebuild the six probes Horizons lacks, write probes-rebuilt.js (run after build.py)
python3 tools/make_sky.py    # write sky.js from Star Explorer's stars.js (expects ../uncharted/starmap-real/stars.js)
python3 tools/validate.py    # check against held-out Horizons samples (exit code 1 on failure)
node tools/check_js.mjs      # check the page's math against the Python
```

## Project layout

```
index.html        the entire app (single self-contained file, three.js r136 inline)
bodies.js         Sun, planets, dwarf planets, asteroids and comets (generated)
moons.js          moons, relative to their planets (generated)
probes.js         spacecraft (generated)
probes-rebuilt.js probes Horizons doesn't have, rebuilt from mission dates (generated)
sky.js            naked-eye stars for the backdrop (generated; CC BY-SA 4.0, from HYG v3)
tools/
  catalog.py      every object: Horizons IDs, names, colors, special cases
  orbit.py        two-body propagation and the evaluator (mirrors the page's math)
  horizons.py     Horizons, SBDB, and CelesTrak access with a local cache
  build.py        builds the data files
  validate.py     accuracy check against held-out samples
  check_js.mjs    page-vs-Python math check
  make_sky.py     builds sky.js
  reconstruct.py  rebuilds the six missing probes; reconstruct-report.txt has its physics checks
  build-report.txt, build-meta.json, accuracy-report.txt
objects.md        the full object list with Horizons IDs and coverage
probe-events.md   dated mission events and sources for the rebuilt probes
PLAN.md           the plan
LICENSE           proprietary code + third-party data credits
```

## Credits

- **JPL Horizons**, Solar System Dynamics Group, NASA/JPL-Caltech: positions, masses, and radii.
- **JPL Small-Body Database**: small-body radii and masses.
- **CelesTrak** satellite catalog: launch dates.
- **NASA NSSDCA** and NASA mission pages: the mission events behind the rebuilt probes (cited in `probe-events.md`).
- **HYG Database v3**, David Nash / astronexus, CC BY-SA 4.0: the backdrop stars (`sky.js` is a derivative and is likewise CC BY-SA 4.0).
- **NASA Saturnian Rings Fact Sheet**: ring radii.
- **IAU WGCCRE 2015 report**: Saturn's pole orientation.
- **three.js** r136, MIT, vendored inline.

## License

Proprietary. © 2026 John Terhorst. All Rights Reserved. See [`LICENSE`](LICENSE). The backdrop star data (`sky.js`) remains under **CC BY-SA 4.0** and may be reused under those terms with attribution to the HYG Database.
