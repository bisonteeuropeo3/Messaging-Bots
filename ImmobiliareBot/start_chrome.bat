@echo off
REM Avvia Chrome con la porta di debug attiva, in un profilo separato dal tuo daily Chrome.
REM Dopo che si apre, fai login su immobiliare.it (e idealista/subito se vuoi).
REM Lascia questa finestra aperta mentre il bot lavora.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-bot-profile" https://www.immobiliare.it/login/
