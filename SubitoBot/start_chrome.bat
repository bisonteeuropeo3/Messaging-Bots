@echo off
REM Avvia Chrome con la porta di debug attiva, in un profilo separato dal tuo daily Chrome.
REM Dopo che si apre, fai login su subito.it.
REM Lascia questa finestra aperta mentre il bot lavora.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-bot-profile" https://areariservata.subito.it/login_form
