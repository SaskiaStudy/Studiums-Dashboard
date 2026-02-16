"""
database.py – Persistenzschicht des Studenten-Dashboards (SQLite).

Dieses Modul kuemmert sich um das Speichern, Laden und Loeschen aller
Daten in einer SQLite-Datenbank. Die Struktur gliedert sich in:

    Repository-Klassen (je eine pro Entitaetstyp):
        - StudiengangRepository:  CRUD fuer Studiengaenge und Semester
        - ModulRepository:        CRUD fuer Module und Pruefungsleistungen
        - ZeiteintragRepository:  CRUD fuer Lerntermine und Lernsessions

    Fassade:
        - DatenbankManager:  Koordiniert die Repositories und stellt
                             eine einheitliche Schnittstelle fuer den
                             restlichen Code bereit.

Die Repositories werden dem DatenbankManager per Dependency Injection
uebergeben, sodass sie bei Bedarf (z. B. fuer Tests) ausgetauscht
werden koennen.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any

from models import (Studiengang, Semester, Modul, Pruefungsleistung,
                    Status, Lerntermin, Lernsession, ZeitEintrag)


# =====================================================================
# Repository-Klassen – je eine Klasse pro Entitaetstyp
# =====================================================================

class StudiengangRepository:
    """
    Repository fuer Studiengaenge und deren Semester.

    Bietet Methoden zum Speichern (INSERT / UPDATE), Laden und
    Loeschen von Studiengaengen inkl. der zugehoerigen Semester.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn: sqlite3.Connection = conn

    def speichern(self, studiengang: Studiengang) -> None:
        """
        Speichert oder aktualisiert einen Studiengang mit seinen Semestern.

        Neue Studiengaenge (id == None) werden per INSERT angelegt,
        bestehende per UPDATE aktualisiert. Die Semester werden jeweils
        komplett ersetzt (DELETE + INSERT), um Konsistenz zu gewaehrleisten.
        """
        cursor = self.conn.cursor()

        if studiengang.id is None:
            cursor.execute(
                "INSERT INTO studiengaenge (name, regelstudienzeit, zielschnitt) VALUES (?, ?, ?)",
                (studiengang.name, studiengang.regelstudienzeit, studiengang.zielschnitt)
            )
            studiengang.id = cursor.lastrowid
        else:
            cursor.execute(
                "UPDATE studiengaenge SET name=?, regelstudienzeit=?, zielschnitt=? WHERE id=?",
                (studiengang.name, studiengang.regelstudienzeit,
                 studiengang.zielschnitt, studiengang.id)
            )

        # Semester komplett ersetzen
        cursor.execute("DELETE FROM semester WHERE studiengang_id=?", (studiengang.id,))
        for sem in studiengang.semester_liste:
            cursor.execute(
                "INSERT INTO semester (nummer, start_datum, end_datum, studiengang_id) "
                "VALUES (?, ?, ?, ?)",
                (sem.nummer, sem.start_datum.isoformat(),
                 sem.end_datum.isoformat(), studiengang.id)
            )
            sem.id = cursor.lastrowid

        self.conn.commit()

    def laden_alle(self) -> List[Studiengang]:
        """Laedt alle Studiengaenge inkl. der zugehoerigen Semester aus der Datenbank."""
        cursor = self.conn.cursor()
        studiengaenge: List[Studiengang] = []

        cursor.execute("SELECT * FROM studiengaenge")
        for sg_zeile in cursor.fetchall():
            sg = Studiengang(
                sg_zeile['name'],
                sg_zeile['regelstudienzeit'],
                sg_zeile['zielschnitt']
            )
            sg.id = sg_zeile['id']

            # Zugehoerige Semester laden
            cursor.execute(
                "SELECT * FROM semester WHERE studiengang_id=? ORDER BY nummer",
                (sg.id,)
            )
            for sem_zeile in cursor.fetchall():
                sem = Semester(
                    sem_zeile['nummer'],
                    datetime.fromisoformat(sem_zeile['start_datum']),
                    datetime.fromisoformat(sem_zeile['end_datum'])
                )
                sem.id = sem_zeile['id']
                sg.semester_liste.append(sem)

            studiengaenge.append(sg)

        return studiengaenge

    def loeschen(self, sg_id: int) -> None:
        """Loescht einen Studiengang samt aller abhaengigen Daten (CASCADE)."""
        self.conn.execute("DELETE FROM studiengaenge WHERE id=?", (sg_id,))
        self.conn.commit()


