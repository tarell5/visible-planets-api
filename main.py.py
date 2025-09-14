from fastapi import FastAPI, Query
from skyfield.api import load, wgs84

app = FastAPI()

@app.get("/visible-objects")
def get_visible_objects(lat: float = Query(...), lon: float = Query(...)):
    ts = load.timescale()
    eph = load('de421.bsp')

    t = ts.now()
    observer = wgs84.latlon(lat, lon)
    earth = eph['earth']
    obs = earth + observer

    visible = []

    celestial_objects = [
        ("Mercury", "planet"),
        ("Venus", "planet"),
        ("Mars", "planet"),
        ("Jupiter", "planet"),
        ("Saturn", "planet"),
        ("Uranus", "planet"),
        ("Neptune", "planet"),
        ("Pluto", "dwarf planet"),
        ("Moon", "moon")
    ]

    for name, obj_type in celestial_objects:
        try:
            body = eph[name]
            astrometric = obs.at(t).observe(body)
            alt, az, _ = astrometric.apparent().altaz()

            if alt.degrees > 0:
                visible.append({
                    "object": name,
                    "type": obj_type,
                    "altitude": round(alt.degrees, 2),
                    "azimuth": round(az.degrees, 2)
                })
        except KeyError:
            # Skip if object is not in the ephemeris file
            continue

    return {"visible_objects": visible}
