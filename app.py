import logging
import threading
import time

from flask import Flask, jsonify, render_template, request

import database
import mpesa
import nodogsplash
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

database.init_db()

PACKAGES = {p["id"]: p for p in Config.PACKAGES}


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_mpesa_cfg() -> dict:
    """
    Load M-Pesa credentials: DB settings take priority over .env defaults.
    This lets each operator configure their own credentials via the admin panel.
    """
    s = database.get_settings()
    return {
        "consumer_key":    s.get("mpesa_consumer_key")    or Config.MPESA_CONSUMER_KEY,
        "consumer_secret": s.get("mpesa_consumer_secret") or Config.MPESA_CONSUMER_SECRET,
        "shortcode":       s.get("mpesa_shortcode")       or Config.MPESA_SHORTCODE,
        "passkey":         s.get("mpesa_passkey")         or Config.MPESA_PASSKEY,
        "callback_url":    s.get("mpesa_callback_url")    or Config.MPESA_CALLBACK_URL,
        "base_url":        s.get("mpesa_base_url")        or Config.MPESA_BASE_URL,
    }


def is_setup_complete() -> bool:
    cfg = get_mpesa_cfg()
    return all([cfg["consumer_key"], cfg["consumer_secret"], cfg["shortcode"], cfg["passkey"]])


# ── Auto-disconnect background thread ────────────────────────────────────────
# nodogsplash already disconnects devices via the session timeout parameter.
# This thread is a safety net: it also deauths and marks any sessions whose
# expires_at has passed but are still recorded as 'paid' in the database.

def _auto_disconnect_loop():
    while True:
        try:
            expired = database.get_expired_active_sessions()
            for session in expired:
                logger.info("Auto-disconnecting expired session %s (mac: %s)", session["id"], session["client_mac"])
                nodogsplash.deauth_client(session["nds_token"])
                database.mark_session_expired(session["id"])
        except Exception as exc:
            logger.error("Auto-disconnect error: %s", exc)
        time.sleep(60)  # check every 60 seconds


threading.Thread(target=_auto_disconnect_loop, daemon=True).start()


# ── Portal pages ─────────────────────────────────────────────────────────────

@app.route("/")
def portal():
    client_ip   = request.args.get("clientip", request.remote_addr)
    client_mac  = request.args.get("clientmac", "unknown")
    nds_token   = request.args.get("tok", "")
    redirect_url = request.args.get("redir", "https://google.com")

    s = database.get_settings()
    hotspot_name = s.get("hotspot_name") or Config.HOTSPOT_NAME

    return render_template(
        "portal.html",
        packages=Config.PACKAGES,
        client_ip=client_ip,
        client_mac=client_mac,
        nds_token=nds_token,
        redirect_url=redirect_url,
        hotspot_name=hotspot_name,
    )


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    sessions, total_revenue, today_revenue = database.get_admin_stats()
    settings = database.get_settings()
    s = settings
    hotspot_name = s.get("hotspot_name") or Config.HOTSPOT_NAME

    # Mask secrets for display
    masked = dict(s)
    for key in ("mpesa_consumer_key", "mpesa_consumer_secret", "mpesa_passkey"):
        if masked.get(key):
            v = masked[key]
            masked[key] = v[:4] + "****" + v[-4:] if len(v) > 8 else "****"

    return render_template(
        "admin.html",
        sessions=sessions,
        total_revenue=total_revenue,
        today_revenue=today_revenue,
        hotspot_name=hotspot_name,
        settings=masked,
        setup_complete=is_setup_complete(),
    )


@app.route("/admin/setup", methods=["POST"])
def admin_setup():
    """Save operator M-Pesa credentials and hotspot name."""
    fields = [
        "hotspot_name",
        "nds_host",
        "nds_port",
        "mpesa_consumer_key",
        "mpesa_consumer_secret",
        "mpesa_shortcode",
        "mpesa_passkey",
        "mpesa_callback_url",
        "mpesa_base_url",
    ]
    data = {f: request.form.get(f, "").strip() for f in fields}

    # Ensure callback URL always ends with /mpesa-callback
    if data.get("mpesa_callback_url"):
        url = data["mpesa_callback_url"].rstrip("/")
        if not url.endswith("/mpesa-callback"):
            url += "/mpesa-callback"
        data["mpesa_callback_url"] = url

    database.save_settings(data)
    return jsonify({"ok": True, "message": "Settings saved.", "callback_url": data.get("mpesa_callback_url", "")})


