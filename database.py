import sqlite3
import uuid
from datetime import datetime, timedelta
from config import Config


def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id                  TEXT PRIMARY KEY,
            client_mac          TEXT,
            client_ip           TEXT,
            nds_token           TEXT,
            phone               TEXT,
            package_id          TEXT,
            amount              REAL,
            checkout_request_id TEXT UNIQUE,
            merchant_request_id TEXT,
            status              TEXT DEFAULT 'pending',
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at          TIMESTAMP,
            redirect_url        TEXT
        );

        CREATE TABLE IF NOT EXISTS payments (
            id             TEXT PRIMARY KEY,
            session_id     TEXT,
            mpesa_receipt  TEXT UNIQUE,
            amount         REAL,
            phone          TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ── Sessions ────────────────────────────────────────────────────────────────

def create_session(client_mac, client_ip, nds_token, phone, package_id, amount, redirect_url):
    conn = get_db()
    session_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO sessions
           (id, client_mac, client_ip, nds_token, phone, package_id, amount, redirect_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, client_mac, client_ip, nds_token, phone, package_id, amount, redirect_url),
    )
    conn.commit()
    conn.close()
    return session_id


def update_session_checkout(session_id, checkout_request_id, merchant_request_id):
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET checkout_request_id=?, merchant_request_id=? WHERE id=?",
        (checkout_request_id, merchant_request_id, session_id),
    )
    conn.commit()
    conn.close()


def get_session_by_checkout(checkout_request_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sessions WHERE checkout_request_id=?", (checkout_request_id,)
    ).fetchone()
    conn.close()
    return row


def get_session(session_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return row


def mark_session_paid(session_id, duration_minutes):
    conn = get_db()
    expires_at = (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat()
    conn.execute(
        "UPDATE sessions SET status='paid', expires_at=? WHERE id=?",
        (expires_at, session_id),
    )
    conn.commit()
    conn.close()


def mark_session_failed(session_id):
    conn = get_db()
    conn.execute("UPDATE sessions SET status='failed' WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def mark_session_expired(session_id):
    conn = get_db()
    conn.execute("UPDATE sessions SET status='expired' WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def record_payment(session_id, mpesa_receipt, amount, phone):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO payments (id, session_id, mpesa_receipt, amount, phone) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), session_id, mpesa_receipt, amount, str(phone)),
    )
    conn.commit()
    conn.close()


def get_expired_active_sessions():
    """Return paid sessions whose time has run out (used by auto-disconnect)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE status='paid' AND expires_at <= datetime('now')"
    ).fetchall()
    conn.close()
    return rows


def get_admin_stats():
    conn = get_db()
    sessions = conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 200"
    ).fetchall()
    revenue = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM payments"
    ).fetchone()
    today_revenue = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE DATE(created_at)=DATE('now')"
    ).fetchone()
    conn.close()
    return sessions, revenue["total"], today_revenue["total"]


# ── Settings (operator configuration stored in DB) ──────────────────────────

def get_settings():
    """Return all operator settings as a plain dict."""
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def save_settings(settings_dict):
    """Upsert a dict of settings into the DB."""
    conn = get_db()
    for key, value in settings_dict.items():
        if value:  # skip blanks — keep existing value
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
    conn.commit()
    conn.close()
