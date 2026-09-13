#!/usr/bin/env python3
"""
SafePass AI 24/7 Watchdog Supervisor
Monitors:
  1. Local FastAPI process & /health endpoint
  2. Public Cloudflare Tunnel & connectivity
  3. Caffeinate sleep-prevention daemon
  4. Syncs active live URL to LIVE_URL.txt and Desktop launcher
"""

import time
import os
import re
import sys
import subprocess
import urllib.request
import json
from pathlib import Path

BASE_DIR = Path("/Users/parthsonkusare1340/Hack2026ps1/safepass-ai")
LOGS_DIR = BASE_DIR / "logs"
CLOUDFLARED_LOG = LOGS_DIR / "cloudflared.log"
WATCHDOG_LOG = LOGS_DIR / "watchdog.log"
LIVE_URL_FILE = BASE_DIR / "LIVE_URL.txt"
DESKTOP_HTML = Path("/Users/parthsonkusare1340/Desktop/SAFEPASS_LIVE_LINK.html")

LOGS_DIR.mkdir(exist_ok=True)

def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def ensure_caffeinate():
    try:
        res = subprocess.run(["pgrep", "-f", "caffeinate -ids"], capture_output=True, text=True)
        if not res.stdout.strip():
            log("Caffeinate was not running. Launching 10-day sleep inhibitor (864000s)...")
            subprocess.Popen(["caffeinate", "-ids", "-t", "864000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log("Caffeinate active.")
    except Exception as e:
        log(f"Error checking caffeinate: {e}")

def check_local_fastapi() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_active_tunnel_url() -> str:
    if not CLOUDFLARED_LOG.exists():
        return ""
    try:
        with open(CLOUDFLARED_LOG, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in reversed(lines):
            match = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", line)
            if match:
                return match.group(0)
    except Exception as e:
        log(f"Error reading cloudflared log: {e}")
    return ""

def check_public_url(url: str) -> bool:
    if not url:
        return False
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=6) as resp:
            return resp.status == 200
    except Exception:
        return False

def update_live_url_files(url: str):
    try:
        with open(LIVE_URL_FILE, "w", encoding="utf-8") as f:
            f.write(f"{url}\n")
    except Exception as e:
        log(f"Failed to write LIVE_URL.txt: {e}")

    try:
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SafePass AI Live Web App</title>
    <meta http-equiv="refresh" content="0; url={url}">
    <script>window.location.href = "{url}";</script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0F172A; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        a {{ color: #38BDF8; font-size: 1.25rem; font-weight: 600; text-decoration: none; padding: 12px 24px; background: rgba(56, 189, 248, 0.1); border: 1px solid #38BDF8; border-radius: 8px; }}
        a:hover {{ background: #38BDF8; color: #0F172A; }}
    </style>
</head>
<body>
    <h2>🚀 SafePass AI Live Map & Risk Engine</h2>
    <p>Redirecting to live 24/7 tunnel...</p>
    <a href="{url}">Click here if not redirected automatically ({url})</a>
</body>
</html>"""
        with open(DESKTOP_HTML, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        log(f"Failed to write Desktop launcher: {e}")

def main():
    log("SafePass AI 24/7 Watchdog daemon started.")
    last_url = ""
    
    while True:
        try:
            ensure_caffeinate()

            # 1. Check local server
            if not check_local_fastapi():
                log("WARNING: Local FastAPI server not responding at 127.0.0.1:8000! Checking launchd...")
                subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.safepass.fastapi"], capture_output=True)
                time.sleep(2)

            # 2. Check tunnel URL
            tunnel_url = get_active_tunnel_url()
            if tunnel_url != last_url:
                log(f"Active Cloudflare Public URL detected: {tunnel_url}")
                last_url = tunnel_url
                update_live_url_files(tunnel_url)

            # 3. Verify public connectivity
            if tunnel_url:
                if check_public_url(tunnel_url):
                    pass # Healthy
                else:
                    log(f"Public URL {tunnel_url} did not respond to /health. Checking cloudflared process...")
                    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.safepass.cloudflared"], capture_output=True)
                    time.sleep(3)

        except Exception as e:
            log(f"Watchdog loop exception: {e}")

        time.sleep(15)

if __name__ == "__main__":
    main()
