# SubitoBot — Guida operativa

## Come funziona

Il bot si compone di due step eseguiti in sequenza:

```
[Step 1]  generate_messages.py   →   crea listings_ready.csv
[Step 2]  send_messages.py       →   invia i messaggi su subito.it
```

> Solo gli annunci di **privati** vengono processati — le aziende sono automaticamente escluse.

Il motore condivide lo stesso core di ImmobiliareBot (`core/engine.py`, `core/browser.py`, `core/scheduler.py`) con tutte le protezioni anti-detection integrate.

---

## Step 1 — Generare i messaggi

```bash
python generate_messages.py
```

**Input:** un file `Subito_scraper*.csv` nella stessa cartella (esportato da Apify).
**Output:** `listings_ready.csv` con i messaggi personalizzati pronti all'invio.

Alla fine stampa un'anteprima dei primi 3 messaggi per controllo rapido.

---

## Step 2 — Inviare i messaggi

```bash
python send_messages.py
```

**Prima esecuzione:** si apre Chrome, fai login su subito.it manualmente, poi torna al terminale e premi **ENTER**. La sessione viene salvata e non ti verra' richiesta di nuovo.

**Opzioni:**

| Opzione | Default | Descrizione |
|---|---|---|
| `--total N` | 0 (tutti) | Totale messaggi da inviare |
| `--batch N` | 50 | Messaggi per batch prima della pausa inter-sessione |
| `--pause N` | 20 | Minuti di pausa tra un batch e l'altro |
| `--dry-run` | off | Simula senza inviare (mostra anteprima) |
| `--config PATH` | `config.yaml` | File di configurazione personalizzato |

### Esempi

```bash
# Riprende da dove era rimasto (tutti i pending)
python send_messages.py

# 400 messaggi, batch da 50, pausa 20 min tra batch
python send_messages.py --total 400 --batch 50 --pause 20

# Simulazione senza invio
python send_messages.py --dry-run --total 100
```

Il bot **riprende automaticamente** da dove si era fermato (tiene traccia in `progress.json`).

---

## Anti-detection e comportamento umano

Tutto gestito automaticamente dal core condiviso + `config.yaml`:

**Browser fingerprint:**
- User agent Chrome rotanti (4 versioni reali)
- Viewport randomizzato ad ogni sessione
- Flag `navigator.webdriver` nascosto
- Plugins e languages simulati
- Chrome runtime iniettato
- `AutomationControlled` disabilitato

**Interazioni umane:**
- Click con offset casuale dal centro dell'elemento
- Digitazione con velocita' variabile (40-130ms/carattere) + pause "di pensiero"
- Scroll graduale che simula la lettura dell'annuncio
- Pause random tra ogni step (caricamento, lettura, compilazione)

**Rate limiting:**
- Delay gaussiano tra messaggi (25-55s di default)
- Pausa lunga ogni 4-7 messaggi (1-3 minuti)
- Limite orario (25 msg/h) e giornaliero (100 msg/giorno)
- Cooldown progressivo dopo errore (backoff esponenziale)
- Pausa tra batch (default 20 min con jitter)

Tutti i valori sono configurabili in `config.yaml`.

---

## Configurazione (`config.yaml`)

```yaml
# Timing tra messaggi (secondi)
delay_min: 25
delay_max: 55

# Pausa lunga ogni N messaggi
pause_every_min: 4
pause_every_max: 7
pause_duration_min: 60    # secondi
pause_duration_max: 180   # secondi

# Cooldown dopo errore
error_cooldown_min: 60
error_cooldown_max: 120

# Limiti di sicurezza
max_per_session: 0        # 0 = nessun limite
max_per_hour: 25
max_per_day: 100
max_consecutive_errors: 3

# Browser
headless: false
slow_mo: 50
typing_delay_min: 40
typing_delay_max: 130

# Viewport random
viewport_widths: [1280, 1366, 1440, 1536, 1600, 1920]
viewport_heights: [800, 900, 960, 1024, 1080]
```

---

## Caricare un nuovo dataset (nuova campagna)

1. Scarica il nuovo CSV da Apify e mettilo nella cartella del bot
2. **Elimina** i file della sessione precedente:
   ```bash
   rm listings_ready.csv progress.json
   ```
   > Non eliminare `auth_state.json` — contiene il login e puoi riutilizzarlo.
3. Riesegui dallo Step 1:
   ```bash
   python generate_messages.py
   python send_messages.py --total 50
   ```

> **Nota:** se nella cartella ci sono piu' file CSV, lo script prende automaticamente il **piu' recente** tra quelli che matchano `Subito_scraper*.csv`, `Subito*.csv` o `dataset_subito*.csv`.

---

## Ricominciare da zero (reset completo)

Elimina questi file:

| File | Cosa contiene |
|---|---|
| `listings_ready.csv` | Annunci + messaggi generati |
| `progress.json` | Traccia degli invii effettuati |
| `auth_state.json` | Sessione di login (elimina solo se vuoi rifare il login) |

Lascia i file CSV se vuoi riprocessarli, oppure sostituiscili con il nuovo export.

---

## File presenti nella cartella

```
Subito_scraper*.csv    → export raw da Apify (input)
listings_ready.csv     → annunci con messaggi generati (generato da Step 1)
progress.json          → stato degli invii (generato da Step 2)
auth_state.json        → sessione login Chrome (generato al primo avvio)
config.yaml            → configurazione timing, limiti e browser
screenshots/           → screenshot automatici in caso di errore
snapshots/             → HTML snapshots per debug
logs/                  → log strutturati JSONL per sessione
generate_messages.py   → Step 1
send_messages.py       → Step 2
requirements.txt       → dipendenze Python
```

---

## Differenze rispetto a ImmobiliareBot

| | ImmobiliareBot | SubitoBot |
|---|---|---|
| Sito target | immobiliare.it | subito.it |
| Campo URL nel CSV | `directLink` | `page_url` |
| Campo nome | `advertiser/supervisor/displayName` | `advertiser/name` |
| Filtro aziende | no | si (escluse automaticamente) |
| Flow invio | textarea visibile in pagina | click "Contatta" → textarea → "Invia" |

---

## Problemi comuni

**"Textarea non trovata"**
Subito potrebbe aver cambiato il layout del form di contatto. Controlla gli screenshot nella cartella `screenshots/` per capire cosa vede il bot. Potrebbe anche essere un annuncio scaduto.

**"Sessione scaduta"**
Elimina `auth_state.json` e rilancia — ti chiedera' di rifare il login.

**"Nessun CSV di Subito trovato"**
Il CSV di Apify non e' nella stessa cartella dello script. Spostalo li'. Il file deve chiamarsi `Subito_scraper*.csv` o simile.

**"Bloccato / rilevato blocco anti-bot"**
- Disconnetti e riconnetti il router (cambia IP)
- Aspetta qualche ora prima di riprovare
- Il bot si ferma automaticamente se rileva un blocco

**"Rate limit raggiunto"**
Il bot si mette in pausa automaticamente e riprende quando il limite orario/giornaliero lo permette.
