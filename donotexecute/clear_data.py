"""
WARNING: This script deletes ALL member, membership, and payment data from gym.db.
         The users/login table is NOT touched.
         All active login sessions are also cleared.

Run only when you want a completely fresh start.
"""

import sys
import os

# Make sure we run from the project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

confirm = input("This will DELETE all member/payment data and log out all users. Type YES to continue: ")
if confirm.strip() != "YES":
    print("Aborted.")
    sys.exit(0)

# ── Clear DB tables ──────────────────────────────────────────────────────────
import sqlite3
conn = sqlite3.connect("gym.db")
conn.execute("DELETE FROM payment_history")
conn.execute("DELETE FROM membership")
conn.execute("DELETE FROM member_master")
conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('member_master','membership','payment_history')")
conn.commit()
conn.close()
print("DB cleared: payment_history, membership, member_master (users table untouched).")

# ── Clear all in-memory sessions ─────────────────────────────────────────────
try:
    import auth
    auth._SESSIONS.clear()
    print("All active login sessions cleared.")
except Exception as e:
    print(f"Sessions could not be cleared (server may not be running): {e}")

print("\nDone. Restart the application to begin fresh.")
