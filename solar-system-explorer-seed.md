# Seed: Solar System Explorer

Instructions for starting a new project in its own folder. Read all of this before doing anything, then follow "First session" at the end. Nothing has been built yet; this file records an idea and the decisions made so far.

## The idea

A navigable 3D model of the solar system that shows the planets, major moons, and the major human-made objects at their real positions, with a time slider to watch them move. Positions come from real ephemeris data, not guesses.

It's a hobby project and a sibling to two existing ones, matching their theme and camera navigation:

- **UNCHARTED**, a procedural 3D galaxy you can fly through: `/usr/local/home/claude/uncharted/`
- **Star Explorer** ("osok" / starmap-real), a navigable 3D map of about 109,000 real stars with Sol at the origin: `/usr/local/home/claude/uncharted/starmap-real/`

Star Explorer is the closest model. It is real data, not a game, and it reuses UNCHARTED's rendering, camera, and info-panel backbone. This project should feel like the same family.

## Decided

- **Look and navigation** match UNCHARTED and Star Explorer: their theme, camera movement (glide to an object, drag to look around, scroll to zoom, click to fly there, right-click to inspect), info panel, and label de-cluttering.
- **Separate size and distance scales.** Distances are true. Planet and moon sizes are exaggerated so they're visible. Spacecraft are fixed-size markers that stay visible at any zoom. The UI should say plainly that sizes aren't to scale.
- **A time slider**, with a "now" button and play at selectable speeds.
- **Objects:** the planets, notable moons, a few dwarf planets, deep-space probes, and a hand-picked set of famous Earth-orbiters (the ISS, Hubble, JWST, and similar). Not the full satellite catalog.
- **Format: one self-contained `index.html`, like Star Explorer.** three.js is bundled inside the file, data lives in sibling `.js` files, and there's no build step or server. It runs offline by opening the file. (A separate script that fetches ephemeris data and writes those data files is fine. It's a data-prep tool, not part of the page.)
- **Time range: 1957 (Sputnik) to 2035.**
- **No stars beyond the Sun.** The scene stays within the solar system or just outside it, so there is no star catalog. (Whether to add a faint, purely decorative background for orientation is a small open question below.)

## Not yet decided (ask John at the start)

1. **Object list.** Draft one (planets, notable moons, dwarf planets, roughly 20 to 30 spacecraft, plus the famous Earth-orbiters) and have John edit it before fetching any data.
2. **Where it lives.** Inside the uncharted folder next to starmap-real, or its own top-level project? This also decides whether it shares code by copying or by reference.
3. **Hosting.** Hobby projects go on sqnp.org (Uncharted is at uncharted.sqnp.org). Confirm before planning any deploy. John deploys himself.
4. **Background.** Pure black, or a faint decorative starfield for orientation (not real stars, no labels)? John's site-design rule: if there is a starfield, make it dense enough to read as stars, not dead pixels.

## Technical notes from the planning discussion

- **Ephemeris data: JPL Horizons** (`https://ssd.jpl.nasa.gov/api/horizons.api`), free. It covers the Sun, planets, moons, dwarf planets, and most deep-space spacecraft. Spacecraft use negative IDs (for example Voyager 1 is -31). Look up each ID in Horizons rather than trusting memory. A build script fetches position tables (heliocentric, ecliptic J2000) for each object and writes them to a sibling data file. The page interpolates between samples, so the site stays static with no live API calls.
- **Spacecraft exist only over their mission spans** in Horizons: show each from launch until its data ends. Some, such as the Voyagers, have predicted positions into the future. Label predictions as predictions.
- **Sampling:** daily samples are fine for planets and probes in cruise. Moons and close flybys need finer sampling, or cubic interpolation. Check by comparing interpolated positions against held-out Horizons samples, not by eye.
- **Earth-orbiters (ISS, Hubble) can't come from daily tables:** they orbit in about 90 minutes. Show them as orbit rings around Earth, with a live position near "now" propagated from orbital elements published by CelesTrak (SGP4, for example the satellite.js library). Elements go stale within days, so treat these as approximate and say so in the UI. JWST sits near Sun–Earth L2 and Horizons covers it, so it behaves like the probes.
- **Early Earth-orbiters (Sputnik and others from the 1950s and 1960s)** aren't in Horizons, and current CelesTrak elements don't cover objects that have reentered. Historical orbital elements exist, but some archives need an account, so check what's freely available. Otherwise show these as approximate orbit rings over their known lifetimes, labeled approximate.
- **Precision:** solar-system distances break 32-bit GPU precision, so objects jitter. Use camera-relative rendering (keep positions in 64-bit on the CPU, subtract the camera position before handing them to the GPU) from the start. It's hard to retrofit.
- **Possible later link:** Star Explorer has Sol at its origin, so "zoom into Sol" could hand off to this project. This is for later, not v1.
- **Possible slider feature:** event markers (launches, flybys, arrivals), which make each probe's story visible.

## John's standing rules that apply here

His global CLAUDE.md covers these; the ones most relevant to this project:

- Ambiguity: stop and ask. Confirm larger pieces of work before building.
- Don't declare anything done from internal checks. John tests what he sees on screen and confirms.
- Scientific data comes from authoritative sources (JPL Horizons, CelesTrak), named in the data files and the README. Spot-check known values before shipping, for example Earth at about 1 AU, Jupiter at about 5.2 AU, and Voyager 1's current distance against NASA's published figure.
- When reusing code from UNCHARTED or Star Explorer, read the original first and list the behaviors being carried over. Confirm with John which ones to keep.
- No em dashes in anything a user sees (UI text, README). Use American spelling.
- Never commit or bump versions unless asked. Stage by explicit path, never `git add -A`.
- John packages, pushes, and deploys himself. End each change by saying what it needs to take effect.

## First session

1. Read Star Explorer's README and `index.html`, and skim UNCHARTED's README, to learn the backbone, theme, and camera controls.
2. Ask John the four open questions above, starting with the draft object list.
3. Write a short plan (data pipeline, scene structure, scale modes, time slider) and get it confirmed.
4. Only then build, starting with a small prototype: Sun, planets, and one or two probes over a short time range.
