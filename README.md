# Messaging Bots — Immobiliare & Subito

Bot per l'invio automatico di messaggi personalizzati su **immobiliare.it** e **subito.it**.
Pensati per contattare in massa gli inserzionisti di annunci immobiliari, simulando comportamento umano per evitare blocchi anti-bot.

Il repo contiene due bot indipendenti, uno per piattaforma:

```
ImmobiliareBot/   → bot per immobiliare.it
SubitoBot/        → bot per subito.it
```

---

## A cosa servono

Ogni bot fa due cose:

1. **Genera messaggi personalizzati** a partire da un dataset di annunci (nome dell'inserzionista, indirizzo, prezzo, ecc.).
2. **Invia i messaggi** in automatico tramite browser (Playwright + Chromium), con timing umano, pause, viewport randomizzati e protezioni anti-detection.

Il bot tiene traccia di cosa ha già inviato (`progress.json`) e riprende da dove si era fermato.

---

## Cosa serve per usarli

### 1. Dipendenze

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Dati di input

I bot leggono i dati grezzi presi da **Apify** — vanno scaricati gli scraper di immobiliare.it / subito.it dalla piattaforma [apify.com](https://apify.com) ed esportati in CSV.

Il file CSV va messo nella cartella del bot corrispondente:

- **ImmobiliareBot/** → file `dataset_*.csv` (export dello scraper di immobiliare.it)
- **SubitoBot/** → file `Subito_scraper*.csv` o `dataset_subito*.csv` (export dello scraper di subito.it)

I bot prendono automaticamente il CSV piu' recente nella cartella.

### 3. Login

Al primo avvio il bot apre Chrome e ti chiede di fare login manualmente sulla piattaforma. La sessione viene salvata in `auth_state.json` e riutilizzata alle esecuzioni successive.

---

## Come si usano

Da dentro la cartella del bot (`ImmobiliareBot/` o `SubitoBot/`):

```bash
# Step 1 — genera i messaggi a partire dal CSV di Apify
python generate_messages.py

# Step 2 — invia i messaggi
python send_messages.py --total 400 --batch 50 --pause 20
```

Vedi i `README.md` dentro ciascuna cartella per le opzioni complete.

---

## Modificare i testi e i parametri

**Tutto e' nel codice.** Non c'e' un'interfaccia di configurazione separata per i template dei messaggi: la firma, le frasi di apertura, le varianti del pitch, le keyword di filtro aziende, ecc. sono **direttamente nei file `generate_messages.py`** di ciascun bot.

Per modificarli:

- Apri `generate_messages.py` nella cartella del bot
- Cerca la stringa che vuoi cambiare (es. firma, template messaggio, parole chiave)
- Modificala

I parametri di timing, rate limit e browser si modificano invece in `config.yaml` di ciascun bot.

### Consigliato: usa Claude Code

Per orientarti nel codice e modificare le cose senza dover capire tutto a mano, conviene usare **[Claude Code](https://claude.com/claude-code)** (o un'altra IA con accesso al filesystem). Basta aprirla nella cartella del repo e chiedere cose tipo:

- "Cambia la firma dei messaggi da X a Y"
- "Aggiungi una variante al pitch sull'agenzia"
- "Modifica le parole chiave per filtrare le aziende"
- "Spiegami come funziona il flusso di invio"

L'IA trova i punti giusti nel codice e li modifica al posto tuo.

---

## Struttura del repo

```
ImmobiliareBot/
  core/                  motore condiviso (browser, scheduler, engine)
  platforms/             selettori specifici per piattaforma
  generate_messages.py   step 1 — genera i messaggi dal CSV
  send_messages.py       step 2 — invia i messaggi
  config.yaml            timing, rate limit, browser
  requirements.txt
  README.md

SubitoBot/
  generate_messages.py
  send_messages.py
  import_cookies.py      utility per importare cookie da export browser
  config.yaml
  requirements.txt
  README.md
```

---

## Note

- I bot usano protezioni anti-detection (user agent rotanti, viewport random, `navigator.webdriver` nascosto, digitazione carattere per carattere, scroll graduale, ecc.).
- Il rate limiting e' configurato in modo conservativo di default. Spingere oltre i limiti aumenta il rischio di blocco.
- L'uso di una **VPN** e' consigliato per distribuire le sessioni su IP diversi.
- I file con dati personali, sessioni di login, dataset e output sono esclusi via `.gitignore` — vedi il file alla radice del repo.
