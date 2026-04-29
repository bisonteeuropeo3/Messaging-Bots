# FreedHome Bot — Operating Guide

Bot for sending automated messages on **immobiliare.it**, **subito.it** and **idealista.it**.
Each platform has its own folder with independent code.

---

## Setup (one time only)

```bash
pip install -r requirements.txt
playwright install chromium
```

> Starting from this version, the bot attaches to a **real Chrome window** (yours) via CDP, instead of launching a separate Chromium. Bypasses most anti-bot detection.

---

## Folder structure

```
ImmobiliareBot/          ← immobiliare.it code (here)
  generate_messages.py
  send_messages.py
  config.yaml

SubitoBot/               ← subito.it code
  generate_messages.py
  send_messages.py
  config.yaml

IdealistaBot/            ← idealista.it code
  generate_messages.py
  send_messages.py
  config.yaml

core/                    ← shared engine (don't touch)
platforms/               ← per-platform selectors (don't touch)
```

---

## How to use: 3 steps

### Step 1 — Generate messages

Drop the Apify CSV into the platform folder, then:

```bash
# Immobiliare
python generate_messages.py

# Subito
cd SubitoBot && python generate_messages.py

# Idealista
cd IdealistaBot && python generate_messages.py
```

### Step 2 — Open Chrome with the debug port

From terminal (Windows / macOS / Linux):

```bash
python start_chrome.py
```

Alternatively on Windows: **double-click `start_chrome.bat`**.

A dedicated Chrome window for the bot opens, on a separate profile:
- Windows: `C:\chrome-bot-profile`
- macOS / Linux: `~/chrome-bot-profile`

The first time, log in to immobiliare.it / subito.it / idealista.it manually in that window. After that, the login is saved.

> **Leave that Chrome window open** during sending. If you close it, the bot disconnects.

Direct Chrome command alternative:
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-bot-profile"

# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-bot-profile"
```

### Step 3 — Send messages

```bash
python send_messages.py --total 400 --batch 50 --pause 20
```

**That's it.** The bot:
- Sends 50 messages
- Pauses 20 minutes
- Sends another 50
- Pauses 20 minutes
- ...repeats until 400 total
- You don't have to do anything, fully automatic

---

## THE COMMAND YOU NEED

To send 400 messages automatically without touching anything:

```bash
python send_messages.py --total 400 --batch 50 --pause 20
```

What it actually does:
- **8 batches of 50 messages** each
- **20-minute pause** between batches
- Within each batch: **25-55 seconds** between messages
- Every **4-7 messages**: **long pause of 2-5 minutes** (simulates reading)
- **Estimated total time: ~6-7 hours** (perfect for a workday)

### Before launching for real, check with dry-run:

```bash
python send_messages.py --dry-run --total 400 --batch 50 --pause 20
```

---

## Available options

| Option | Default | Description |
|---|---|---|
| `--total N` | all | Total messages to send |
| `--batch N` | 50 | Messages per batch |
| `--pause N` | 20 | Minutes of pause between batches |
| `--dry-run` | off | Simulate without sending |
| `--config file` | config.yaml | Custom config |

### Examples

```bash
# Quick session: 100 messages, batches of 25, 15-min pause
python send_messages.py --total 100 --batch 25 --pause 15

# Safe session (aggressive site): small batches, long pauses
python send_messages.py --total 200 --batch 30 --pause 30

