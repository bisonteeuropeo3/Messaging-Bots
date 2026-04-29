# FreedHome Bot — Guida operativa

Bot per invio automatico messaggi su **immobiliare.it**, **subito.it** e **idealista.it**.
Ogni piattaforma ha la propria cartella con codice indipendente.

---

## Setup (una sola volta)

```bash
pip install -r requirements.txt
playwright install chromium
```

> Da questa versione il bot si attacca a una finestra **Chrome reale** (la tua) tramite CDP, invece di lanciare un Chromium separato. Bypassa la maggior parte delle detection anti-bot.

---

## Struttura cartelle

```
ImmobiliareBot/          ← codice immobiliare.it (qui)
  generate_messages.py
  send_messages.py
  config.yaml

SubitoBot/               ← codice subito.it
  generate_messages.py
  send_messages.py
  config.yaml

IdealistaBot/            ← codice idealista.it
  generate_messages.py
  send_messages.py
  config.yaml

core/                    ← motore condiviso (non toccare)
platforms/               ← selettori per piattaforma (non toccare)
```

---

## Come usare: 3 passi

### Passo 1 — Genera i messaggi

Metti il CSV di Apify nella cartella della piattaforma, poi:

```bash
# Immobiliare
python generate_messages.py

# Subito
cd SubitoBot && python generate_messages.py

# Idealista
cd IdealistaBot && python generate_messages.py
```

### Passo 2 — Apri Chrome con la porta di debug

Da terminale (Windows / macOS / Linux):

```bash
python start_chrome.py
```

In alternativa su Windows: **doppio click su `start_chrome.bat`**.

Si apre una finestra Chrome dedicata al bot, su un profilo separato:
- Windows: `C:\chrome-bot-profile`
- macOS / Linux: `~/chrome-bot-profile`

La prima volta fai login a immobiliare.it / subito.it / idealista.it manualmente in quella finestra. Da li' in poi il login resta salvato.

> **Lascia quella finestra Chrome aperta** durante l'invio. Se la chiudi, il bot si disconnette.

In alternativa, comando Chrome diretto:
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-bot-profile"

# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-bot-profile"
```

### Passo 3 — Invia i messaggi

```bash
python send_messages.py --total 400 --batch 50 --pause 20
```

**Questo e' tutto.** Il bot:
- Invia 50 messaggi
- Pausa 20 minuti
- Invia altri 50
- Pausa 20 minuti
- ...ripete fino a 400 totali
- Tu non devi fare nulla, va tutto in automatico

---

## IL COMANDO CHE TI SERVE

Per mandare 400 messaggi in automatico senza toccare nulla:

```bash
python send_messages.py --total 400 --batch 50 --pause 20
```

Cosa fa concretamente:
- **8 batch da 50 messaggi** ciascuno
- **20 minuti di pausa** tra un batch e l'altro
- Dentro ogni batch: **25-55 secondi** tra un messaggio e l'altro
- Ogni **4-7 messaggi**: **pausa lunga 2-5 minuti** (simula lettura)
- **Tempo totale stimato: ~6-7 ore** (perfetto per una giornata)

### Prima di lanciare per davvero, controlla col dry-run:

```bash
python send_messages.py --dry-run --total 400 --batch 50 --pause 20
```

---

## Opzioni disponibili

| Opzione | Default | Descrizione |
|---|---|---|
| `--total N` | tutti | Totale messaggi da inviare |
| `--batch N` | 50 | Quanti messaggi per batch |
| `--pause N` | 20 | Minuti di pausa tra batch |
| `--dry-run` | off | Simula senza inviare |
| `--config file` | config.yaml | Config personalizzata |

### Esempi

```bash
# Sessione veloce: 100 messaggi, batch da 25, pausa 15 min
python send_messages.py --total 100 --batch 25 --pause 15

# Sessione sicura (sito aggressivo): batch piccoli, pause lunghe
python send_messages.py --total 200 --batch 30 --pause 30

