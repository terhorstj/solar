# Object list

Signed off by John on 2026-10-18: everything from the draft, provided each object can get a reasonable ballpark position. IDs and coverage below were checked against JPL Horizons and CelesTrak on 2026-10-18.

Position source key:

- **Horizons**: position tables from JPL Horizons (heliocentric, ecliptic J2000).
- **Reconstructed**: not in Horizons. Trajectory rebuilt from dated mission events (launch, flybys, arrival) as two-body transfer arcs between Horizons planet positions. Exact at the events, approximate in between. Labeled "reconstructed" in the UI.
- **Ring (current)**: orbit ring from current CelesTrak elements; live position near "now" via SGP4. Labeled approximate.
- **Ring (historical)**: orbit ring from published orbit parameters over the object's lifetime. No reliable position along the ring. Labeled approximate.

How the Horizons objects are tracked (details in the README):

- **Moons** are stored relative to their planet, to 1% of their distance from it (agreed 2026-10-18: approximate is fine).
- **Spacecraft** are stored relative to the Sun in cruise. Near a planet, dwarf planet, or visited small body, they're stored relative to that body. Near a planet, that means inside its sphere of influence (twice that for Earth, to cover the L1 and L2 craft). Near a dwarf planet or small body, it means within 150,000 km.
- **Where a span ends.** Tracking stops when a craft enters a giant planet or reaches a rocky planet's surface (Galileo, Cassini, MESSENGER, and the Mars rovers at landing). NEAR's span ends at its Eros landing and Rosetta's at its comet landing. DART's ends at its closest approach to Didymos, which is the impact on Dimorphos.
- **Hayabusa2 near Ryugu.** Horizons can't center on Ryugu, so Hayabusa2 is placed there by subtracting the two heliocentric positions. Horizons' Ryugu and Hayabusa2 solutions disagree by about 15 to 20 km, which is noted on its card.

## Sun, planets, moons (Horizons, full 1957 to 2035)

| Object | ID |
|---|---|
| Sun | 10 |
| Mercury, Venus, Earth, Mars | 199, 299, 399, 499 |
| Jupiter, Saturn, Uranus, Neptune | 599, 699, 799, 899 |
| Moon | 301 |
| Phobos, Deimos | 401, 402 |
| Io, Europa, Ganymede, Callisto | 501, 502, 503, 504 |
| Mimas, Enceladus, Tethys, Dione, Rhea, Titan, Iapetus | 601, 602, 603, 604, 605, 606, 608 |
| Miranda, Ariel, Umbriel, Titania, Oberon | 705, 701, 702, 703, 704 |
| Triton | 801 |
| Charon | 901 |

## Dwarf planets and small bodies (Horizons, full 1957 to 2035)

Haumea, Eris, Arrokoth, and Didymos use their small-body solutions: their system-barycenter IDs only cover a few decades.

| Object | Horizons command |
|---|---|
| Ceres | 2000001 |
| Pluto | 999 |
| Haumea | 136108; |
| Makemake | 136472; |
| Eris | 136199; |
| Vesta | 4; |
| Eros | 433; |
| 67P/Churyumov-Gerasimenko | DES=67P;CAP; |
| Ryugu | 162173; |
| Bennu | 101955; |
| Arrokoth | 486958; |
| Didymos (Dimorphos shown with it) | 65803; |
| Halley's Comet | DES=1P;CAP<1995; (1986 apparition solution) |
| Comet Grigg-Skjellerup (added 2026-10-19 for Giotto) | DES=26P;CAP<1995; |

## Deep-space probes

Spans are the data in `probes.js` (Horizons coverage, cut where tracking ends). "Rebuilt" probes aren't in Horizons; their paths come from the dated events in `probe-events.md` (`probes-rebuilt.js`), approximate between encounters. Positions after 2026-10-18 are Horizons predictions and are labeled that way in the app. Launch dates are from CelesTrak's satellite catalog.

