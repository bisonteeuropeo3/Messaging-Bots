# SubitoBot — Guida operativa

Bot per invio automatico messaggi su **subito.it**.

> Questa versione usa la modalita' **CDP attach**: apri Chrome con un profilo dedicato, fai login una volta, e il bot si attacca alla finestra esistente. Niente piu' `auth_state.json`, niente piu' login interattivo da terminale.

---

## Setup (una sola volta)

```bash
pip install -r requirements.txt
playwright install chromium
```

> Solo gli annunci di **privati** vengono processati — le aziende sono escluse automaticamente.

---

## Flusso a 3 step

### Step 1 — Genera i messaggi

Metti il CSV di Apify nella cartella, poi:

```bash
python generate_messages.py
```

**Input:** un file `Subito_scraper*.csv` (export Apify) nella stessa cartella.
**Output:** `listings_ready.csv` con messaggi personalizzati pronti.

Alla fine stampa un'anteprima dei primi 3 messaggi per controllo.

---

### Step 2 — Apri Chrome con la porta di debug

#### Windows
Doppio click su **`start_chrome.bat`**, oppure da terminale:
```bash
python start_chrome.py
```

#### macOS
Doppio click su **`start_chrome.command`** (la prima volta: `chmod +x start_chrome.command`),
oppure da terminale:
```bash
python start_chrome.py
```

#### Linux
```bash
python start_chrome.py
```

Si apre una finestra Chrome dedicata al bot, su un profilo separato:
- Windows: `C:\chrome-bot-profile`
- macOS / Linux: `~/chrome-bot-profile`

**La prima volta** fai login a subito.it manualmente in quella finestra. Da li' in poi il login resta salvato — non te lo richiede piu'.

> **Lascia quella finestra Chrome aperta** mentre il bot lavora. Se la chiudi, il bot si disconnette.

Comando Chrome diretto (alternativa, se gli script non funzionano):
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-bot-profile" https://areariservata.subito.it/login_form

# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-bot-profile" https://areariservata.subito.it/login_form
```

---

### Step 3 — Invia i messaggi

```bash
python send_messages.py --total 400 --batch 50 --pause 20
```

Il bot:
- Si attacca alla finestra Chrome aperta allo Step 2
- Verifica che sei loggato (cookies + redirect check)
- Invia 50 messaggi
- Pausa 20 minuti
- Ripete fino a 400 totali

Riprende automaticamente da dove si era fermato (traccia in `progress.json`).

---

## Opzioni `send_messages.py`

| Opzione | Default | Descrizione |
|---|---|---|
| `--total N` | 0 (tutti) | Totale messaggi da inviare |
| `--batch N` | 50 | Messaggi per batch prima della pausa inter-sessione |
| `--pause N` | 20 | Minuti di pausa tra batch |
| `--dry-run` | off | Simula senza inviare (mostra anteprima) |
| `--config PATH` | `config.yaml` | File configurazione personalizzato |

### Esempi

```bash
# Riprende da dove era rimasto
python send_messages.py

# 400 messaggi, batch da 50, pausa 20 min
python send_messages.py --total 400 --batch 50 --pause 20

# Sessione veloce
python send_messages.py --total 100 --batch 25 --pause 15

# Sessione ultra-sicura (rate limit aggressivo da subito)
python send_messages.py --total 200 --batch 30 --pause 30