# ── Payment API ───────────────────────────────────────────────────────────────

@app.route("/initiate-payment", methods=["POST"])
def initiate_payment():
    if not is_setup_complete():
        return jsonify({"error": "Hotspot is not configured yet. Contact the administrator."}), 503

    data = request.get_json(force=True)
    phone        = (data.get("phone") or "").strip()
    package_id   = data.get("package_id")
    client_mac   = data.get("client_mac", "unknown")
    client_ip    = data.get("client_ip", request.remote_addr)
    nds_token    = data.get("nds_token", "")
    redirect_url = data.get("redirect_url", "https://google.com")

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400
    if not package_id or package_id not in PACKAGES:
        return jsonify({"error": "Invalid package selected"}), 400

    package = PACKAGES[package_id]
    session_id = database.create_session(
        client_mac, client_ip, nds_token, phone,
        package_id, package["price"], redirect_url,
    )

    try:
        cfg = get_mpesa_cfg()
        result = mpesa.initiate_stk_push(
            phone=phone,
            amount=package["price"],
            account_ref=f"WiFi-{session_id[:8].upper()}",
            description=f"WiFi {package['name']}",
            cfg=cfg,
        )
    except Exception as exc:
        logger.error("STK push failed: %s", exc)
        return jsonify({"error": str(exc)}), 502

    database.update_session_checkout(
        session_id,
        result["CheckoutRequestID"],
        result["MerchantRequestID"],
    )

    return jsonify({
        "session_id": session_id,
        "checkout_request_id": result["CheckoutRequestID"],
        "message": "STK push sent — check your phone and enter your M-Pesa PIN.",
    })


@app.route("/mpesa-callback", methods=["POST"])
def mpesa_callback():
    payload = request.get_json(force=True, silent=True) or {}
    logger.info("M-Pesa callback: %s", payload)

    try:
        stk = payload["Body"]["stkCallback"]
        checkout_request_id = stk["CheckoutRequestID"]
        result_code = stk["ResultCode"]

        session = database.get_session_by_checkout(checkout_request_id)
        if not session:
            logger.warning("No session for CheckoutRequestID %s", checkout_request_id)
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

        if result_code == 0:
            items = {
                item["Name"]: item.get("Value")
                for item in stk.get("CallbackMetadata", {}).get("Item", [])
            }
            mpesa_receipt = items.get("MpesaReceiptNumber", "")
            amount        = items.get("Amount", 0)
            phone         = items.get("PhoneNumber", session["phone"])

            package  = PACKAGES.get(session["package_id"], {})
            duration = package.get("duration", 60)

            database.mark_session_paid(session["id"], duration)
            database.record_payment(session["id"], mpesa_receipt, amount, phone)

            # Grant access — nodogsplash will auto-disconnect after `duration` minutes
            granted = nodogsplash.grant_access(
                session["nds_token"], session["redirect_url"], duration
            )
            logger.info(
                "Session %s paid (receipt %s). Access granted: %s. Duration: %s min",
                session["id"], mpesa_receipt, granted, duration,
            )
        else:
            logger.info("Payment failed for session %s: %s", session["id"], stk.get("ResultDesc"))
            database.mark_session_failed(session["id"])

    except Exception as exc:
        logger.error("Callback error: %s", exc)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


@app.route("/check-payment/<session_id>")
def check_payment(session_id):
    """Frontend polls this every 2 seconds to know when the payment is confirmed."""
    session = database.get_session(session_id)
    if not session:
        return jsonify({"status": "not_found"}), 404

    resp = {"status": session["status"]}
    if session["status"] == "paid":
        resp["redirect_url"] = session["redirect_url"]
        resp["expires_at"]   = session["expires_at"]

        # Build the nodogsplash auth URL so the browser (which is on the local
        # WiFi network) can hit the router directly to unlock internet access.
        # This works whether the portal runs locally or on a cloud server.
        s = database.get_settings()
        nds_host = s.get("nds_host") or Config.NDS_HOST
        nds_port = s.get("nds_port") or Config.NDS_PORT
        nds_token = session["nds_token"]
        redir = session["redirect_url"]
        if nds_token:
            resp["nds_auth_url"] = (
                f"http://{nds_host}:{nds_port}/nodogsplash_auth"
                f"?tok={nds_token}&redir={redir}"
            )

    return jsonify(resp)


if __name__ == "__main__":
    app.run(host=Config.PORTAL_HOST, port=Config.PORTAL_PORT, debug=False)
