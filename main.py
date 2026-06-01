from fastapi import Request
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from skyfield.api import wgs84, Star
from skyfield.iokit import Loader
from twilio.twiml.messaging_response import MessagingResponse

# ── Load ephemeris safely at startup ────────────────────────────────
load_path = Loader('/tmp')
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

    # ── Stars, Constellations & Asterisms ───────────────────────────
    star_objects = [

        # ── Stars ───────────────────────────────────────────────────
        ("Arcturus",       "star",      Star(ra_hours=14.2610, dec_degrees=19.1822)),   # Arcturus
        ("Spica",          "star",      Star(ra_hours=13.4199, dec_degrees=-11.1613)),  # Spica
        ("Vega",           "star",      Star(ra_hours=18.6156, dec_degrees=38.7837)),   # Vega
        ("The_North_Star", "star",      Star(ra_hours=2.5303,  dec_degrees=89.2641)),   # Polaris
        ("Antares",        "star",      Star(ra_hours=16.4901, dec_degrees=-26.4320)),  # Antares
        ("Altair",         "star",      Star(ra_hours=19.8463, dec_degrees=8.8683)),    # Altair
        ("Deneb",          "star",      Star(ra_hours=20.6905, dec_degrees=45.2803)),   # Deneb
        ("Regulus",        "star",      Star(ra_hours=10.1395, dec_degrees=11.9672)),   # Regulus

        # ── Constellations ──────────────────────────────────────────
        ("Orion",          "constellation", Star(ra_hours=5.9195,  dec_degrees=7.4071)),    # Betelgeuse
        ("Bootes",         "constellation", Star(ra_hours=14.2610, dec_degrees=19.1822)),   # Arcturus
        ("Scorpius",       "constellation", Star(ra_hours=16.4901, dec_degrees=-26.4320)),  # Antares
        ("Leo",            "constellation", Star(ra_hours=10.1395, dec_degrees=11.9672)),   # Regulus
        ("Gemini",         "constellation", Star(ra_hours=7.5755,  dec_degrees=31.8883)),   # Pollux
        ("Taurus",         "constellation", Star(ra_hours=4.5988,  dec_degrees=16.5093)),   # Aldebaran
        ("Canis_Major",    "constellation", Star(ra_hours=6.7526,  dec_degrees=-16.7161)),  # Sirius
        ("Canis_Minor",    "constellation", Star(ra_hours=7.6550,  dec_degrees=5.2250)),    # Procyon
        ("Lyra",           "constellation", Star(ra_hours=18.6156, dec_degrees=38.7837)),   # Vega
        ("Aquila",         "constellation", Star(ra_hours=19.8463, dec_degrees=8.8683)),    # Altair
        ("Cygnus",         "constellation", Star(ra_hours=20.6905, dec_degrees=45.2803)),   # Deneb
        ("Perseus",        "constellation", Star(ra_hours=3.0794,  dec_degrees=40.9556)),   # Mirfak
        ("Delphinus",      "constellation", Star(ra_hours=20.6603, dec_degrees=15.9122)),   # Rotanev
        ("Sagittarius",    "constellation", Star(ra_hours=19.0437, dec_degrees=-29.8800)),  # Kaus Australis
        ("Cassiopeia",     "constellation", Star(ra_hours=0.6751,  dec_degrees=56.5373)),   # Schedar
        ("Corona_Borealis","constellation", Star(ra_hours=15.5784, dec_degrees=26.7148)),   # Alphecca

        # ── Asterisms ───────────────────────────────────────────────
        ("The_Big_Dipper",    "asterism", Star(ra_hours=11.0621, dec_degrees=56.3824)),  # Dubhe
        ("The_Teapot",        "asterism", Star(ra_hours=19.0437, dec_degrees=-29.8800)), # Kaus Australis (Sagittarius)
        ("Summer_Triangle",   "asterism", Star(ra_hours=18.6156, dec_degrees=38.7837)),  # Vega (brightest)
        ("Spring_Triangle",   "asterism", Star(ra_hours=14.2610, dec_degrees=19.1822)),  # Arcturus (brightest)
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
