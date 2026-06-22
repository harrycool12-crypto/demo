import sqlite3
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import os

DB_PATH = "gym.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS member_master (
                member_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                mobile      TEXT UNIQUE NOT NULL,
                father_name TEXT DEFAULT '',
                address     TEXT DEFAULT '',
                join_date   DATE NOT NULL,
                status      TEXT DEFAULT 'Active',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS membership (
                membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id     INTEGER NOT NULL,
                plan          TEXT NOT NULL,
                start_date    DATE NOT NULL,
                expiry_date   DATE NOT NULL,
                amount        DECIMAL NOT NULL,
                payment_mode  TEXT DEFAULT 'Cash',
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES member_master(member_id)
            );

            CREATE TABLE IF NOT EXISTS payment_history (
                payment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id     INTEGER NOT NULL,
                membership_id INTEGER,
                amount        DECIMAL NOT NULL,
                payment_date  DATE NOT NULL,
                payment_mode  TEXT DEFAULT 'Cash',
                plan          TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id)     REFERENCES member_master(member_id),
                FOREIGN KEY (membership_id) REFERENCES membership(membership_id)
            );
        """)


# ─── Dashboard ────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    with get_db() as conn:
        today      = date.today().isoformat()
        week_later = (date.today() + timedelta(days=7)).isoformat()
        month_start = date.today().replace(day=1).isoformat()

        total    = conn.execute("SELECT COUNT(*) FROM member_master").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM member_master WHERE status='Active'").fetchone()[0]
        inactive = conn.execute("SELECT COUNT(*) FROM member_master WHERE status='Inactive'").fetchone()[0]

        expiring = conn.execute("""
            SELECT COUNT(DISTINCT m.member_id)
            FROM membership ms
            JOIN member_master m ON m.member_id = ms.member_id
            WHERE m.status = 'Active'
              AND ms.expiry_date BETWEEN ? AND ?
              AND ms.membership_id = (
                    SELECT membership_id FROM membership
                    WHERE member_id = m.member_id
                    ORDER BY expiry_date DESC LIMIT 1
              )
        """, (today, week_later)).fetchone()[0]

        today_col = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_history WHERE payment_date=?",
            (today,)
        ).fetchone()[0]

        monthly_col = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_history WHERE payment_date>=?",
            (month_start,)
        ).fetchone()[0]

        # Last 6 months bar-chart data
        chart_data = []
        for i in range(5, -1, -1):
            d = date.today()
            month = d.month - i
            year  = d.year
            while month <= 0:
                month += 12
                year  -= 1
            ms  = f"{year}-{month:02d}-01"
            me  = f"{year}-{month+1:02d}-01" if month < 12 else f"{year+1}-01-01"
            amt = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM payment_history WHERE payment_date>=? AND payment_date<?",
                (ms, me)
            ).fetchone()[0]
            chart_data.append({"month": datetime(year, month, 1).strftime("%b %Y"), "amount": float(amt)})

        expiring_members = conn.execute("""
            SELECT m.member_id, m.name, m.mobile, ms.expiry_date,
                   CAST(julianday(ms.expiry_date) - julianday(?) AS INTEGER) AS days_remaining
            FROM member_master m
            JOIN membership ms ON ms.member_id = m.member_id
            WHERE m.status = 'Active'
              AND ms.expiry_date BETWEEN ? AND ?
              AND ms.membership_id = (
                    SELECT membership_id FROM membership
                    WHERE member_id = m.member_id
                    ORDER BY expiry_date DESC LIMIT 1
              )
            ORDER BY ms.expiry_date
        """, (today, today, week_later)).fetchall()

        recent_payments = conn.execute("""
            SELECT ph.payment_id, m.name, ph.amount, ph.payment_date, ph.plan, ph.payment_mode
            FROM payment_history ph
            JOIN member_master m ON m.member_id = ph.member_id
            ORDER BY ph.created_at DESC LIMIT 10
        """).fetchall()

        return {
            "total_members":     total,
            "active_members":    active,
            "inactive_members":  inactive,
            "expiring_soon":     expiring,
            "today_collection":  today_col,
            "monthly_collection": monthly_col,
            "chart_data":        chart_data,
            "expiring_members":  [dict(r) for r in expiring_members],
            "recent_payments":   [dict(r) for r in recent_payments],
        }


# ─── Members ──────────────────────────────────────────────────────────────────

def search_members(q: str = "", status: str = ""):
    with get_db() as conn:
        query = """
            SELECT m.member_id, m.name, m.mobile, m.father_name, m.address,
                   m.join_date, m.status, ms.expiry_date, ms.plan
            FROM member_master m
            LEFT JOIN membership ms ON ms.member_id = m.member_id
              AND ms.membership_id = (
                    SELECT membership_id FROM membership
                    WHERE member_id = m.member_id
                    ORDER BY expiry_date DESC LIMIT 1
              )
            WHERE 1=1
        """
        params = []
        if q:
            query += " AND (m.name LIKE ? OR m.mobile LIKE ? OR CAST(m.member_id AS TEXT) LIKE ?)"
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if status:
            query += " AND m.status = ?"
            params.append(status)
        query += " ORDER BY m.member_id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_member(member_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM member_master WHERE member_id=?", (member_id,)
        ).fetchone()
        if not row:
            return None
        m = dict(row)
        ms = conn.execute("""
            SELECT * FROM membership WHERE member_id=?
            ORDER BY expiry_date DESC LIMIT 1
        """, (member_id,)).fetchone()
        m["current_membership"] = dict(ms) if ms else None
        return m


def add_member(data: dict) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO member_master (name, mobile, father_name, address, join_date, status)
            VALUES (?, ?, ?, ?, ?, 'Active')
        """, (data["name"], data["mobile"], data.get("father_name", ""), data.get("address", ""), data["join_date"]))
        member_id = cur.lastrowid

        # First membership
        mid = conn.execute("""
            INSERT INTO membership (member_id, plan, start_date, expiry_date, amount, payment_mode)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (member_id, data["plan"], data["start_date"], data["expiry_date"],
              data["amount"], data.get("payment_mode", "Cash"))).lastrowid

        conn.execute("""
            INSERT INTO payment_history (member_id, membership_id, amount, payment_date, payment_mode, plan)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (member_id, mid, data["amount"], data["start_date"],
              data.get("payment_mode", "Cash"), data["plan"]))

        return member_id