# Simulazione senza invio
python send_messages.py --dry-run --total 100
```

---

## Anti-detection e comportamento umano

Tutto gestito automaticamente dal core condiviso + `config.yaml`:

**Browser fingerprint:**
- Profilo Chrome reale (cookies, history, extensions tuoi) via CDP
- User agent e viewport del Chrome reale
- Flag `navigator.webdriver` nascosto
- `AutomationControlled` disabilitato

**Interazioni umane:**
- Click con offset casuale dal centro dell'elemento
- Digitazione carattere per carattere (40-130ms)
- Scroll graduale che simula la lettura
- Pause random tra ogni step

**Rate limiting:**
- Delay gaussiano tra messaggi (25-55s di default)
- Pausa lunga ogni 4-7 messaggi (1-3 min)
- Limite orario e giornaliero
- Cooldown progressivo dopo errore (backoff)
- Pausa tra batch (default 20 min con jitter)

Tutti i valori sono configurabili in [config.yaml](config.yaml).

---

## Configurazione Chrome (`config.yaml`)

Due modalita' disponibili:

### Modalita' attiva: attach a Chrome esistente (consigliata)
```yaml
cdp_url: "http://127.0.0.1:9222"
```
Il bot si attacca alla finestra Chrome aperta con `start_chrome.py`. Migliore stealth — Chrome reale, fingerprint identico.

### Modalita' alternativa: profilo persistente automatico
```yaml
cdp_url: ""
user_data_dir: ""    # vuoto = usa ./chrome_profile/
```
Il bot lancia Chrome da solo con un profilo dedicato. Non serve `start_chrome.py`.

---

## Caricare un nuovo dataset (nuova campagna)

1. Scarica il nuovo CSV da Apify e mettilo nella cartella
2. Elimina i file della sessione precedente:
   ```bash
   # Windows
   del listings_ready.csv progress.json
   # macOS / Linux
   rm listings_ready.csv progress.json
   ```
3. Riesegui dallo Step 1:
   ```bash
   python generate_messages.py
   python send_messages.py --total 400 --batch 50 --pause 20
   ```

> NON eliminare la cartella `chrome-bot-profile` — contiene il login salvato.

> Se nella cartella ci sono piu' file CSV, lo script prende automaticamente il **piu' recente** tra quelli che matchano `Subito_scraper*.csv`, `Subito*.csv` o `dataset_subito*.csv`.

---

## File presenti nella cartella

```
Subito_scraper*.csv     → export raw da Apify (input)
listings_ready.csv      → annunci con messaggi (generato Step 1)
progress.json           → stato invii (generato Step 2)
config.yaml             → configurazione timing/limiti/browser
generate_messages.py    → Step 1
send_messages.py        → Step 2 / 3
start_chrome.py         → launcher Chrome cross-platform
start_chrome.bat        → launcher Chrome (Windows double-click)
start_chrome.command    → launcher Chrome (macOS double-click)
screenshots/            → screenshot in caso di errore
snapshots/              → HTML snapshot per debug
logs/                   → log JSONL per sessione
```

> Il vecchio `auth_state.json` non e' piu' usato — puoi eliminarlo se esiste.

---

## Problemi comuni

| Problema | Soluzione |
|---|---|
| "non sei loggato nel browser collegato" | Apri subito.it in `chrome-bot-profile` e fai login manualmente, poi rilancia |
| `ECONNREFUSED 9222` | Chrome non aperto con porta debug — lancia `start_chrome.py` |
| `ECONNREFUSED ::1:9222` | Sostituisci `localhost` con `127.0.0.1` in `cdp_url` |
| "Bottone Contatta non trovato" | Annuncio scaduto o layout cambiato — guarda `snapshots/` |
| "Bloccato / blocco anti-bot" | Cambia IP (VPN), aspetta 4-6h, riparti |
| "Limite orario raggiunto" | Aspetta 1 ora o modifica `max_per_hour` in `config.yaml` |
| "Nessun CSV trovato" | Metti il CSV nella cartella SubitoBot |
| Chrome chiuso a meta' campagna | Riapri con `start_chrome.py`, rilancia (riprende da `progress.json`) |
| `start_chrome.command` non si apre (macOS) | `chmod +x start_chrome.command` |

---

## Differenze rispetto a ImmobiliareBot

| | ImmobiliareBot | SubitoBot |
|---|---|---|
| Sito target | immobiliare.it | subito.it |
| Campo URL nel CSV | `directLink` | `page_url` |
| Filtro aziende | no | si (escluse automaticamente) |
| Flow invio | textarea visibile in pagina | click "Contatta" → textarea → "Invia" |
