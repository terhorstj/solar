"""Every object the app shows, with its Horizons ID and display details. See objects.md.

Colors are display choices, not data. Physical data (GM, radius) comes from the Horizons
object headers or JPL's Small-Body Database, except the RADIUS_KM table below.
"""

START = "1957-10-04"   # Sputnik 1
STOP = "2036-01-01"    # through the end of 2035

# (id, name, color)
PLANETS = [
    ("199", "Mercury", "#a7a29b"),
    ("299", "Venus", "#e6cf9f"),
    ("399", "Earth", "#5b93dc"),
    ("499", "Mars", "#cf6a43"),
    ("599", "Jupiter", "#d9b58c"),
    ("699", "Saturn", "#e4d09c"),
    ("799", "Uranus", "#a3dbe2"),
    ("899", "Neptune", "#5a7de0"),
]

# (id, name, parent, approximate period in days [only sets the reference grid spacing], color)
MOONS = [
    ("301", "Moon", "399", 27.32, "#c9c9c9"),
    ("401", "Phobos", "499", 0.319, "#9a8b7c"),
    ("402", "Deimos", "499", 1.263, "#a39684"),
    ("501", "Io", "599", 1.769, "#e8d36a"),
    ("502", "Europa", "599", 3.551, "#ddd2bb"),
    ("503", "Ganymede", "599", 7.155, "#ab9f8b"),
    ("504", "Callisto", "599", 16.69, "#82766a"),
    ("601", "Mimas", "699", 0.942, "#c9c6c0"),
    ("602", "Enceladus", "699", 1.370, "#f1f5f7"),
    ("603", "Tethys", "699", 1.888, "#d9d6cf"),
    ("604", "Dione", "699", 2.737, "#cfcbc3"),
    ("605", "Rhea", "699", 4.518, "#c4c0b8"),
    ("606", "Titan", "699", 15.95, "#e0b45c"),
    ("608", "Iapetus", "699", 79.3, "#b7a58c"),
    ("705", "Miranda", "799", 1.413, "#bfbab2"),
    ("701", "Ariel", "799", 2.520, "#c9c4bc"),
    ("702", "Umbriel", "799", 4.144, "#8f8a83"),
    ("703", "Titania", "799", 8.706, "#c0b6aa"),
    ("704", "Oberon", "799", 13.46, "#ada196"),
    ("801", "Triton", "899", 5.877, "#d8c6c2"),
    ("901", "Charon", "999", 6.387, "#a9a49c"),
]

# Dwarf planets and visited small bodies: (Horizons command, display id, name, kind, color, SBDB designation)
# Haumea, Eris, Arrokoth, and Didymos use small-body solutions: their system-barycenter IDs cover only a few decades.
DWARFS = [
    ("2000001", "2000001", "Ceres", "dwarf", "#a19e98", "1"),
    ("999", "999", "Pluto", "dwarf", "#d9c3a5", None),
    ("136108;", "136108", "Haumea", "dwarf", "#e4e4e4", "136108"),
    ("136472;", "136472", "Makemake", "dwarf", "#d8a985", "136472"),
    ("136199;", "136199", "Eris", "dwarf", "#ececec", "136199"),
]
SMALL = [
    ("4;", "2000004", "Vesta", "asteroid", "#a8a096", "4"),
    ("433;", "2000433", "Eros", "asteroid", "#a8957d", "433"),
    ("DES=67P;CAP;", "67P", "67P/Churyumov-Gerasimenko", "comet", "#9fd3e6", "67P"),
    ("162173;", "2162173", "Ryugu", "asteroid", "#8d8780", "162173"),
    ("101955;", "2101955", "Bennu", "asteroid", "#8e8982", "101955"),
    ("486958;", "2486958", "Arrokoth", "kbo", "#c48a6a", "486958"),
    ("65803;", "2065803", "Didymos", "asteroid", "#a29a8e", "65803"),
    ("DES=1P;CAP<1995;", "1P", "Halley's Comet", "comet", "#9fd3e6", "1P"),
]

