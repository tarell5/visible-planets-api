from fastapi import Request
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from skyfield.api import load, wgs84, Star
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/visible-objects")
def get_visible_objects(lat: float = Query(...), lon: float = Query(...)):
    ts = load.timescale()
    eph = load('de421.bsp')
    t = ts.now()
    observer = wgs84.latlon(lat, lon)
    earth = eph['earth']
    obs = earth + observer

    visible = []

    # ── Planets & Moon ──────────────────────────────────────────────
    celestial_objects = [
        ("mercury",            "Mercury", "planet"),
        ("venus",              "Venus",   "planet"),
        ("mars",               "Mars",    "planet"),
        ("jupiter barycenter", "Jupiter", "planet"),
        ("saturn barycenter",  "Saturn",  "planet"),
        ("uranus barycenter",  "Uranus",  "planet"),
        ("neptune barycenter", "Neptune", "planet"),
        ("pluto barycenter",   "Pluto",   "dwarf planet"),
        ("moon",               "Moon",    "moon"),
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
        ("Vega",  "star", Star(ra_hours=18.6156, dec_degrees=38.7837)),
        ("Orion", "star", Star(ra_hours=5.9195,  dec_degrees=7.4071)),  # anchored to Betelgeuse
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
