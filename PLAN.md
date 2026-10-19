# Solar System Explorer: plan (draft for John to confirm)

Inputs: `solar-system-explorer-seed.md`, `objects.md`, and the answers from 2026-10-18 (own folder, hosted under uncharted.sqnp.org, real-sky backdrop).

## 1. Data pipeline

Python data-prep scripts in `tools/`, using only the standard library. They write plain `.js` data files next to `index.html`. They aren't part of the page, and the page never calls an API.

- **fetch_horizons.py** pulls state vectors (position and velocity) for every Horizons object in `objects.md`. It saves the raw responses to a local cache, so reruns don't hit JPL again.
- **reconstruct.py** builds the six missing probes. For each leg between dated events it solves a two-body transfer, using Horizons planet positions on those dates. It outputs states in the same format as Horizons data. Event dates come from NSSDCA and are cited in the data file.
- **Storage format:** each object is a list of stored states (time, position, velocity). The page finds the nearest stored state and propagates a simple Kepler orbit from it around the parent body (the Sun, or the planet for moons). That makes smooth orbits very cheap to store: monthly states are plenty for planets. Spacecraft get dense states near flybys and maneuvers, and sparse ones during cruise.
- **Adaptive sampling:** the script picks each object's spacing automatically. It keeps adding states until held-out Horizons samples (ones not stored) are reproduced within tolerance. The proposed tolerance is 0.1% of the distance from the parent body. The pass/fail report is saved, so accuracy is measured rather than judged by eye.
- **Frame and units:** heliocentric, ecliptic J2000, in AU. Moons are stored relative to their planet.
- **Spot checks before shipping:** Earth at about 1 AU, Jupiter at about 5.2 AU, and Voyager 1's distance against NASA's published figure for a recent date.
- **Estimated size:** a few MB total across the data files.
- **Earth-orbiters:** **fetch_celestrak.py** saves current elements for the six live satellites. The four historical ones use typical orbit values from NSSDCA.
- **Sky backdrop:** **make_sky.py** takes the brightest stars from Star Explorer's `stars.js`, roughly 5,000 with magnitude 6 or brighter. It keeps only their direction, color, and brightness, rotated into the ecliptic frame. `stars.js` is CC BY-SA, so this file is too, credited in the README.

## 2. Scene structure