# Resume from where it left off (no limit)
python send_messages.py
```

---

## Anti-block tips

### What the bot does automatically

- 25-55s delay between messages (Gaussian distribution)
- Long pause of 2-5 min every 4-7 messages
- Character-by-character typing (40-130ms)
- Gradual scroll before interacting
- Click with random offset
- Randomized viewport and user-agent
- Anti-fingerprinting (navigator.webdriver hidden)
- Auto-stop if blocked
- Progressive cooldown after errors

### What you have to do

1. **Use a VPN** — change IP before each session (or at least once a day)
2. **Spread over time** — don't send 400 messages all on the same platform
3. **Vary the times** — don't always start at 9:00
4. **If blocked** — wait 4-6 hours, change IP, restart

### Recommended daily schedule (300+ messages/day)

| Time | Platform | Command |
|---|---|---|
| 9:00 | Immobiliare | `python send_messages.py --total 100 --batch 50 --pause 20` |
| 12:00 | Subito | `cd SubitoBot && python send_messages.py --total 100 --batch 50 --pause 20` |
| 15:00 | Idealista | `cd IdealistaBot && python send_messages.py --total 100 --batch 30 --pause 25` |

Total: 300 messages, spread across 3 platforms, ~8 hours.

> For Idealista use smaller batches (30) and longer pauses (25 min) because it's the most aggressive platform with captchas.

---

## New campaign

1. Place the new CSV in the right folder
2. Delete the old files:
   ```bash
   rm listings_ready.csv progress.json
   ```
3. Open Chrome with `python start_chrome.py` (or `start_chrome.bat` on Windows), then:
   ```bash
   python generate_messages.py
   python send_messages.py --total 400 --batch 50 --pause 20
   ```

> DO NOT delete the `C:\chrome-bot-profile` (Windows) or `~/chrome-bot-profile` (macOS/Linux) folder — it contains the saved Chrome login.

---

## Configuration (config.yaml)

Each folder has its own `config.yaml`. Edit values to tune behavior:

```yaml
delay_min: 25          # seconds between messages
delay_max: 55
pause_every_min: 4     # long pause every N messages
pause_every_max: 7
pause_duration_min: 120  # pause duration (seconds)
pause_duration_max: 300
max_per_hour: 25       # hourly limit
max_per_day: 100       # daily limit
```

### "Aggressive" profile (at your own risk)
```yaml
delay_min: 15
delay_max: 30
max_per_hour: 40
max_per_day: 200
```

### "Ultra-safe" profile (idealista)
```yaml
delay_min: 40
delay_max: 70
pause_duration_min: 180
pause_duration_max: 420
max_per_hour: 15
max_per_day: 60
```

---

## Common issues

| Problem | Solution |
|---|---|
| "BLOCKED" | Change IP (VPN), wait 4-6h, restart |
| `ECONNREFUSED 9222` | Chrome not opened with debug port — run `python start_chrome.py` |
| `ECONNREFUSED ::1:9222` | `cdp_url` uses `localhost`, replace with `127.0.0.1` in `config.yaml` |
| "Login required" / "not logged in" | Open Chrome via `python start_chrome.py`, log in manually, restart the bot |
| "Textarea not found" | Listing expired or layout changed, check `snapshots/` |
| "hourly limit reached" | Wait 1 hour or change `max_per_hour` |
| "No CSV found" | Place the CSV in the right folder |
| Bot doesn't start | `pip install -r requirements.txt && playwright install chromium` |
| Chrome closed mid-campaign | Reopen with `python start_chrome.py`, restart `send_messages.py` (resumes from `progress.json`) |

---

## Generated files (don't touch)

| File | Contents |
|---|---|
| `listings_ready.csv` | Messages ready to send |
| `progress.json` | Track of what was sent |
| `start_chrome.py` / `start_chrome.bat` | Chrome launcher with debug port (cross-platform Python / Windows batch) |
| `logs/` | Detailed logs per session (JSONL) |
| `snapshots/` | Screenshots and HTML when something goes wrong |
| `C:\chrome-bot-profile\` (Win) / `~/chrome-bot-profile` (Mac/Linux) | Bot-dedicated Chrome profile (login, cookies, etc.) |

> The old `auth_state.json` file is no longer used — you can delete it if it exists.

---

## Chrome configuration (config.yaml)

Two modes available in [config.yaml](config.yaml):

### Active mode: attach to existing Chrome (recommended)
```yaml
cdp_url: "http://127.0.0.1:9222"
```
The bot attaches to the Chrome window opened with `python start_chrome.py` (or `start_chrome.bat`). Best stealth — uses your real Chrome, identical fingerprint.

### Alternative mode: automatic persistent profile
```yaml
cdp_url: ""
user_data_dir: ""    # empty = uses ./chrome_profile/
```
The bot opens Chrome by itself with a dedicated profile. No need for `start_chrome.py`. Good stealth but the profile is "fresh" (no extensions, no real history).
