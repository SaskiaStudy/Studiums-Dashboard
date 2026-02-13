import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Any
from models import Studiengang, Semester, Modul, Pruefungsleistung, Status, Lerntermin, Lernsession, ZeitEintrag # type: ignore

class DatabaseManager:
    """Kapselt SQLite-Verbindung und Persistenz."""

    def __init__(self, db_name="dashboard.db"):
        self.db_name = db_name
        self.conn: Optional[sqlite3.Connection] = None

    def verbinden(self):
        """Stellt Verbindung zur Datenbank her."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON") # aktiviere kaskadierendes Löschen
        self.conn = conn

    def close(self):
        conn = self.conn
        if conn:
            conn.close()

    def tabellen_erstellen(self):
        """Erstellt alle notwendigen Tabellen, falls nicht vorhanden."""
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn is None: raise ConnectionError("Datenbankverbindung fehlt.")
        cursor = conn.cursor()

        # Studiengang
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS studiengaenge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                regelstudienzeit INTEGER DEFAULT 6,
                zielschnitt REAL DEFAULT 2.0
            )
        """)
        # Column hinzufügen falls es fehlt
        cursor.execute("PRAGMA table_info(studiengaenge)")
        cols_sg = [col[1] for col in cursor.fetchall()]
        if 'regelstudienzeit' not in cols_sg:
            cursor.execute("ALTER TABLE studiengaenge ADD COLUMN regelstudienzeit INTEGER DEFAULT 6")
        if 'zielschnitt' not in cols_sg:
            cursor.execute("ALTER TABLE studiengaenge ADD COLUMN zielschnitt REAL DEFAULT 2.0")

        # Einstellungen für die Sitzungsspeicherung
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Semester
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semester (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nummer INTEGER NOT NULL,
                start_datum TEXT NOT NULL,
                end_datum TEXT NOT NULL,
                studiengang_id INTEGER,
                FOREIGN KEY(studiengang_id) REFERENCES studiengaenge(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("PRAGMA table_info(semester)")
        if 'studiengang_id' not in [col[1] for col in cursor.fetchall()]:
            cursor.execute("ALTER TABLE semester ADD COLUMN studiengang_id INTEGER")

        # Module
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS module (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titel TEXT NOT NULL,
                ects INTEGER NOT NULL,
                status TEXT NOT NULL,
                geplantes_semester INTEGER DEFAULT 1,
                studiengang_id INTEGER,
                FOREIGN KEY(studiengang_id) REFERENCES studiengaenge(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("PRAGMA table_info(module)")
        cols_module = [col[1] for col in cursor.fetchall()]
        if 'studiengang_id' not in cols_module:
            cursor.execute("ALTER TABLE module ADD COLUMN studiengang_id INTEGER")
        if 'geplantes_semester' not in cols_module:
            cursor.execute("ALTER TABLE module ADD COLUMN geplantes_semester INTEGER DEFAULT 1")

        # Prüfungsleistungen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pruefungsleistungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note REAL NOT NULL,
                versuchs_nummer INTEGER NOT NULL,
                modul_id INTEGER,
                FOREIGN KEY(modul_id) REFERENCES module(id) ON DELETE CASCADE
            )
        """)

        # Zeiteinträge
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zeit_eintraege (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                datum TEXT NOT NULL,
                start_zeit TEXT NOT NULL,
                end_zeit TEXT,
                geplante_dauer INTEGER,
                tatsaechliche_dauer INTEGER,
                beschreibung TEXT,
                modul_id INTEGER,
                FOREIGN KEY(modul_id) REFERENCES module(id) ON DELETE SET NULL
            )
        """)
        cursor.execute("PRAGMA table_info(zeit_eintraege)")
        if 'modul_id' not in [col[1] for col in cursor.fetchall()]:
            cursor.execute("ALTER TABLE zeit_eintraege ADD COLUMN modul_id INTEGER")
        conn.commit()

    def save_setting(self, key: str, value: str):
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row['value'] if row else None
        return None

    def delete_studiengang(self, sg_id: int):
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn:
            cursor = conn.cursor()
            # Manuelles Kaskadieren, falls die DB-Datei alt ist oder FKs nicht greifen
            cursor.execute("DELETE FROM pruefungsleistungen WHERE modul_id IN (SELECT id FROM module WHERE studiengang_id = ?)", (sg_id,))
            cursor.execute("DELETE FROM module WHERE studiengang_id = ?", (sg_id,))
            cursor.execute("DELETE FROM semester WHERE studiengang_id = ?", (sg_id,))
            cursor.execute("DELETE FROM studiengaenge WHERE id = ?", (sg_id,))
            conn.commit()

    def delete_modul(self, mod_id: int):
        """Löscht ein einzelnes Modul und seine Prüfungsleistungen."""
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pruefungsleistungen WHERE modul_id = ?", (mod_id,))
            cursor.execute("DELETE FROM module WHERE id = ?", (mod_id,))
            conn.commit()

    def delete_zeit_eintrag(self, ze_id: int):
        """Löscht einen Lerntermin oder eine Lernsession."""
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn:
            conn.execute("DELETE FROM zeit_eintraege WHERE id = ?", (ze_id,))
            conn.commit()

    def delete_pruefungsleistung(self, pl_id: int):
        """Löscht eine einzelne Prüfungsleistung."""
        if self.conn is None: self.verbinden()
        conn = self.conn
        if conn:
            conn.execute("DELETE FROM pruefungsleistungen WHERE id = ?", (pl_id,))
            conn.commit()

    def speichern(self, objekt: Any, parent_id: Optional[int] = None):
        if self.conn is None: self.verbinden()
        conn = self.conn
        if not conn: return
        cursor = conn.cursor()

        if isinstance(objekt, Studiengang):
            cursor.execute("SELECT id FROM studiengaenge WHERE name = ?", (objekt.name,))
            row = cursor.fetchone()
            if row:
                sg_id = row['id']
                cursor.execute("UPDATE studiengaenge SET regelstudienzeit = ?, zielschnitt = ? WHERE id = ?", 
                             (objekt.regelstudienzeit, objekt.zielschnitt, sg_id))
            else:
                cursor.execute("INSERT INTO studiengaenge (name, regelstudienzeit, zielschnitt) VALUES (?, ?, ?)", 
                             (objekt.name, objekt.regelstudienzeit, objekt.zielschnitt))
                sg_id = cursor.lastrowid
            
            objekt.id = sg_id # ID zurückschreiben
            
            # Semester speichern (vorher löschen der alten Einträge für diesen SG)
            cursor.execute("DELETE FROM semester WHERE studiengang_id = ?", (sg_id,))
            for sem in objekt.semester_liste:
                cursor.execute("INSERT INTO semester (nummer, start_datum, end_datum, studiengang_id) VALUES (?, ?, ?, ?)",
                             (sem.nummer, sem.start_datum.isoformat(), sem.end_datum.isoformat(), sg_id))
            
            # Module speichern
            for mod in objekt.module:
                self.speichern(mod, parent_id=sg_id)

        elif isinstance(objekt, Modul):
            # Wenn ID bereits gesetzt ist, nehmen wir diese zum Auffinden (wichtig für Umbenennungen)
            row = None
            if objekt.id:
                cursor.execute("SELECT id FROM module WHERE id = ?", (objekt.id,))
                row = cursor.fetchone()
            
            # Fallback: Über Titel suchen (nur falls ID noch nicht bekannt ist)
            if not row:
                cursor.execute("SELECT id FROM module WHERE titel = ? AND studiengang_id = ?", (objekt.titel, parent_id))
                row = cursor.fetchone()

            if row:
                mod_id = row['id']
                # titel = ? hinzugefügt, damit Umbenennungen gespeichert werden
                cursor.execute("UPDATE module SET titel = ?, status = ?, ects = ? , geplantes_semester = ? WHERE id = ?", 
                             (objekt.titel, objekt.status.value, objekt.ects, objekt.geplantes_semester, mod_id))
            else:
                cursor.execute("INSERT INTO module (titel, ects, status, geplantes_semester, studiengang_id) VALUES (?, ?, ?, ?, ?)",
                             (objekt.titel, objekt.ects, objekt.status.value, objekt.geplantes_semester, parent_id))
                mod_id = cursor.lastrowid
            
            objekt.id = mod_id # ID zurückschreiben

            for pl in objekt.pruefungsleistungen:
                self.speichern(pl, parent_id=mod_id)

        elif isinstance(objekt, Pruefungsleistung):
            # Prüfen ob diese Prüfungsleistung (Versuch) bereits existiert
            cursor.execute("SELECT id FROM pruefungsleistungen WHERE modul_id = ? AND versuchs_nummer = ?", (parent_id, objekt.versuchs_nummer))
            row = cursor.fetchone()
            if not row:
                cursor.execute("INSERT INTO pruefungsleistungen (note, versuchs_nummer, modul_id) VALUES (?, ?, ?)",
                             (objekt.note, objekt.versuchs_nummer, parent_id))
                objekt.id = cursor.lastrowid
            else:
                # Update falls bereits vorhanden (zum Korrigieren von Fehlern)
                objekt.id = row['id']
                cursor.execute("UPDATE pruefungsleistungen SET note = ? WHERE id = ?", (objekt.note, objekt.id))

        elif isinstance(objekt, ZeitEintrag):
            if objekt.id:
                # Update (Theoretisch möglich primär für Deletion-Check)
                if isinstance(objekt, Lerntermin):
                    cursor.execute("UPDATE zeit_eintraege SET datum=?, start_zeit=?, geplante_dauer=?, beschreibung=?, modul_id=? WHERE id=?",
                                 (objekt.datum.isoformat(), objekt.start_zeit.isoformat(), objekt.geplante_dauer, objekt.beschreibung, objekt.modul_id, objekt.id))
                elif isinstance(objekt, Lernsession):
                    cursor.execute("UPDATE zeit_eintraege SET datum=?, start_zeit=?, end_zeit=?, tatsaechliche_dauer=?, modul_id=? WHERE id=?",
                                 (objekt.datum.isoformat(), objekt.start_zeit.isoformat(), objekt.end_zeit.isoformat(), objekt.tatsaechliche_dauer, objekt.modul_id, objekt.id))
            else:
                # Insert
                if isinstance(objekt, Lerntermin):
                    cursor.execute("INSERT INTO zeit_eintraege (type, datum, start_zeit, geplante_dauer, beschreibung, modul_id) VALUES (?, ?, ?, ?, ?, ?)",
                                 ('TERMIN', objekt.datum.isoformat(), objekt.start_zeit.isoformat(), objekt.geplante_dauer, objekt.beschreibung, objekt.modul_id))
                elif isinstance(objekt, Lernsession):
                    cursor.execute("INSERT INTO zeit_eintraege (type, datum, start_zeit, end_zeit, tatsaechliche_dauer, modul_id) VALUES (?, ?, ?, ?, ?, ?)",
                                 ('SESSION', objekt.datum.isoformat(), objekt.start_zeit.isoformat(), objekt.end_zeit.isoformat(), objekt.tatsaechliche_dauer, objekt.modul_id))
                objekt.id = cursor.lastrowid
        
        conn.commit()

    def laden(self) -> dict:
        if self.conn is None: self.verbinden()
        conn = self.conn
        if not conn: return {'studiengaenge': [], 'zeiteintraege': []}
        cursor = conn.cursor()
        
        studiengaenge = []
        cursor.execute("SELECT * FROM studiengaenge")
        for sg_row in cursor.fetchall():
            regel = sg_row['regelstudienzeit'] if 'regelstudienzeit' in sg_row.keys() else 6
            ziel = sg_row['zielschnitt'] if 'zielschnitt' in sg_row.keys() else 2.0
            sg = Studiengang(sg_row['name'], regel, ziel)
            sg.id = sg_row['id'] # Hilfsattribut für Session
            
            cursor.execute("SELECT * FROM semester WHERE studiengang_id = ?", (sg.id,))
            for sem_row in cursor.fetchall():
                sem = Semester(sem_row['nummer'], datetime.fromisoformat(sem_row['start_datum']), datetime.fromisoformat(sem_row['end_datum']))
                sem.id = sem_row['id']
                sg.semester_liste.append(sem)
            
            cursor.execute("SELECT * FROM module WHERE studiengang_id = ?", (sg.id,))
            for mod_row in cursor.fetchall():
                mod = Modul(mod_row['titel'], mod_row['ects'], Status(mod_row['status']), mod_row['geplantes_semester'])
                mod.id = mod_row['id']
                cursor.execute("SELECT * FROM pruefungsleistungen WHERE modul_id = ?", (mod_row['id'],))
                for pl_row in cursor.fetchall():
                    pl = Pruefungsleistung(pl_row['note'], pl_row['versuchs_nummer'])
                    pl.id = pl_row['id']
                    mod.pruefungsleistungen.append(pl)
                sg.module.append(mod)
            
            studiengaenge.append(sg)

        zeiteintraege = []
        cursor.execute("SELECT * FROM zeit_eintraege")
        for row in cursor.fetchall():
            d, s = datetime.fromisoformat(row['datum']), datetime.fromisoformat(row['start_zeit'])
            m_id = row['modul_id'] if 'modul_id' in row.keys() else None
            ze = None
            if row['type'] == 'TERMIN':
                ze = Lerntermin(d, s, row['geplante_dauer'], row['beschreibung'], modul_id=m_id)
            else:
                ze = Lernsession(d, s, datetime.fromisoformat(row['end_zeit']), modul_id=m_id)
            
            if ze:
                ze.id = row['id']
                zeiteintraege.append(ze)

        return {'studiengaenge': studiengaenge, 'zeiteintraege': zeiteintraege}
