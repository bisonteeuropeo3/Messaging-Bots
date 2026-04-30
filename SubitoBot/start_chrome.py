"""
Apre Chrome con la porta di debug attiva, in un profilo separato dal daily Chrome.
Equivalente di start_chrome.bat ma lanciabile da terminale.
Compatibile Windows e macOS.

Uso:
  python start_chrome.py
"""

import os
import sys
import subprocess

DEBUG_PORT = 9222
START_URL = "https://areariservata.subito.it/login_form"


def chrome_path():
    if sys.platform == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]
    return "google-chrome"


def user_data_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/chrome-bot-profile")
    if sys.platform == "win32":
        return r"C:\chrome-bot-profile"
    return os.path.expanduser("~/chrome-bot-profile")


def main():
    path = chrome_path()
    profile = user_data_dir()

    if not os.path.exists(path):
        print(f"ERRORE: Chrome non trovato in {path}")
        print("Installa Google Chrome o modifica chrome_path() in questo script.")
        sys.exit(1)

    subprocess.Popen([
        path,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile}",
        START_URL,
    ])
    print(f"Chrome avviato su porta {DEBUG_PORT} con profilo {profile}")
    print("Lascia questa finestra Chrome aperta mentre il bot lavora.")


if __name__ == "__main__":
    main()
