#!/usr/bin/env python3
"""EL-Wasset CRM - Arabic Real Estate Broker CRM
Run with: python run.py
"""

import uvicorn
import webbrowser
import threading
import time


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print("=" * 50)
    print("  EL-Wasset CRM - Arabic Real Estate Broker CRM")
    print("=" * 50)
    print("  http://localhost:8000")
    print("  Security: disposable email | OTP | rate limit | bcrypt | JWT | audit")
    print("=" * 50)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
