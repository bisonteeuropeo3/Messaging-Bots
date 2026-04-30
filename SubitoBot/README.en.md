# SubitoBot — Operating Guide

Bot for sending automated messages on **subito.it**.

> This version uses **CDP attach** mode: open Chrome with a dedicated profile, log in once, and the bot attaches to the existing window. No more `auth_state.json`, no more interactive terminal login.

---

## Setup (one time only)

```bash
pip install -r requirements.txt
playwright install chromium
```

> Only **private** listings are processed — agencies are filtered out automatically.

---

## 3-step flow

### Step 1 — Generate messages

Drop the Apify CSV into the folder, then:

```bash
python generate_messages.py
```

**Input:** a `Subito_scraper*.csv` file (Apify export) in the same folder.
**Output:** `listings_ready.csv` with personalized messages ready to send.

Prints a preview of the first 3 messages for sanity check.

---

### Step 2 — Open Chrome with the debug port

#### Windows
Double-click **`start_chrome.bat`**, or from terminal:
```bash
python start_chrome.py
```

#### macOS
Double-click **`start_chrome.command`** (first time: `chmod +x start_chrome.command`),
or from terminal:
```bash
python start_chrome.py
```

#### Linux
```bash
python start_chrome.py
```

A dedicated Chrome window opens for the bot, on a separate profile:
- Windows: `C:\chrome-bot-profile`
- macOS / Linux: `~/chrome-bot-profile`

**The first time**, log in to subito.it manually in that window. From there on, the login is persisted — you won't be asked again.

> **Leave that Chrome window open** while the bot runs. If you close it, the bot disconnects.

Direct Chrome command (alternative, if the launchers don't work):
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-bot-profile" https://areariservata.subito.it/login_form

# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-bot-profile" https://areariservata.subito.it/login_form
```

---

### Step 3 — Send messages

```bash
python send_messages.py --total 400 --batch 50 --pause 20
```

The bot:
- Attaches to the Chrome window from Step 2
- Verifies you're logged in (cookies + redirect check)
- Sends 50 messages
- Pauses 20 minutes
- Repeats up to 400 total

Resumes automatically from where it stopped (state in `progress.json`).

---

## `send_messages.py` options

| Option | Default | Description |
|---|---|---|
| `--total N` | 0 (all) | Total messages to send |
| `--batch N` | 50 | Messages per batch before inter-session pause |
| `--pause N` | 20 | Minutes between batches |
| `--dry-run` | off | Simulate without sending (preview) |
| `--config PATH` | `config.yaml` | Custom config file |

### Examples

```bash
# Resume from where you left off
python send_messages.py

# 400 messages, batches of 50, 20-min pause
python send_messages.py --total 400 --batch 50 --pause 20

# Quick session
python send_messages.py --total 100 --batch 25 --pause 15

# Ultra-safe session (subito is being aggressive)
python send_messages.py --total 200 --batch 30 --pause 30

# Dry run, no actual sending
python send_messages.py --dry-run --total 100
```

---

## Anti-detection and human-like behavior

All handled automatically by the shared core + `config.yaml`:

**Browser fingerprint:**
- Real Chrome profile (your cookies, history, extensions) via CDP
- User agent and viewport from your real Chrome
- `navigator.webdriver` flag hidden
- `AutomationControlled` disabled

**Human-like interactions:**
- Click with random offset from the element center
- Character-by-character typing (40-130ms)
- Gradual scroll simulating reading
- Random pauses between every step

**Rate limiting:**
- Gaussian delay between messages (25-55s default)
- Long pause every 4-7 messages (1-3 min)
- Hourly and daily limits
- Progressive cooldown after errors (backoff)
- Inter-batch pause (default 20 min with jitter)

All values are configurable in [config.yaml](config.yaml).

---

## Chrome configuration (`config.yaml`)

Two modes available:

### Active mode: attach to existing Chrome (recommended)
```yaml
cdp_url: "http://127.0.0.1:9222"
```
The bot attaches to the Chrome window opened with `start_chrome.py`. Best stealth — real Chrome, identical fingerprint.

### Alternative mode: automatic persistent profile
```yaml
cdp_url: ""
user_data_dir: ""    # empty = uses ./chrome_profile/
```
The bot launches Chrome by itself with a dedicated profile. No need for `start_chrome.py`.

---

## Loading a new dataset (new campaign)

1. Download the new CSV from Apify and place it in the folder
2. Delete the previous session files:
   ```bash
   # Windows
   del listings_ready.csv progress.json
   # macOS / Linux
   rm listings_ready.csv progress.json
   ```
3. Re-run from Step 1:
   ```bash
   python generate_messages.py
   python send_messages.py --total 400 --batch 50 --pause 20
   ```

> DO NOT delete the `chrome-bot-profile` folder — it holds the saved login.

> If multiple CSV files are in the folder, the script picks the **most recent** matching `Subito_scraper*.csv`, `Subito*.csv` or `dataset_subito*.csv`.

---

## Files in the folder

```
Subito_scraper*.csv     → raw Apify export (input)
listings_ready.csv      → listings with messages (Step 1 output)
progress.json           → send state (Step 2 output)
config.yaml             → timing/limits/browser config
generate_messages.py    → Step 1
send_messages.py        → Step 2 / 3
start_chrome.py         → cross-platform Chrome launcher
start_chrome.bat        → Chrome launcher (Windows double-click)
start_chrome.command    → Chrome launcher (macOS double-click)
screenshots/            → error screenshots
snapshots/              → HTML snapshots for debugging
logs/                   → JSONL logs per session
```

> The old `auth_state.json` is no longer used — you can delete it if it exists.

---

## Common issues

| Problem | Solution |
|---|---|
| "not logged in to attached browser" | Open subito.it in `chrome-bot-profile` and log in manually, then re-run |
| `ECONNREFUSED 9222` | Chrome not opened with debug port — run `start_chrome.py` |
| `ECONNREFUSED ::1:9222` | Replace `localhost` with `127.0.0.1` in `cdp_url` |
| "Contatta button not found" | Listing expired or layout changed — check `snapshots/` |
| "Blocked / anti-bot detection" | Change IP (VPN), wait 4-6h, restart |
| "Hourly limit reached" | Wait 1 hour or change `max_per_hour` in `config.yaml` |
| "No CSV found" | Place the CSV in the SubitoBot folder |
| Chrome closed mid-campaign | Reopen with `start_chrome.py`, restart (resumes from `progress.json`) |
| `start_chrome.command` won't open (macOS) | `chmod +x start_chrome.command` |

---

## Differences vs ImmobiliareBot

| | ImmobiliareBot | SubitoBot |
|---|---|---|
| Target site | immobiliare.it | subito.it |
| URL field in CSV | `directLink` | `page_url` |
| Agency filter | no | yes (auto-excluded) |
| Send flow | inline textarea | click "Contatta" → textarea → "Invia" |