# Riprende da dove era (nessun limite)
python send_messages.py
```

---

## Consigli anti-blocco

### Cosa fa il bot automaticamente

- Delay 25-55s tra messaggi (distribuzione gaussiana)
- Pausa lunga 2-5 min ogni 4-7 messaggi
- Digitazione carattere per carattere (40-130ms)
- Scroll graduale prima di interagire
- Click con offset casuale
- Viewport e user-agent randomizzati
- Anti-fingerprinting (navigator.webdriver nascosto)
- Stop automatico se bloccato
- Cooldown progressivo dopo errori

### Cosa devi fare tu

1. **Usa VPN** — cambia IP prima di ogni sessione (o almeno una volta al giorno)
2. **Distribuisci nel tempo** — non fare 400 messaggi tutti sulla stessa piattaforma
3. **Varia gli orari** — non partire sempre alle 9:00
4. **Se bloccato** — aspetta 4-6 ore, cambia IP, riparti

### Schema giornaliero consigliato (300+ messaggi/giorno)

| Ora | Piattaforma | Comando |
|---|---|---|
| 9:00 | Immobiliare | `python send_messages.py --total 100 --batch 50 --pause 20` |
| 12:00 | Subito | `cd SubitoBot && python send_messages.py --total 100 --batch 50 --pause 20` |
| 15:00 | Idealista | `cd IdealistaBot && python send_messages.py --total 100 --batch 30 --pause 25` |

Totale: 300 messaggi, distribuiti su 3 piattaforme, ~8 ore.

> Per Idealista usa batch piu' piccoli (30) e pause piu' lunghe (25 min) perche' e' la piattaforma piu' aggressiva con i captcha.

---

## Nuova campagna

1. Metti il nuovo CSV nella cartella giusta
2. Elimina i vecchi file:
   ```bash
   rm listings_ready.csv progress.json
   ```
3. Apri Chrome con `python start_chrome.py` (o `start_chrome.bat` su Windows), poi:
   ```bash
   python generate_messages.py
   python send_messages.py --total 400 --batch 50 --pause 20
   ```

> NON eliminare la cartella `C:\chrome-bot-profile` (Windows) o `~/chrome-bot-profile` (macOS/Linux) — contiene il login Chrome salvato.

---

## Configurazione (config.yaml)

Ogni cartella ha il suo `config.yaml`. Modifica i valori per regolare il comportamento:

```yaml
delay_min: 25          # secondi tra messaggi
delay_max: 55
pause_every_min: 4     # pausa lunga ogni N messaggi
pause_every_max: 7
pause_duration_min: 120  # durata pausa (secondi)
pause_duration_max: 300
max_per_hour: 25       # limite orario
max_per_day: 100       # limite giornaliero
```

### Profilo "aggressivo" (a tuo rischio)
```yaml
delay_min: 15
delay_max: 30
max_per_hour: 40
max_per_day: 200
```

### Profilo "ultra-sicuro" (idealista)
```yaml
delay_min: 40
delay_max: 70
pause_duration_min: 180
pause_duration_max: 420
max_per_hour: 15
max_per_day: 60
```

---

## Problemi comuni

| Problema | Soluzione |
|---|---|
| "BLOCCATO" | Cambia IP (VPN), aspetta 4-6h, riparti |
| `ECONNREFUSED 9222` | Chrome non aperto con la porta di debug — lancia `python start_chrome.py` |
| `ECONNREFUSED ::1:9222` | `cdp_url` usa `localhost`, sostituisci con `127.0.0.1` in `config.yaml` |
| "Login richiesto" / "non sei loggato" | Apri Chrome via `python start_chrome.py`, fai login manualmente, rilancia il bot |
| "Textarea non trovata" | Annuncio scaduto o layout cambiato, guarda `snapshots/` |
| "limite orario raggiunto" | Aspetta 1 ora o modifica `max_per_hour` |
| "Nessun CSV trovato" | Metti il CSV nella cartella giusta |
| Il bot non parte | `pip install -r requirements.txt && playwright install chromium` |
| Chrome chiuso a meta' campagna | Riapri con `python start_chrome.py`, rilancia `send_messages.py` (riprende da `progress.json`) |

---

## File generati (non toccare)

| File | Cosa contiene |
|---|---|
| `listings_ready.csv` | Messaggi pronti all'invio |
| `progress.json` | Traccia di cosa e' stato inviato |
| `start_chrome.py` / `start_chrome.bat` | Launcher Chrome con porta di debug (Python cross-platform / batch Windows) |
| `logs/` | Log dettagliati per sessione (JSONL) |
| `snapshots/` | Screenshot e HTML quando qualcosa va storto |
| `C:\chrome-bot-profile\` | Profilo Chrome dedicato al bot (login, cookie, ecc.) |

> Il vecchio file `auth_state.json` non e' piu' usato — puoi eliminarlo se esiste.

---

## Configurazione Chrome (config.yaml)

Due modalita' disponibili in [config.yaml](config.yaml):

### Modalita' attiva: attach a Chrome esistente (consigliata)
```yaml
cdp_url: "http://127.0.0.1:9222"
```
Il bot si attacca alla finestra Chrome aperta con `python start_chrome.py` (o `start_chrome.bat`). Migliore stealth — usa il tuo Chrome reale, fingerprint identico.

### Modalita' alternativa: profilo persistente automatico
```yaml
cdp_url: ""
user_data_dir: ""    # vuoto = usa ./chrome_profile/
```
Il bot apre Chrome da solo con un profilo dedicato. Non serve `start_chrome.bat`. Buona stealth ma il profilo e' "fresco" (no extensions, no history reale).