class ModulRepository:
    """
    Repository fuer Module und deren Pruefungsleistungen.

    Bietet Methoden zum Speichern, Laden und Loeschen von Modulen
    sowie einzelner Pruefungsleistungen.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn: sqlite3.Connection = conn

    def speichern(self, modul: Modul, studiengang_id: int) -> None:
        """
        Speichert oder aktualisiert ein Modul inkl. neuer Pruefungsleistungen.

        Bereits gespeicherte Pruefungsleistungen (id != None) werden
        uebersprungen, nur neue werden eingefuegt.
        """
        cursor = self.conn.cursor()

        if modul.id is None:
            cursor.execute(
                "INSERT INTO module (titel, ects, status, geplantes_semester, "
                "studiengang_id) VALUES (?, ?, ?, ?, ?)",
                (modul.titel, modul.ects, modul.status.value,
                 modul.geplantes_semester, studiengang_id)
            )
            modul.id = cursor.lastrowid
        else:
            cursor.execute(
                "UPDATE module SET titel=?, ects=?, status=?, geplantes_semester=? "
                "WHERE id=?",
                (modul.titel, modul.ects, modul.status.value,
                 modul.geplantes_semester, modul.id)
            )

        # Nur neue Pruefungsleistungen einfuegen
        for pl in modul.pruefungsleistungen:
            if pl.id is None:
                cursor.execute(
                    "INSERT INTO pruefungsleistungen (note, versuchs_nummer, modul_id) "
                    "VALUES (?, ?, ?)",
                    (pl.note, pl.versuchs_nummer, modul.id)
                )
                pl.id = cursor.lastrowid

        self.conn.commit()

    def laden_fuer_studiengang(self, sg_id: int) -> List[Modul]:
        """Laedt alle Module eines Studiengangs inkl. Pruefungsleistungen."""
        cursor = self.conn.cursor()
        module: List[Modul] = []

        cursor.execute("SELECT * FROM module WHERE studiengang_id=?", (sg_id,))
        for mod_zeile in cursor.fetchall():
            modul = Modul(
                mod_zeile['titel'],
                mod_zeile['ects'],
                Status(mod_zeile['status']),
                mod_zeile['geplantes_semester']
            )
            modul.id = mod_zeile['id']

            # Pruefungsleistungen des Moduls laden
            cursor.execute(
                "SELECT * FROM pruefungsleistungen WHERE modul_id=? "
                "ORDER BY versuchs_nummer",
                (modul.id,)
            )
            for pl_zeile in cursor.fetchall():
                pl = Pruefungsleistung(pl_zeile['note'], pl_zeile['versuchs_nummer'])
                pl.id = pl_zeile['id']
                modul.pruefungsleistungen.append(pl)

            module.append(modul)

        return module

    def loeschen(self, modul_id: int) -> None:
        """Loescht ein Modul und seine Pruefungsleistungen (CASCADE)."""
        self.conn.execute("DELETE FROM module WHERE id=?", (modul_id,))
        self.conn.commit()

    def loeschen_pruefungsleistung(self, pl_id: int) -> None:
        """Loescht eine einzelne Pruefungsleistung anhand ihrer ID."""
        self.conn.execute("DELETE FROM pruefungsleistungen WHERE id=?", (pl_id,))
        self.conn.commit()


class ZeiteintragRepository:
    """
    Repository fuer Zeiteintraege (Lerntermine und Lernsessions).

    Der Typ (TERMIN oder SESSION) wird als String-Spalte gespeichert,
    sodass beim Laden automatisch das passende Objekt erzeugt wird.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn: sqlite3.Connection = conn

    def speichern(self, eintrag: ZeitEintrag) -> None:
        """
        Speichert oder aktualisiert einen Zeiteintrag.

        Lerntermine und Lernsessions werden anhand ihres Typs
        unterschieden und mit den jeweiligen Feldern gespeichert.
        """
        cursor = self.conn.cursor()

        ist_termin = isinstance(eintrag, Lerntermin)
        typ = 'TERMIN' if ist_termin else 'SESSION'

        if eintrag.id is None:
            # Neuen Eintrag einfuegen
            if ist_termin:
                cursor.execute(
                    "INSERT INTO zeiteintraege (typ, datum, start_zeit, "
                    "geplante_dauer, beschreibung, modul_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (typ, eintrag.datum.isoformat(), eintrag.start_zeit.isoformat(),
                     eintrag.geplante_dauer, eintrag.beschreibung, eintrag.modul_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO zeiteintraege (typ, datum, start_zeit, end_zeit, "
                    "tatsaechliche_dauer, modul_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (typ, eintrag.datum.isoformat(), eintrag.start_zeit.isoformat(),
                     eintrag.end_zeit.isoformat(), eintrag.tatsaechliche_dauer,
                     eintrag.modul_id)
                )
            eintrag.id = cursor.lastrowid
        else:
            # Bestehenden Eintrag aktualisieren
            if ist_termin:
                cursor.execute(
                    "UPDATE zeiteintraege SET datum=?, start_zeit=?, geplante_dauer=?, "
                    "beschreibung=?, modul_id=? WHERE id=?",
                    (eintrag.datum.isoformat(), eintrag.start_zeit.isoformat(),
                     eintrag.geplante_dauer, eintrag.beschreibung,
                     eintrag.modul_id, eintrag.id)
                )
            else:
                cursor.execute(
                    "UPDATE zeiteintraege SET datum=?, start_zeit=?, end_zeit=?, "
                    "tatsaechliche_dauer=?, modul_id=? WHERE id=?",
                    (eintrag.datum.isoformat(), eintrag.start_zeit.isoformat(),
                     eintrag.end_zeit.isoformat(), eintrag.tatsaechliche_dauer,
                     eintrag.modul_id, eintrag.id)
                )

        self.conn.commit()

    def laden_alle(self) -> List[ZeitEintrag]:
        """
        Laedt alle Zeiteintraege und erzeugt je nach Typ
        ein Lerntermin- oder Lernsession-Objekt.
        """
        cursor = self.conn.cursor()
        zeiteintraege: List[ZeitEintrag] = []

        cursor.execute("SELECT * FROM zeiteintraege ORDER BY datum")
        for zeile in cursor.fetchall():
            datum = datetime.fromisoformat(zeile['datum'])
            start = datetime.fromisoformat(zeile['start_zeit'])
            m_id = zeile['modul_id']

            if zeile['typ'] == 'TERMIN':
                eintrag = Lerntermin(
                    datum, start, zeile['geplante_dauer'],
                    zeile['beschreibung'], m_id
                )
            else:
                ende = datetime.fromisoformat(zeile['end_zeit'])
                eintrag = Lernsession(datum, start, ende, m_id)

            eintrag.id = zeile['id']
            zeiteintraege.append(eintrag)

        return zeiteintraege

    def loeschen(self, eintrag_id: int) -> None:
        """Loescht einen Zeiteintrag anhand seiner ID."""
        self.conn.execute("DELETE FROM zeiteintraege WHERE id=?", (eintrag_id,))
        self.conn.commit()


