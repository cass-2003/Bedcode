"""Watchdog: auto-restart bot.py on crash."""
import os, subprocess, sys, time

MAX_RESTARTS, WINDOW = 10, 3600
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
restarts = []

while True:
    now = time.time()
    restarts = [t for t in restarts if now - t < WINDOW]
    if len(restarts) >= MAX_RESTARTS:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {MAX_RESTARTS} restarts in 1h, giving up.")
        sys.exit(1)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting bot.py...")
    try:
        rc = subprocess.call([sys.executable, "bot.py"], cwd=_SCRIPT_DIR)
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Interrupted, exiting.")
        sys.exit(0)
    if rc == 0:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Clean exit (0), not restarting.")
        break
    restarts.append(time.time())
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Crashed (exit {rc}), restarting in 5s...")
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Interrupted, exiting.")
        sys.exit(0)
