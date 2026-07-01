import logging

import requests

from config import Config

logger = logging.getLogger(__name__)


def _nds_url(path):
    return f"http://{Config.NDS_HOST}:{Config.NDS_PORT}/{path}"


def grant_access(nds_token: str, redirect_url: str, duration_minutes: int = None) -> bool:
    """
    Allow a client through the firewall for `duration_minutes`.
    nodogsplash automatically disconnects the device when the timeout expires.
    """
    params = {"tok": nds_token, "redir": redirect_url}
    if duration_minutes:
        params["timeout"] = duration_minutes * 60  # nodogsplash expects seconds

    try:
        resp = requests.get(_nds_url("nodogsplash_auth"), params=params, timeout=10)
        if resp.status_code == 200:
            logger.info("nodogsplash granted access for token %s (%s min)", nds_token, duration_minutes)
            return True
        logger.warning("nodogsplash auth returned %s", resp.status_code)
        return False
    except requests.RequestException as exc:
        logger.error("nodogsplash auth failed: %s", exc)
        return False


def deauth_client(nds_token: str) -> bool:
    """
    Forcibly disconnect a device before its session expires.
    Called by the auto-disconnect background thread as a safety net.
    """
    try:
        resp = requests.get(
            _nds_url("nodogsplash_deauth"),
            params={"tok": nds_token},
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("nodogsplash deauthed token %s", nds_token)
            return True
        logger.warning("nodogsplash deauth returned %s for token %s", resp.status_code, nds_token)
        return False
    except requests.RequestException as exc:
        logger.error("nodogsplash deauth failed: %s", exc)
        return False