def update_member(member_id: int, data: dict):
    with get_db() as conn:
        conn.execute("""
            UPDATE member_master SET name=?, mobile=?, father_name=?, address=?
            WHERE member_id=?
        """, (data["name"], data["mobile"], data.get("father_name", ""), data.get("address", ""), member_id))


def deactivate_member(member_id: int):
    with get_db() as conn:
        conn.execute("UPDATE member_master SET status='Inactive' WHERE member_id=?", (member_id,))


def reactivate_member(member_id: int):
    with get_db() as conn:
        conn.execute("UPDATE member_master SET status='Active' WHERE member_id=?", (member_id,))


# ─── Payments ─────────────────────────────────────────────────────────────────

PLAN_MONTHS = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Annual": 12}


def renew_membership(member_id: int, data: dict):
    from dateutil.relativedelta import relativedelta  # type: ignore
    months = PLAN_MONTHS.get(data["plan"], 1)
    start  = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
    expiry = start + relativedelta(months=months)

    with get_db() as conn:
        mid = conn.execute("""
            INSERT INTO membership (member_id, plan, start_date, expiry_date, amount, payment_mode)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (member_id, data["plan"], start.isoformat(), expiry.isoformat(),
              data["amount"], data.get("payment_mode", "Cash"))).lastrowid

        conn.execute("""
            INSERT INTO payment_history (member_id, membership_id, amount, payment_date, payment_mode, plan)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (member_id, mid, data["amount"], start.isoformat(),
              data.get("payment_mode", "Cash"), data["plan"]))

        conn.execute("UPDATE member_master SET status='Active' WHERE member_id=?", (member_id,))
        return expiry.isoformat()


