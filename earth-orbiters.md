# Earth-orbiters: sources (for John to check)

Earth-orbiters circle Earth every 1.5 to 63 hours, far too fast for daily position tables. So each one is drawn as an orbit ring around Earth, visible when you zoom in near Earth, and labeled approximate. Ten objects are in the plan (`objects.md`): six still in orbit and four that have reentered.

Categories, as in `probe-events.md`:

- **Documented**: stated by the cited source.
- **Memory, checked**: my recollection, not found on an accessible source, but consistent with a documented value (shown).
- **Memory, unconfirmed**: my recollection only.

Sources, retrieved 2026-10-19:

- **NSSDCA**: NASA's Space Science Data Coordinated Archive. Its catalog entries for Sputnik 1 (`1957-001B`), Explorer 1 (`1958-001A`), and Mir (`1986-017A`) return an error page today, like Luna 1 and Giotto. Skylab's loads.
- **SATCAT**: CelesTrak's satellite catalog, the public copy of the US Space Force catalog. Launch and reentry dates are reliable. Its orbit fields are the last ones recorded, so for a reentered object they describe the final days before reentry, not a typical orbit.
- **CelesTrak elements**: current orbital elements (GP data) for objects still in orbit.

## The four historical orbiters

### Sputnik 1 (NORAD 2, `1957-001B`)

| Value | Used | Source and quote | Category |
|---|---|---|---|
| Launch | 1957-10-04 | SATCAT: LAUNCH_DATE 1957-10-04 | Documented |
| Reentry | 1958-01-03 | SATCAT: DECAY_DATE 1958-01-03 | Documented |
| Inclination | 65.1 degrees | SATCAT: INCLINATION 65 | Documented (65 in SATCAT; 65.1 from memory) |
| Period | about 96 minutes | NASA history page (`nasa.gov/history/sputnik/index.html`): "took about 98 minutes to orbit Earth on its elliptical path"; SATCAT: PERIOD 96.1 | Documented |
| Initial orbit | 215 x 939 km | Gives a 96.2-minute period, matching SATCAT's 96.1 | Memory, checked |

### Explorer 1 (NORAD 4, `1958-001A`)

| Value | Used | Source and quote | Category |
|---|---|---|---|
| Launch | 1958-02-01 (03:48 UT; the evening of January 31 in Florida) | SATCAT: LAUNCH_DATE 1958-02-01; NASA Explorer 1 page: "31, 1958 as Explorer 1 launched and reached orbit" | Documented (time of day from memory) |
| Reentry | 1970-03-31 | SATCAT: DECAY_DATE 1970-03-31 | Documented |
| Inclination | 33.2 degrees | SATCAT: INCLINATION 33.15 | Documented |
| Initial orbit | 358 x 2,550 km, period about 115 minutes | The size and period are consistent with each other (they give 115 minutes) | Memory, unconfirmed (no documented period for the initial orbit) |
| Final orbit | 183 x 215 km, period 88.5 minutes | SATCAT: APOGEE 215, PERIGEE 183, PERIOD 88.48 | Documented |

### Skylab (NORAD 6633, `1973-027A`)

| Value | Used | Source and quote | Category |
|---|---|---|---|
| Launch | 1973-05-14 17:30 UT | NSSDCA `1973-027A`: "Launch Date/Time: 1973-05-14T17:30:00Z" | Documented |
| Reentry | 1979-07-11 | NSSDCA `1973-027A`: "Decay Date: 1979-07-11" | Documented |
| Orbit | 434 x 442 km, 50.0 degrees, 93.4 minutes | NSSDCA `1973-027A`: "434.00 km 442.00 km 93.40 minutes 50.000°" | Documented |
| Final orbit | 221 x 227 km | SATCAT: APOGEE 227, PERIGEE 221 | Documented |

### Mir (NORAD 16609, `1986-017A`; the core module)

| Value | Used | Source and quote | Category |
|---|---|---|---|
| Launch | 1986-02-19 | SATCAT: LAUNCH_DATE 1986-02-19 | Documented |
| Reentry | 2001-03-23 | SATCAT: DECAY_DATE 2001-03-23 | Documented |
| Inclination | 51.6 degrees | SATCAT: INCLINATION 51.64 | Documented |
| Typical orbit | about 350 x 375 km, period about 91.5 minutes | | Memory, unconfirmed (Mir was reboosted many times, so no single orbit is right) |
| Final orbit | 151 x 215 km | SATCAT: APOGEE 215, PERIGEE 151 | Documented |

## The six still in orbit

These use current CelesTrak elements, fetched when the data is built: size, inclination, eccentricity, and the orientation of the orbit at that moment. Launch dates are from SATCAT.

| Object | NORAD | Launched | Current orbit (SATCAT) |
|---|---|---|---|
| ISS (Zarya, the first module) | 25544 | 1998-11-20 | 415 x 424 km, 51.6 degrees |
| Hubble | 20580 | 1990-04-24 | 468 x 471 km, 28.5 degrees |
| Tiangong (Tianhe core module) | 48274 | 2021-04-29 | 384 x 386 km, 41.5 degrees |
| Chandra | 25867 | 1999-07-23 | 12,649 x 136,195 km, 57.9 degrees (a third of the way to the Moon) |
| Vanguard 1 | 5 | 1958-03-17 | 651 x 3,819 km, 34.3 degrees |
| Telstar 1 | 340 | 1962-07-10 | 947 x 5,638 km, 44.8 degrees |

## How the rings would be drawn (my proposal)

- **Size and tilt:** from the values above, tilted relative to Earth's equator and converted into the app's ecliptic frame.
- **Orientation over time:** Earth's equatorial bulge makes a low orbit's plane swing around (for the ISS, about 5 degrees a day). I'd apply that standard swing rate, computed from each orbit's size and tilt. For the six current objects it starts from the measured orientation today; for the four historical ones it starts from an arbitrary angle, so their orientation is approximate. Labeled so.
- **Live marker:** within a week of the elements' date, a marker shows where the object actually is (SGP4, the standard satellite model, via the satellite.js library bundled into the page). Farther from that date, the ring shows without a marker.
- **Scale:** these rings are tiny (the ISS ring is 6% bigger than Earth), so they only show when you're zoomed in near Earth, with the same minimum-size rule as everything else.

## Decisions (John, 2026-10-19) and what the build found

- **Memory values used** as listed. Sputnik 1's catalog "final" apogee (1,080 km) is higher than its first (939 km), which a decaying orbit can't do, so no ring is ever allowed to grow: final sizes are capped at the first.
- **Historical rings shrink** from first to final orbit over the lifetime, faster near the end (the square of the fraction of the lifetime).
- **Current objects** show at today's size from launch to 2035, with the live marker within 7 days of the elements' date.
- **No satellite.js.** The marker uses two-body motion plus the bulge's drift instead of SGP4. Checked against JPL Horizons' own tracks: the ISS within 31 to 53 km and Hubble within 40 to 56 km, from 7 days before to 7 days after the elements' date. That's more than enough for a marker, without bundling a library.