| Probe | Horizons ID | Launched | Span | Where tracking ends |
|---|---|---|---|---|
| Luna 1 | rebuilt (`luna1`) | 1959-01-02 | 1959-01-02 to 1959-01-05 | Contact lost about 62 hours after launch |
| Mariner 2 | -2 | 1962-08-27 | 1962-08-27 to 1962-12-31 |  |
| Mariner 4 | rebuilt (`mariner4`) | 1964-11-28 | 1964-11-28 to 1967-12-21 | Communications ended |
| Pioneer 10 | -23 | 1972-03-03 | 1972-03-03 to 2036-01-01 (predicted after 2026-10-18) |  |
| Pioneer 11 | -24 | 1973-04-06 | 1973-04-06 to 2036-01-01 (predicted after 2026-10-18) |  |
| Mariner 10 | rebuilt (`mariner10`) | 1973-11-03 | 1973-11-03 to 1975-03-24 | Attitude-control gas ran out |
| Viking 1 | rebuilt (`viking1`) | 1975-08-20 | 1975-08-20 to 1980-08-17 | Operations ended |
| Viking 2 | rebuilt (`viking2`) | 1975-09-09 | 1975-09-09 to 1978-07-25 | Turned off |
| Voyager 1 | -31 | 1977-09-05 | 1977-09-05 to 2036-01-01 (predicted after 2026-10-18) |  |
| Voyager 2 | -32 | 1977-08-20 | 1977-08-20 to 2036-01-01 (predicted after 2026-10-18) |  |
| Giotto | rebuilt (`giotto`) | 1985-07-02 | 1985-07-02 to 1992-07-23 | Operations ended |
| Galileo | -77 | 1989-10-18 | 1989-10-19 to 2003-09-21 | Entered Jupiter on 2003-09-21 |
| Ulysses | -55 | 1990-10-06 | 1990-10-06 to 2036-01-01 (predicted after 2026-10-18) |  |
| NEAR Shoemaker | -93 | 1996-02-17 | 1996-02-19 to 2001-02-12 | Reached the surface of Eros on 2001-02-12 |
| Cassini-Huygens | -82 | 1997-10-15 | 1997-10-15 to 2017-09-15 | Entered Saturn on 2017-09-15 |
| Stardust | -29 | 1999-02-07 | 1999-02-07 to 2011-03-12 |  |
| Rosetta | -226 | 2004-03-02 | 2004-03-02 to 2016-09-30 | Reached the surface of 67P/Churyumov-Gerasimenko on 2016-09-30 |
| MESSENGER | -236 | 2004-08-03 | 2004-08-03 to 2015-04-30 | Crashed into Mercury on 2015-04-30, as planned |
| New Horizons | -98 | 2006-01-19 | 2006-01-19 to 2036-01-01 (predicted after 2026-10-18) |  |
| Dawn | -203 | 2007-09-27 | 2007-09-27 to 2035-12-31 (predicted after 2026-10-18) |  |
| Juno | -61 | 2011-08-05 | 2011-08-05 to 2028-09-02 (predicted after 2026-10-18) |  |
| Curiosity | -76 | 2011-11-26 | 2011-11-26 to 2012-08-06 | Reached the surface of Mars on 2012-08-06 |
| Perseverance | -168 | 2020-07-30 | 2020-07-30 to 2021-02-18 | Reached the surface of Mars on 2021-02-18 |
| OSIRIS-REx | -64 | 2016-09-08 | 2016-09-08 to 2030-03-22 (predicted after 2026-10-18) |  |
| Hayabusa2 | -37 | 2014-12-03 | 2014-12-03 to 2026-12-31 (predicted after 2026-10-18) |  |
| Parker Solar Probe | -96 | 2018-08-12 | 2018-08-12 to 2030-01-01 (predicted after 2026-10-18) |  |
| BepiColombo | -121 | 2018-10-20 | 2018-10-20 to 2027-04-10 (predicted after 2026-10-18) |  |
| Solar Orbiter | -144 | 2020-02-10 | 2020-02-10 to 2030-11-20 (predicted after 2026-10-18) |  |
| Lucy | -49 | 2021-10-16 | 2021-10-16 to 2033-04-02 (predicted after 2026-10-18) |  |
| DART | -135 | 2021-11-24 | 2021-11-24 to 2022-09-26 | Crashed into its target on 2022-09-26, as planned |
| JUICE | -28 | 2023-04-14 | 2023-04-14 to 2031-07-21 (predicted after 2026-10-18) |  |
| Psyche | -255 | 2023-10-13 | 2023-10-13 to 2029-02-11 (predicted after 2026-10-18) |  |
| Europa Clipper | -159 | 2024-10-14 | 2024-10-14 to 2034-09-03 (predicted after 2026-10-18) |  |
| Hera | -91 | 2024-10-07 | 2024-10-07 to 2026-11-04 (predicted after 2026-10-18) |  |