# Radii that neither Horizons nor the SBDB provides (km, volume-equivalent mean radius).
# Published values; please confirm before shipping.
RADIUS_KM = {
    "136108": (798.0, "Ortiz et al. 2017, Nature 550, 219 (triaxial 1161 x 852 x 513 km)"),
    "136472": (715.0, "Ortiz et al. 2012, Nature 491, 566 (diameter about 1430 km)"),
    "136199": (1163.0, "Sicardy et al. 2011, Nature 478, 493 (diameter 2326 km)"),
    "2486958": (9.0, "Spencer et al. 2020, Science 367, aay3999 (36 x 20 x 10 km; ~18 km equivalent diameter)"),
}

# Spacecraft: (Horizons id, name, kind, note shown on the card or None)
# Launch dates come from CelesTrak's satellite catalog via each craft's international designator.
PROBES = [
    ("-2", "Mariner 2", "probe", None),
    ("-23", "Pioneer 10", "probe", None),
    ("-24", "Pioneer 11", "probe", None),
    ("-31", "Voyager 1", "probe", None),
    ("-32", "Voyager 2", "probe", None),
    ("-77", "Galileo", "probe", None),
    ("-55", "Ulysses", "probe", None),
    ("-93", "NEAR Shoemaker", "probe", None),
    ("-82", "Cassini-Huygens", "probe", None),
    ("-29", "Stardust", "probe", None),
    ("-226", "Rosetta", "probe", None),
    ("-236", "MESSENGER", "probe", None),
    ("-98", "New Horizons", "probe", None),
    ("-203", "Dawn", "probe", None),
    ("-61", "Juno", "probe", None),
    ("-76", "Curiosity", "probe", "Cruise to Mars, then on the surface."),
    ("-168", "Perseverance", "probe", "Cruise to Mars, then on the surface."),
    ("-64", "OSIRIS-REx", "probe", "Renamed OSIRIS-APEX after returning its Bennu sample in 2023."),
    ("-37", "Hayabusa2", "probe", "Position relative to Ryugu is only good to about 20 km."),
    ("-96", "Parker Solar Probe", "probe", None),
    ("-121", "BepiColombo", "probe", None),
    ("-144", "Solar Orbiter", "probe", None),
    ("-49", "Lucy", "probe", None),
    ("-135", "DART", "probe", "Ended by design, crashing into Dimorphos, the small moon of Didymos."),
    ("-28", "JUICE", "probe", None),
    ("-255", "Psyche", "probe", None),
    ("-159", "Europa Clipper", "probe", None),
    ("-91", "Hera", "probe", None),
    ("-170", "James Webb Space Telescope", "observatory", "Orbits the Sun-Earth L2 point."),
    ("-21", "SOHO", "observatory", "Orbits the Sun-Earth L1 point."),
    ("-227", "Kepler", "observatory", "Trails Earth around the Sun, slowly drifting away."),
    ("-79", "Spitzer", "observatory", "Trails Earth around the Sun, slowly drifting away."),
    ("-399080", "Apollo 8", "apollo", "Position is the S-IVB third stage, which flew with the crew toward the Moon."),
    ("-399110", "Apollo 11", "apollo", "Position is the S-IVB third stage, which flew with the crew toward the Moon."),
]
# probes whose span ends when they stop closing in on a body (an impact the surface rule can't see: after it,
# Horizons keeps DART riding along with Dimorphos, about 1.2 km from the Didymos system's center)
END_AT_CLOSEST = {"-135": "2065803"}
# explicit end times (UTC) where Horizons' track gives no usable signal. Please confirm before shipping.
#   MESSENGER: its reconstructed orbit grazes 4 km above Mercury's mean radius at the crash and then keeps
#   orbiting in Horizons. Impact time from NASA's MESSENGER mission announcement, 2015-04-30.
END_AT = {"-236": ("2015-04-30 19:26", "Crashed into Mercury on 2015-04-30, as planned; tracking ends there.")}
PROBE_COLOR = {"probe": "#ffd27a", "observatory": "#b9e2a0", "apollo": "#f2a0a0"}
