"""Versione di C.L.E.F.

Il numero sta qui. Quando GitHub costruisce una nuova versione (vedi tools/prepara_rilascio.py) controlla che il numero della versione da pubblicare
sia proprio questo: cosi' il programma installato, la release su GitHub e la schermata Stato dicono sempre lo stesso numero.
Il file VERSION accanto al programma (se c'e' ed e' valido) vince su questo: serve solo a chi vuole forzare un numero a mano.
"""
import re
from pathlib import Path

VERSIONE = "2.1.1"
_FORMA = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}$")


def versione(cartella=None):
    """Il numero di versione, per esempio «1.1.0»."""
    if cartella:
        try:
            v = (Path(cartella) / "VERSION").read_text(encoding="utf-8").strip()
            if _FORMA.match(v):
                return v
        except OSError:
            pass
    return VERSIONE
