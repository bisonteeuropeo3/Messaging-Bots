#!/bin/bash
# Avvia Chrome con la porta di debug attiva, in un profilo separato dal tuo daily Chrome.
# Dopo che si apre, fai login su immobiliare.it.
# Lascia questa finestra aperta mentre il bot lavora.
#
# Su macOS: doppio click su questo file (potresti dover dare permessi: chmod +x start_chrome.command).

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-bot-profile" \
  https://www.immobiliare.it/login/ &