def get_payment_history(member_id: int = None, limit: int = 200):
    with get_db() as conn:
        if member_id:
            rows = conn.execute("""
                SELECT ph.*, m.name FROM payment_history ph
                JOIN member_master m ON m.member_id = ph.member_id
                WHERE ph.member_id=?
                ORDER BY ph.created_at DESC LIMIT ?
            """, (member_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT ph.*, m.name FROM payment_history ph
                JOIN member_master m ON m.member_id = ph.member_id
                ORDER BY ph.created_at DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]


# ─── Reports ──────────────────────────────────────────────────────────────────

def report_active_members():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT m.member_id, m.name, m.mobile, m.father_name, m.address,
                   m.join_date, ms.plan, ms.expiry_date
            FROM member_master m
            LEFT JOIN membership ms ON ms.member_id = m.member_id
              AND ms.membership_id = (
                    SELECT membership_id FROM membership
                    WHERE member_id = m.member_id ORDER BY expiry_date DESC LIMIT 1
              )
            WHERE m.status='Active'
            ORDER BY m.name
        """).fetchall()
        return [dict(r) for r in rows]


def report_inactive_members():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT m.member_id, m.name, m.mobile, m.father_name, m.address,
                   m.join_date, ms.expiry_date AS last_expiry
            FROM member_master m
            LEFT JOIN membership ms ON ms.member_id = m.member_id
              AND ms.membership_id = (
                    SELECT membership_id FROM membership
                    WHERE member_id = m.member_id ORDER BY expiry_date DESC LIMIT 1
              )
            WHERE m.status='Inactive'
            ORDER BY m.name
        """).fetchall()
        return [dict(r) for r in rows]


def report_expiry(days: int = 30):
    today  = date.today().isoformat()
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT m.member_id, m.name, m.mobile, ms.plan, ms.expiry_date,
                   CAST(julianday(ms.expiry_date) - julianday(?) AS INTEGER) AS days_remaining
            FROM member_master m
            JOIN membership ms ON ms.member_id = m.member_id
            WHERE m.status='Active'
              AND ms.expiry_date BETWEEN ? AND ?
              AND ms.membership_id = (
                    SELECT membership_id FROM membership
                    WHERE member_id = m.member_id ORDER BY expiry_date DESC LIMIT 1
              )
            ORDER BY ms.expiry_date
        """, (today, today, cutoff)).fetchall()
        return [dict(r) for r in rows]


def report_collection(period: str = "monthly", year: int = None, month: int = None):
    today = date.today()
    year  = year  or today.year
    month = month or today.month
    with get_db() as conn:
        if period == "daily":
            start = f"{year}-{month:02d}-01"
            if month == 12:
                end = f"{year+1}-01-01"
            else:
                end = f"{year}-{month+1:02d}-01"
            rows = conn.execute("""
                SELECT payment_date AS label, COALESCE(SUM(amount),0) AS amount
                FROM payment_history
                WHERE payment_date>=? AND payment_date<?
                GROUP BY payment_date ORDER BY payment_date
            """, (start, end)).fetchall()
        elif period == "monthly":
            start = f"{year}-01-01"
            end   = f"{year+1}-01-01"
            rows = conn.execute("""
                SELECT strftime('%Y-%m', payment_date) AS label, COALESCE(SUM(amount),0) AS amount
                FROM payment_history
                WHERE payment_date>=? AND payment_date<?
                GROUP BY label ORDER BY label
            """, (start, end)).fetchall()
        else:  # yearly
            rows = conn.execute("""
                SELECT strftime('%Y', payment_date) AS label, COALESCE(SUM(amount),0) AS amount
                FROM payment_history
                GROUP BY label ORDER BY label
            """).fetchall()

        total = sum(float(r["amount"]) for r in rows)
        return {"rows": [dict(r) for r in rows], "total": total}
