from fastapi import Request
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from skyfield.api import load, wgs84, Star
from skyfield.iokit import Loader
from twilio.twiml.messaging_response import MessagingResponse
import os

# ── Load ephemeris safely at startup ────────────────────────────────
load_path = Loader('/tmp')  # Railway's writable directory
eph = load_path('de421.bsp')
ts = load_path.timescale()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/visible-objects")
def get_visible_objects(lat: float = Query(...), lon: float = Query(...)):
    t = ts.now()
    observer = wgs84.latlon(lat, lon)
    earth = eph['earth']
    obs = earth + observer

    visible = []

    # ── Planets & Moon ──────────────────────────────────────────────
    celestial_objects = [
        ("mercury",            "Mercury",  "planet"),
        ("venus",              "Venus",    "planet"),
        ("mars",               "Mars",     "planet"),
        ("jupiter barycenter", "Jupiter",  "planet"),
        ("saturn barycenter",  "Saturn",   "planet"),
        ("uranus barycenter",  "Uranus",   "planet"),
        ("neptune barycenter", "Neptune",  "planet"),
        ("pluto barycenter",   "Pluto",    "dwarf planet"),
        ("moon",               "Moon",     "moon"),
    ]

    for eph_key, display_name, obj_type in celestial_objects:
        try:
            body = eph[eph_key]
            astrometric = obs.at(t).observe(body)
            alt, az, _ = astrometric.apparent().altaz()
            if alt.degrees > 0:
                visible.append({
                    "object": display_name,
                    "type": obj_type,
                    "altitude": round(alt.degrees, 2),
                    "azimuth": round(az.degrees, 2)
                })
        except KeyError:
            continue

    # ── Stars & Constellations ──────────────────────────────────────
    star_objects = [
        ("Vega",        "star",          Star(ra_hours=18.6156, dec_degrees=38.7837)),
        ("Orion",       "constellation", Star(ra_hours=5.9195,  dec_degrees=7.4071)),
        ("Arcturus",    "star",          Star(ra_hours=14.2610, dec_degrees=19.1822)),
        ("Regulus",     "star",          Star(ra_hours=10.1395, dec_degrees=11.9672)),
        ("Spica",       "star",          Star(ra_hours=13.4199, dec_degrees=-11.1613)),
        ("Polaris",     "star",          Star(ra_hours=2.5303,  dec_degrees=89.2641)),
        ("Big_Dipper",  "constellation", Star(ra_hours=11.0621, dec_degrees=56.3824)),
        ("Cassiopeia",  "constellation", Star(ra_hours=0.6751,  dec_degrees=56.5373)),
    ]

    for display_name, obj_type, star in star_objects:
        try:
            astrometric = obs.at(t).observe(star)
            alt, az, _ = astrometric.apparent().altaz()
            if alt.degrees > 0:
                visible.append({
                    "object": display_name,
                    "type": obj_type,
                    "altitude": round(alt.degrees, 2),
                    "azimuth": round(az.degrees, 2)
                })
        except Exception:
            continue

    return {"visible_objects": visible}


@app.post("/webhook")
async def webhook(request: Request):
    print("🔥 Webhook hit")
    event = await request.json()
    print("Event type:", event.get('type'))
    if event and event.get('type') == 'checkout.session.completed':
        session = event['data']['object']
        phone = session.get('customer_details', {}).get('phone')
        print("Customer phone:", phone)
        print("✅ PAYMENT SUCCESSFUL")
    return {"status": "ok"}


@app.post("/sms")
async def sms_reply(request: Request):
    form = await request.form()
    incoming_msg = form.get("Body", "").strip()
    resp = MessagingResponse()
    resp.message(f"You said: {incoming_msg}")
    return Response(content=str(resp), media_type="application/xml")
