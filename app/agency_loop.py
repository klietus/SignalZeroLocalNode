# app/agency_loop.py

import time
from datetime import datetime
from app.symbol_store import get_symbols

def run_agency_loop():
    while True:
        now = datetime.now().isoformat()
        print(f"[{now}] 🌀 AGENCY LOOP: Symbol scan running...")

        symbols = get_symbols(start=0, limit=100)
        count = len(symbols)

        print(f"[{now}] Found {count} symbols.")

        # TODO: Add your actual symbolic logic here
        # e.g. detect unresolved paradoxes, empty macros, orphan triads, etc

        time.sleep(60)  # sleep 60 seconds (adjust as needed)

if __name__ == "__main__":
    run_agency_loop()
