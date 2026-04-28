"""
Invio messaggi su subito.it

Uso:
  python send_messages.py                                    # riprende da dove era
  python send_messages.py --total 400 --batch 50 --pause 20  # 400 msg automatici
  python send_messages.py --dry-run --total 100              # simula senza inviare
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMMOBILIARE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "ImmobiliareBot")
sys.path.insert(0, IMMOBILIARE_DIR)

import argparse
from platforms.subito import Subito
from core.engine import run_campaign


def main():
    parser = argparse.ArgumentParser(description="Invio messaggi su subito.it")
    parser.add_argument("--total", type=int, default=0,
                        help="Totale messaggi da inviare (0 = tutti)")
    parser.add_argument("--batch", type=int, default=50,
                        help="Messaggi per batch (default: 50)")
    parser.add_argument("--pause", type=float, default=20,
                        help="Minuti di pausa tra batch (default: 20)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simula senza inviare")
    parser.add_argument("--config", type=str,
                        default=os.path.join(SCRIPT_DIR, "config.yaml"),
                        help="File configurazione YAML")
    args = parser.parse_args()

    run_campaign(Subito(), SCRIPT_DIR, args)


if __name__ == "__main__":
    main()
