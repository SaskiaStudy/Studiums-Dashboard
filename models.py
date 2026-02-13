from enum import Enum
from datetime import datetime
from typing import List, Optional, cast

class Status(Enum):
    """Status eines Moduls."""
    OFFEN = "OFFEN"
    BESTANDEN = "BESTANDEN"
    NICHT_BESTANDEN = "NICHT_BESTANDEN"

class Pruefungsleistung:
    """
    Repräsentiert eine Prüfungsleistung (Versuch).
    """
    def __init__(self, note: float, versuchs_nummer: int):
        self._note = 0.0  # Initialisierung für den Setter
        self.note = note
        self.versuchs_nummer = versuchs_nummer
        self.id: Optional[int] = None # DB-ID

    @property
    def note(self) -> float:
        return self._note

    @note.setter
    def note(self, value: float):
        if not (1.0 <= value <= 5.0):
            raise ValueError("Note muss zwischen 1.0 und 5.0 liegen.")
        self._note = value

    def __repr__(self):
        return f"Pruefungsleistung(note={self.note}, versuch={self.versuchs_nummer})"

class Modul:
    """
    Repräsentiert ein Modul.
    Gehört zu einem Studiengang und hat ein geplantes Semester.
    """
    def __init__(self, titel: str, ects: int, status: Status = Status.OFFEN, geplantes_semester: int = 1):
        self.titel = titel
        self.ects = ects
        self.status = status
        self.geplantes_semester = geplantes_semester
        self.pruefungsleistungen: List[Pruefungsleistung] = []
        self.id: Optional[int] = None # DB-ID

    def neue_pruefungsleistung(self, note: float):
        """Fügt eine neue Prüfungsleistung hinzu. Prüft auf max. 3 Versuche."""
        if len(self.pruefungsleistungen) >= 3:
            raise ValueError("Maximal 3 Versuche erlaubt.")
        
        versuch = len(self.pruefungsleistungen) + 1
        leistung = Pruefungsleistung(note, versuch)
        self.pruefungsleistungen.append(leistung)
        
        if leistung.note <= 4.0:
            self.status = Status.BESTANDEN
        elif versuch == 3:
            self.status = Status.NICHT_BESTANDEN

    def __repr__(self):
        return f"Modul('{self.titel}', ECTS={self.ects}, Status={self.status.value}, Sem={self.geplantes_semester})"

class Semester:
    """
    Repräsentiert ein fixes Zeitfenster (Semester).
    """
    def __init__(self, nummer: int, start_datum: datetime, end_datum: datetime):
        self.nummer = nummer
        self.start_datum = start_datum
        self.end_datum = end_datum
        self.id: Optional[int] = None # DB-ID

    def __repr__(self):
        return f"Semester {self.nummer} ({self.start_datum.strftime('%d.%m.%Y')} - {self.end_datum.strftime('%d.%m.%Y')})"

class Studiengang:
    """
    Aggregate Root. Verwaltet Module und Semester.
    """
    def __init__(self, name: str, regelstudienzeit: int = 6, zielschnitt: float = 2.0):
        self.name = name
        self.semester_liste: List[Semester] = []
        self.module: List[Modul] = []
        self.regelstudienzeit = regelstudienzeit
        self.zielschnitt = zielschnitt
        self.id: Optional[int] = None # DB-ID

    def generiere_semester(self, start_datum: datetime):
        """Generiert automatisch n Semester (jeweils exakt 6 Monate)."""
        self.semester_liste = []
        
        curr_start = start_datum
        for i in range(1, self.regelstudienzeit + 1):
            # Enddatum: 6 Monate später minus 1 Tag
            # Das nächste Semester beginnt am 1. Tag des folgenden Monats
            m = int(curr_start.month) + 6
            y = int(curr_start.year)
            while m > 12:
                m -= 12
                y += 1
            
            # Das Ende des Semesters ist der Tag vor dem Start des nächsten Semesters
            next_sem_start = curr_start.replace(year=int(y), month=int(m), day=int(curr_start.day))
            import datetime as dt
            curr_end = next_sem_start - dt.timedelta(days=1)
            
            self.semester_liste.append(Semester(i, curr_start, curr_end))
            curr_start = next_sem_start

    def get_aktuelles_semester_nr(self) -> int:
        """Ermittelt das aktuelle Semester basierend auf dem heutigen Datum."""
        jetzt = datetime.now()
        for sem in self.semester_liste:
            if sem.start_datum <= jetzt <= sem.end_datum:
                return sem.nummer
        # Fallback: Falls Studium noch nicht begonnen hat
        if self.semester_liste and jetzt < self.semester_liste[0].start_datum:
            return 1
        # Fallback: Falls Studium schon beendet ist
        return self.regelstudienzeit

    def get_naechstes_semester_start(self) -> Optional[datetime]:
        """Gibt das Startdatum des nächsten Semesters zurück."""
        akt_nr = self.get_aktuelles_semester_nr()
        if akt_nr < len(self.semester_liste):
            return self.semester_liste[akt_nr].start_datum
        return None

    def berechne_fortschritt(self) -> int:
        """Summiert alle ECTS von bestandenen Modulen."""
        return sum(cast(int, m.ects) for m in self.module if m.status == Status.BESTANDEN)

    def berechne_durchschnitt(self) -> float:
        """Berechnet den Notendurchschnitt (arithmetisch)."""
        noten = [float(m.pruefungsleistungen[-1].note) for m in self.module 
                 if m.status == Status.BESTANDEN and m.pruefungsleistungen]
        
        if not noten: return 0.0
        durchschnitt = sum(noten) / len(noten)
        return float(f"{durchschnitt:.2f}")

    def __repr__(self):
        return f"Studiengang('{self.name}', Module={len(self.module)})"

class ZeitEintrag:
    """Basisklasse für Zeiteinträge."""
    id: Optional[int] = None
    
    def __init__(self, datum: datetime, start_zeit: datetime, modul_id: Optional[int] = None):
        self.datum = datum
        self.start_zeit = start_zeit
        self.modul_id = modul_id
        self.id = None # DB-ID

class Lerntermin(ZeitEintrag):
    """Geplanter Lerntermin."""
    def __init__(self, datum: datetime, start_zeit: datetime, geplante_dauer: int, beschreibung: str, modul_id: Optional[int] = None):
        super().__init__(datum, start_zeit, modul_id)
        self.geplante_dauer = geplante_dauer # in Minuten
        self.beschreibung = beschreibung
    
    def __repr__(self):
        return f"Lerntermin({self.datum.date()}, dauer={self.geplante_dauer}min, '{self.beschreibung}')"

class Lernsession(ZeitEintrag):
    """Vergangene Lernsession."""
    def __init__(self, datum: datetime, start_zeit: datetime, end_zeit: datetime, modul_id: Optional[int] = None):
        super().__init__(datum, start_zeit, modul_id)
        self.end_zeit = end_zeit
        self.tatsaechliche_dauer = self._berechne_dauer()

    def _berechne_dauer(self) -> int:
        """Berechnet Dauer in Minuten."""
        delta = self.end_zeit - self.start_zeit
        return int(delta.total_seconds() / 60)

    def __repr__(self):
        return f"Lernsession({self.datum.date()}, dauer={self.tatsaechliche_dauer}min)"