## Lagrange points and Earth-trailing (Horizons)

| Object | Horizons ID | Launched | Span | Where tracking ends |
|---|---|---|---|---|
| James Webb Space Telescope | -170 | 2021-12-25 | 2021-12-25 to 2031-10-04 (predicted after 2026-10-18) |  |
| SOHO | -21 | 1995-12-02 | 1995-12-02 to 2026-11-02 (predicted after 2026-10-18) |  |
| Kepler | -227 | 2009-03-07 | 2009-03-07 to 2036-01-01 (predicted after 2026-10-18) |  |
| Spitzer | -79 | 2003-08-25 | 2003-08-25 to 2036-01-01 (predicted after 2026-10-18) |  |

## Apollo (Horizons, S-IVB third stage)

Horizons has the S-IVB stage, not the crewed spacecraft. The stage flew with the crew through translunar coast, so it is a fair stand-in for the outbound leg.

| Object | Horizons ID | Launched | Span | Where tracking ends |
|---|---|---|---|---|
| Apollo 8 | -399080 | 1968-12-21 | 1968-12-21 to 1968-12-31 |  |
| Apollo 11 | -399110 | 1969-07-16 | 1969-07-16 to 1969-07-28 |  |

## Earth-orbiters (CelesTrak catalog numbers)

| Object | NORAD | Source | Lifetime |
|---|---|---|---|
| ISS | 25544 | Ring (current) | 1998 to present |
| Hubble | 20580 | Ring (current) | 1990 to present |
| Tiangong (Tianhe core) | 48274 | Ring (current) | 2021 to present |
| Chandra | 25867 | Ring (current) | 1999 to present |
| Vanguard 1 | 5 | Ring (current) | 1958 to present |
| Telstar 1 | 340 | Ring (current) | 1962 to present (dead, still in orbit) |
| Sputnik 1 | 2 | Ring (historical) | 1957-10-04 to 1958-01-03 |
| Explorer 1 | 4 | Ring (historical) | 1958-02-01 to 1970-03-31 |
| Skylab | 6633 | Ring (historical) | 1973-05-14 to 1979-07-11 |
| Mir | 16609 | Ring (historical) | 1986-02-19 to 2001-03-23 |
| Geostationary belt | | Single ring at 35,786 km | |

## Values to confirm before shipping

These aren't from JPL or CelesTrak data feeds; they're published values I entered by hand (in `tools/catalog.py`):

- MESSENGER's impact time, 2015-04-30 19:26 UTC (NASA). Horizons' track gives no usable signal for it.
- Radii of Haumea (798 km), Makemake (715 km), Eris (1,163 km), and Arrokoth (about 9 km), from the papers cited in the catalog.

## Still to source

- Event dates for the six reconstructed probes (launch, flybys, arrival, end of mission), from NASA's NSSDCA catalog.
- Typical orbit parameters for the four historical Earth-orbiters. CelesTrak's catalog holds their final orbit just before reentry (Sputnik 1 shows a 64 km perigee), not a representative one, so these come from NSSDCA too.