# =====================================================================
# DatenbankManager – Fassade fuer die gesamte Persistenzschicht
# =====================================================================

class DatenbankManager:
    """
    Zentrale Fassade fuer alle Datenbankoperationen.

    Koordiniert die drei spezialisierten Repositories und stellt
    eine einheitliche Schnittstelle fuer die Anwendung bereit.
    Die Repositories koennen per Konstruktor injiziert werden;
    werden keine uebergeben, erstellt der Manager Standard-Instanzen.
    """

    def __init__(self, dateiname: str = "dashboard.db",
                 studiengang_repo: Optional[StudiengangRepository] = None,
                 modul_repo: Optional[ModulRepository] = None,
                 zeiteintrag_repo: Optional[ZeiteintragRepository] = None) -> None:
        """
        Parameter:
            dateiname:         Pfad zur SQLite-Datenbankdatei
            studiengang_repo:  Optional – Repository fuer Studiengaenge
            modul_repo:        Optional – Repository fuer Module
            zeiteintrag_repo:  Optional – Repository fuer Zeiteintraege
        """
        self.dateiname: str = dateiname
        self.conn: Optional[sqlite3.Connection] = None
        self._sg_repo: Optional[StudiengangRepository] = studiengang_repo
        self._modul_repo: Optional[ModulRepository] = modul_repo
        self._zeit_repo: Optional[ZeiteintragRepository] = zeiteintrag_repo

    def verbinden(self) -> None:
        """
        Stellt die Verbindung zur SQLite-Datenbank her, aktiviert
        Fremdschluessel-Unterstuetzung und erstellt die Tabellen.

        Falls keine Repositories injiziert wurden, werden hier
        Standard-Instanzen erzeugt.
        """
        self.conn = sqlite3.connect(self.dateiname)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        self._tabellen_erstellen()

        # Standard-Repositories erstellen, falls nicht injiziert
        if self._sg_repo is None:
            self._sg_repo = StudiengangRepository(self.conn)
        if self._modul_repo is None:
            self._modul_repo = ModulRepository(self.conn)
        if self._zeit_repo is None:
            self._zeit_repo = ZeiteintragRepository(self.conn)

    def _tabellen_erstellen(self) -> None:
        """Erstellt alle Datenbank-Tabellen, falls sie noch nicht existieren."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS studiengaenge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                regelstudienzeit INTEGER DEFAULT 6,
                zielschnitt REAL DEFAULT 2.0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semester (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nummer INTEGER NOT NULL,
                start_datum TEXT NOT NULL,
                end_datum TEXT NOT NULL,
                studiengang_id INTEGER NOT NULL,
                FOREIGN KEY (studiengang_id)
                    REFERENCES studiengaenge(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS module (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titel TEXT NOT NULL,
                ects INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'OFFEN',
                geplantes_semester INTEGER DEFAULT 1,
                studiengang_id INTEGER NOT NULL,
                FOREIGN KEY (studiengang_id)
                    REFERENCES studiengaenge(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pruefungsleistungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note REAL NOT NULL,
                versuchs_nummer INTEGER NOT NULL,
                modul_id INTEGER NOT NULL,
                FOREIGN KEY (modul_id)
                    REFERENCES module(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zeiteintraege (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                typ TEXT NOT NULL,
                datum TEXT NOT NULL,
                start_zeit TEXT NOT NULL,
                end_zeit TEXT,
                geplante_dauer INTEGER,
                tatsaechliche_dauer INTEGER,
                beschreibung TEXT,
                modul_id INTEGER,
                FOREIGN KEY (modul_id)
                    REFERENCES module(id) ON DELETE SET NULL
            )
        """)

        self.conn.commit()

    # --- Oeffentliche Methoden (delegieren an Repositories) ---

    def speichern(self, studiengang: Studiengang) -> None:
        """Speichert einen Studiengang mit allen zugehoerigen Modulen."""
        if self.conn is None:
            self.verbinden()

        self._sg_repo.speichern(studiengang)

        for modul in studiengang.module:
            self._modul_repo.speichern(modul, studiengang.id)

    def speichern_zeiteintrag(self, eintrag: ZeitEintrag) -> None:
        """Speichert einen Zeiteintrag (Lerntermin oder Lernsession)."""
        if self.conn is None:
            self.verbinden()
        self._zeit_repo.speichern(eintrag)

    def loeschen_zeiteintrag(self, eintrag_id: int) -> None:
        """Loescht einen Zeiteintrag anhand seiner ID."""
        if self.conn is None:
            self.verbinden()
        self._zeit_repo.loeschen(eintrag_id)

    def loeschen_modul(self, modul_id: int) -> None:
        """Loescht ein Modul und seine Pruefungsleistungen."""
        if self.conn is None:
            self.verbinden()
        self._modul_repo.loeschen(modul_id)

    def loeschen_studiengang(self, sg_id: int) -> None:
        """Loescht einen Studiengang und alle zugehoerigen Daten."""
        if self.conn is None:
            self.verbinden()
        self._sg_repo.loeschen(sg_id)

    def loeschen_pruefungsleistung(self, pl_id: int) -> None:
        """Loescht eine einzelne Pruefungsleistung."""
        if self.conn is None:
            self.verbinden()
        self._modul_repo.loeschen_pruefungsleistung(pl_id)

    def laden(self) -> Dict[str, Any]:
        """
        Laedt alle Daten aus der Datenbank.

        Rueckgabe: Dictionary mit den Schluesseln
            'studiengaenge' -> Liste aller Studiengang-Objekte (inkl. Module)
            'zeiteintraege' -> Liste aller ZeitEintrag-Objekte
        """
        if self.conn is None:
            self.verbinden()

        # Studiengaenge mit Semestern laden
        studiengaenge = self._sg_repo.laden_alle()

        # Module fuer jeden Studiengang nachladen
        for sg in studiengaenge:
            sg.module = self._modul_repo.laden_fuer_studiengang(sg.id)

        # Zeiteintraege laden
        zeiteintraege = self._zeit_repo.laden_alle()

        return {"studiengaenge": studiengaenge, "zeiteintraege": zeiteintraege}

    def schliessen(self) -> None:
        """Schliesst die Datenbankverbindung."""
        if self.conn:
            self.conn.close()
