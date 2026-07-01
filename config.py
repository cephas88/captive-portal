import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-before-going-live")
    # On Fly.io the persistent volume is mounted at /data
    _default_db = "/data/captive_portal.db" if os.path.isdir("/data") else "captive_portal.db"
    DATABASE_PATH = os.environ.get("DATABASE_PATH", _default_db)

    # M-Pesa Daraja API credentials
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "")
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL", "https://yourdomain.com/mpesa-callback")
    # Switch to https://api.safaricom.co.ke for production
    MPESA_BASE_URL = os.environ.get("MPESA_BASE_URL", "https://sandbox.safaricom.co.ke")

    # nodogsplash auth endpoint (runs on the router)
    NDS_HOST = os.environ.get("NDS_HOST", "192.168.1.1")
    NDS_PORT = os.environ.get("NDS_PORT", "2050")

    # Flask server binding
    PORTAL_HOST = os.environ.get("PORTAL_HOST", "0.0.0.0")
    PORTAL_PORT = int(os.environ.get("PORTAL_PORT", "5000"))

    # Hotspot name shown on the portal
    HOTSPOT_NAME = os.environ.get("HOTSPOT_NAME", "QuickNet Hotspot")

    # Base price in KES per hour — all package prices are calculated from this.
    # Override via admin panel or BASE_PRICE env var.
    DEFAULT_BASE_PRICE = int(os.environ.get("BASE_PRICE", "10"))

    # Packages: multiplier determines price = round(base_price * multiplier).
    # Longer packages have smaller multipliers relative to duration → cheaper per hour.
    # discount_pct shows how much cheaper per hour vs the 1hr base rate.
    PACKAGES = [
        {"id": "30min", "name": "30 Min",  "duration": 30,    "multiplier": 0.5,  "speed": "5 Mbps",  "discount_pct": 0},
        {"id": "1hr",   "name": "1 Hour",  "duration": 60,    "multiplier": 1,    "speed": "5 Mbps",  "discount_pct": 0},
        {"id": "3hr",   "name": "3 Hours", "duration": 180,   "multiplier": 2.5,  "speed": "5 Mbps",  "discount_pct": 17},
        {"id": "1day",  "name": "1 Day",   "duration": 1440,  "multiplier": 15,   "speed": "10 Mbps", "discount_pct": 38},
        {"id": "1week", "name": "1 Week",  "duration": 10080, "multiplier": 75,   "speed": "10 Mbps", "discount_pct": 55},
    ]
