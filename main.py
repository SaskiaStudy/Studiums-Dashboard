"""
main.py – Einstiegspunkt fuer das Studenten-Dashboard.

Hier werden alle Komponenten zusammengebaut und die Anwendung gestartet:
    1. DatenbankManager erstellen und Verbindung herstellen
    2. BenutzerMenue mit dem DatenbankManager initialisieren
    3. Interaktive Hauptschleife starten

Verwendung:
    python main.py
"""

import sqlite3
from database import (DatenbankManager, StudiengangRepository,
                      ModulRepository, ZeiteintragRepository)
from ui import BenutzerMenue


def main() -> None:
    """
    Hauptfunktion: Baut die Anwendung zusammen und startet das Menue.

    Der DatenbankManager erhaelt den Dateinamen der SQLite-Datenbank
    und erstellt beim Verbinden automatisch die benoetigten Repositories.
    """
    dateiname = "dashboard.db"

    # Datenbank-Fassade erstellen und Verbindung herstellen
    db_manager = DatenbankManager(dateiname)
    db_manager.verbinden()

    # Benutzeroberflaeche initialisieren und starten
    menue = BenutzerMenue(db_manager)
    menue.start()


if __name__ == "__main__":
    main()
