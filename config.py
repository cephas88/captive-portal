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

    # Default prices — overridden by admin panel (DB) or env vars.
    PACKAGES = [
        {"id": "1hr",    "name": "1 Hour",   "duration": 60,    "default_price": int(os.environ.get("PRICE_1HR",    "10")),   "speed": "5 Mbps"},
        {"id": "3hr",    "name": "3 Hours",  "duration": 180,   "default_price": int(os.environ.get("PRICE_3HR",    "25")),   "speed": "5 Mbps"},
        {"id": "5hr",    "name": "5 Hours",  "duration": 300,   "default_price": int(os.environ.get("PRICE_5HR",    "40")),   "speed": "5 Mbps"},
        {"id": "10hr",   "name": "10 Hours", "duration": 600,   "default_price": int(os.environ.get("PRICE_10HR",   "70")),   "speed": "10 Mbps"},
        {"id": "1day",   "name": "1 Day",    "duration": 1440,  "default_price": int(os.environ.get("PRICE_1DAY",   "100")),  "speed": "10 Mbps"},
        {"id": "1week",  "name": "1 Week",   "duration": 10080, "default_price": int(os.environ.get("PRICE_1WEEK",  "500")),  "speed": "10 Mbps"},
        {"id": "1month", "name": "1 Month",  "duration": 43200, "default_price": int(os.environ.get("PRICE_1MONTH", "1500")), "speed": "10 Mbps"},
    ]
