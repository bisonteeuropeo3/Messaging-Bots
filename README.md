# Messaging Bots — Immobiliare & Subito

Bots for sending automated personalized messages on **immobiliare.it** and **subito.it**.
Designed to contact real-estate listing advertisers in bulk, simulating human behavior to avoid anti-bot blocks.

The repo contains two independent bots, one per platform:

```
ImmobiliareBot/   → bot for immobiliare.it
SubitoBot/        → bot for subito.it
```

---

## What they do

Each bot does two things:

1. **Generates personalized messages** from a dataset of listings (advertiser name, address, price, etc.).
2. **Sends the messages** automatically through a browser (Playwright + Chromium), with human-like timing, pauses, randomized viewports and anti-detection protections.

The bot tracks what it has already sent (`progress.json`) and resumes from where it left off.

---

## What you need

### 1. Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Input data

The bots read **raw data scraped from Apify** — you need to run the immobiliare.it / subito.it scrapers on [apify.com](https://apify.com) and export the results as CSV.

Place the CSV file in the corresponding bot folder:

- **ImmobiliareBot/** → file `dataset_*.csv` (export from the immobiliare.it scraper)
- **SubitoBot/** → file `Subito_scraper*.csv` or `dataset_subito*.csv` (export from the subito.it scraper)

The bots automatically pick up the most recent CSV in the folder.

### 3. Login

On first launch the bot opens Chrome and asks you to log in manually on the target platform. The session is saved in `auth_state.json` and reused on subsequent runs.

---

## How to use them

From inside the bot folder (`ImmobiliareBot/` or `SubitoBot/`):

```bash
# Step 1 — generate messages from the Apify CSV
python generate_messages.py

# Step 2 — send the messages
python send_messages.py --total 400 --batch 50 --pause 20
```

See the `README.md` inside each folder for the full set of options.

---

## Editing texts and parameters

**Everything lives in the code.** There is no separate configuration interface for the message templates: signature, opening lines, pitch variants, business-filter keywords, etc. are **directly inside the `generate_messages.py` file** of each bot.

To edit them:

- Open `generate_messages.py` in the bot folder
- Search for the string you want to change (e.g. signature, message template, keywords)
- Edit it

Timing, rate-limit and browser parameters are configured in `config.yaml` inside each bot folder.

### Recommended: use Claude Code

To navigate the code and change things without having to understand everything manually, it's recommended to use **[Claude Code](https://claude.com/claude-code)** (or another AI with filesystem access). Just open it in the repo folder and ask things like:

- "Change the message signature from X to Y"
- "Add a new variant to the no-agency pitch"
- "Update the keywords used to filter out business advertisers"
- "Explain how the sending flow works"

The AI locates the right spots in the code and edits them for you.

---

## Repo structure

```
ImmobiliareBot/
  core/                  shared engine (browser, scheduler, engine)
  platforms/             platform-specific selectors
  generate_messages.py   step 1 — generates messages from the CSV
  send_messages.py       step 2 — sends the messages
  config.yaml            timing, rate limit, browser
  requirements.txt
  README.md

SubitoBot/
  generate_messages.py
  send_messages.py
  import_cookies.py      utility to import cookies from a browser export
  config.yaml
  requirements.txt
  README.md
```

---

## Notes

- The bots use anti-detection protections (rotating user agents, random viewports, hidden `navigator.webdriver`, character-by-character typing, gradual scrolling, etc.).
- Rate limiting defaults are conservative. Pushing past the limits increases the risk of being blocked.
- Using a **VPN** is recommended to spread sessions across different IPs.
- Files containing personal data, login sessions, datasets and outputs are excluded via `.gitignore` — see the file at the repo root.