- **Precision (built in from day one):** positions are computed in 64-bit on the CPU. Each frame, the focused object becomes the origin and everything else is placed relative to it before going to the GPU. This keeps nearby objects from jittering at solar-system distances.
- **Up is ecliptic north.** The reference grid lies on the ecliptic plane, with distance rings labeled in AU (adapted from Star Explorer's grid).
- **Sun and planets:** shaded spheres lit from the Sun. Saturn gets a ring.
- **Spacecraft:** markers that stay the same size on screen at any zoom, as decided.
- **Earth-orbiters:** each satellite is a ring around Earth, tilted from Earth's equator into the ecliptic frame. A live marker shows only within a few days of its element date, near "now." Ring orientation is approximate and labeled so.
- **Sky:** a star sphere drawn at infinity, so it never shifts as you move. It isn't labeled or clickable.

## 3. Scale rule

The problem: if distances are true and planets are drawn bigger, inner moons and low Earth-orbiters end up inside their planets.

The proposed fix:

- **Minimum on-screen size.** Each planet, moon, and the Sun is drawn at whichever is larger: its true size or a minimum size on screen (about 8 to 12 px). Zoomed out, they're enlarged enough to see. Zoomed in close, they shrink to true scale, so Phobos, Mimas, and the ISS ring all sit where they really are, outside the planet.
- **Hide hidden moons.** In between, a moon whose true position falls inside its planet's enlarged disc is hidden, and so is its label.
- **Scale badge.** A small badge reads "Sizes enlarged" or "True scale," depending on the focused object. That covers the seed's requirement to say plainly that sizes aren't to scale.

This replaces a fixed exaggeration factor, which would have to be wrong somewhere: big enough to see Mercury from far out means Jupiter swallows Io up close.

## 4. Time slider

- **Layout:** a bottom bar with a UTC date readout and a slider from 1957-10-04 (Sputnik) to 2035-12-31.
- **Controls:** a NOW button, and play/pause (also on the space bar). Speeds are 1 hour, 1 day, 1 week, 1 month, or 1 year per second, forward or reverse.
- **Spans:** each object appears only within its time span from `objects.md`.
- **Labels:** a probe past its last real data shows "prediction," and the six rebuilt probes show "reconstructed."
- **Later, not v1:** event markers on the slider (launches, flybys, arrivals).

## 5. Behaviors carried over from Star Explorer

My recommendation for each is below. Confirm or change any of them.

| Behavior | Recommendation |
|---|---|
| Theme: colors, monospace type, translucent panels | Keep |
| Orbit camera: drag to look, scroll and PgUp/PgDn to zoom, smooth damping | Keep |
| Glide travel: 1.1 s eased flight that keeps your viewing direction | Keep |
| Left-click to fly there, right-click to inspect, with a 4 px drag-vs-click threshold | Keep. Add long-press to inspect for iPad |
| Picking by the dot you actually see on screen | Keep |
| Hover tooltip | Keep. Add a tap equivalent for iPad |
| Info panel card with a facts table | Keep. Facts change to distance from Sun and Earth, speed, launch date, mission status |
| Labels: priority tiers, grid de-cluttering, nearer ones drawn on top, clickable | Keep |
| Spinning selection reticle | Keep |
| Search box with arrow keys, Enter, and Esc | Keep |
| Home (SOL) and RESET VIEW buttons | Keep |
| Idle drift: slow camera turn after 2.5 minutes untouched | Keep |
| Reference-plane grid with labeled rings | Keep, as an ecliptic grid in AU |
| "You are here" ship marker, bearing line, LOOK / LOOK BACK | Drop. There's no travel concept here, and the camera simply follows what you focus on |
| Naming, descriptions, favorites, Export | Drop for v1 |
| Survey rankings, collections, guided tours | Drop for v1. Tours could come back later as probe stories |
| Spectral filter legend | Replace with category toggles (planets, moons, dwarf planets, small bodies, probes, Earth-orbiters) |

## 6. Additions the seed doesn't call for

Each of these needs your yes before it gets built:

1. **Camera follows its focus as time plays.** Without this, Jupiter drifts out of frame on its own. Recommended.
2. **Orbit lines** for planets, dwarf planets, and moons, drawn faintly. Recommended.
3. **Probe trails:** a solid line for the path so far, and a dashed line for the predicted future. Recommended.
4. **Category toggles** (from the table above).
5. **A proprietary LICENSE** matching UNCHARTED and Star Explorer, plus the third-party data credits.

## 7. Layout and hosting

```
solar/
  index.html        the whole app (three.js r136, OrbitControls, satellite.js inline)
  bodies.js         Sun, planets, moons, dwarf planets, small bodies
  probes.js         deep-space probes, Lagrange-point craft, Apollo
  orbiters.js       Earth-orbiter elements and orbit values
  sky.js            backdrop stars (CC BY-SA, from HYG v3)
  tools/            data-prep scripts and the saved accuracy report
  objects.md, PLAN.md, README.md
```

**Hosting:** the site goes at a path under uncharted.sqnp.org, for example `/solar/`. UNCHARTED's deploy script won't cover a separate folder, so this needs its own small deploy script, modeled on UNCHARTED's. You'd run it. That comes after the prototype.

**Git:** the folder isn't a repo yet. You'll want to `git init` before code arrives. I won't commit anything unless you ask.

## 8. First prototype

**Scope:** the Sun, eight planets, Voyager 1 and Voyager 2, from 1977 to 1990.

**It proves out:** the pipeline end to end (fetch, adaptive sampling, accuracy report), the precision handling, the scale rule, glide travel, labels, the info card, and the time slider.

**Not yet:** moons, the sky, Earth-orbiters, and the rebuilt probes come after you've looked at the prototype on screen.

## 9. Next phase (agreed 2026-10-18, after the prototype was reviewed)

Each step ends in something to look at before the next starts.

1. **Every Horizons object, full range 1957 to 2035.** Planets over the full span, the 23 moons, dwarf planets, visited small bodies, the other 26 probes, JWST, SOHO, Kepler, Spitzer, and Apollo 8 and 11. Moons are stored relative to their planet at 0.1% of their distance from it, since approximate positions are fine. A moon whose true position falls inside its planet's enlarged disc is hidden, along with its label. Probe spans that run past today are labeled "prediction" and drawn dashed. The show panel gets toggles for each new group.
2. **Real-sky backdrop** from Star Explorer's catalog.
3. **The six rebuilt probes.** First a table of mission dates from NASA NSSDCA with links, for John to check, then the build.
4. **Earth-orbiters.** Current CelesTrak elements with satellite.js, plus NSSDCA orbit values for the four historical ones (also a table for John to check first).
5. **Deploy script** for the path under uncharted.sqnp.org, modeled on UNCHARTED's. Kept out of git, like UNCHARTED's. John runs it.

**Trails** (a change from section 6): the selected probe shows its full trail; every other probe shows a short faint tail covering roughly its last year.
