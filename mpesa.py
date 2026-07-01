import base64
import logging
from datetime import datetime

import requests

from config import Config

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    phone = phone.strip().lstrip("+").replace(" ", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    return phone


def _get_access_token(cfg: dict) -> str:
    credentials = base64.b64encode(
        f"{cfg['consumer_key']}:{cfg['consumer_secret']}".encode()
    ).decode()
    resp = requests.get(
        f"{cfg['base_url']}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {credentials}"},
        timeout=15,
    )
    if resp.status_code == 400:
        raise RuntimeError("Invalid Consumer Key or Consumer Secret — check your Daraja app credentials")
    if resp.status_code == 401:
        raise RuntimeError("Unauthorized — Consumer Key/Secret rejected by Safaricom")
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Unexpected Daraja response: {data}")
    return data["access_token"]


def _make_password(cfg: dict):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{cfg['shortcode']}{cfg['passkey']}{timestamp}"
    return base64.b64encode(raw.encode()).decode(), timestamp


def initiate_stk_push(phone: str, amount: int, account_ref: str, description: str, cfg: dict) -> dict:
    token = _get_access_token(cfg)
    password, timestamp = _make_password(cfg)
    phone = _normalize_phone(phone)

    payload = {
        "BusinessShortCode": cfg["shortcode"],
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": cfg["shortcode"],
        "PhoneNumber": phone,
        "CallBackURL": cfg["callback_url"],
        "AccountReference": account_ref,
        "TransactionDesc": description,
    }

    resp = requests.post(
        f"{cfg['base_url']}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("STK push response: %s", data)

    if data.get("ResponseCode") != "0":
        raise RuntimeError(data.get("ResponseDescription", "STK push failed"))

    return data
