"""
models.py – Datenmodell-Klassen fuer das Studenten-Dashboard.

Dieses Modul definiert die zentralen Entitaeten des Domaenenmodells:
    - Status:              Enum fuer den Modul-Status (OFFEN / BESTANDEN / NICHT_BESTANDEN)
    - Pruefungsleistung:   Einzelner Pruefungsversuch mit Note und Validierung
    - Modul:               Studienmodul mit ECTS, Status und Pruefungsleistungen
    - ZeitEintrag:         Abstrakte Basisklasse fuer zeitbasierte Eintraege
    - Lerntermin:          Geplanter Lerntermin (erbt von ZeitEintrag)
    - Lernsession:         Durchgefuehrte Lernsession (erbt von ZeitEintrag)
    - Semester:            Zeitraum eines Semesters mit Start- und Enddatum
    - Studiengang:         Zentrales Aggregat mit Semestern, Modulen und Statistiken

Verwendete OOP-Konzepte:
    - Kapselung ueber Properties (Note-Validierung in Pruefungsleistung)
    - Vererbung (ZeitEintrag -> Lerntermin, Lernsession)
    - Komposition (Studiengang besitzt Semester und Module)
    - Enum fuer typsichere Status-Werte
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional


class Status(Enum):
    """Moegliche Zustaende eines Moduls als Aufzaehlungstyp."""
    OFFEN = "OFFEN"
    BESTANDEN = "BESTANDEN"
    NICHT_BESTANDEN = "NICHT_BESTANDEN"


class Pruefungsleistung:
    """
    Repraesentiert einen einzelnen Pruefungsversuch mit Note.

    Die Note wird ueber ein Property mit Setter-Validierung gekapselt,
    sodass nur Werte im Bereich 1.0 bis 5.0 akzeptiert werden.
    """

    def __init__(self, note: float, versuchs_nummer: int) -> None:
        """
        Parameter:
            note:             Die erreichte Note (1.0 bis 5.0)
            versuchs_nummer:  Laufende Nummer des Pruefungsversuchs
        """
        self._note: float = 0.0
        self.note = note                        # Validierung ueber Property-Setter
        self.versuchs_nummer: int = versuchs_nummer
        self.id: Optional[int] = None           # Datenbank-ID, wird beim Speichern gesetzt

    # --- Property fuer die Note mit Validierung ---

    @property
    def note(self) -> float:
        """Gibt die Note zurueck."""
        return self._note

    @note.setter
    def note(self, wert: float) -> None:
        """Setzt die Note. Wirft ValueError bei ungueltigem Bereich."""
        if not (1.0 <= wert <= 5.0):
            raise ValueError("Note muss zwischen 1.0 und 5.0 liegen.")
        self._note = wert

    def ist_bestanden(self) -> bool:
        """Prueft, ob dieser Versuch bestanden ist (Note <= 4.0)."""
        return self._note <= 4.0

    def __repr__(self) -> str:
        return f"Pruefungsleistung(note={self.note}, versuch={self.versuchs_nummer})"


class Modul:
    """
    Repraesentiert ein Modul im Studiengang (z. B. 'Mathematik I').

    Enthaelt ECTS-Punkte, den aktuellen Status sowie eine Liste
    von Pruefungsleistungen (maximal 3 Versuche, Kardinalitaet 0..3).
    Der Status wird automatisch anhand der Pruefungsergebnisse berechnet.
    """

    def __init__(self, titel: str, ects: int,
                 status: Status = Status.OFFEN,
                 geplantes_semester: int = 1) -> None:
        """
        Parameter:
            titel:              Name des Moduls
            ects:               ECTS-Punkte des Moduls
            status:             Aktueller Status (Standard: OFFEN)
            geplantes_semester:  Semester, in dem das Modul geplant ist
        """
        self.titel: str = titel
        self.ects: int = ects
        self.status: Status = status
        self.geplantes_semester: int = geplantes_semester
        self.pruefungsleistungen: List[Pruefungsleistung] = []
        self.id: Optional[int] = None

    def neue_pruefungsleistung(self, note: float) -> None:
        """
        Fuegt eine neue Pruefungsleistung hinzu und aktualisiert den Status.

        Maximal 3 Versuche sind erlaubt. Die Versuchsnummer wird
        automatisch anhand der bisherigen Anzahl vergeben.
        """
        if len(self.pruefungsleistungen) >= 3:
            raise ValueError("Maximal 3 Versuche erlaubt.")

        versuch = len(self.pruefungsleistungen) + 1
        leistung = Pruefungsleistung(note, versuch)
        self.pruefungsleistungen.append(leistung)
        self.aktualisiere_status()

    def aktualisiere_status(self) -> None:
        """
        Berechnet den Modul-Status anhand der Pruefungsleistungen neu.

        Regeln:
            - Keine Pruefungen vorhanden    -> OFFEN
            - Letzte Note bestanden (<= 4.0) -> BESTANDEN
            - 3 Fehlversuche                -> NICHT_BESTANDEN
            - Sonst                         -> OFFEN (weitere Versuche moeglich)
        """
        if not self.pruefungsleistungen:
            self.status = Status.OFFEN
        elif self.pruefungsleistungen[-1].ist_bestanden():
            self.status = Status.BESTANDEN
        elif len(self.pruefungsleistungen) >= 3:
            self.status = Status.NICHT_BESTANDEN
        else:
            self.status = Status.OFFEN

    def ist_bestanden(self) -> bool:
        """Prueft, ob das Modul bestanden ist."""
        return self.status == Status.BESTANDEN

    def berechne_aufwand(self, sessions: list) -> int:
        """
        Berechnet den bisherigen Lernaufwand fuer dieses Modul in Minuten.

        Parameter:
            sessions: Liste aller Lernsessions (werden nach modul_id gefiltert)
        """
        gesamt = 0
        for s in sessions:
            if s.modul_id == self.id:
                gesamt = gesamt + s.dauer()
        return gesamt

    def __repr__(self) -> str:
        return f"Modul('{self.titel}', ECTS={self.ects}, Status={self.status.value})"


# =====================================================================
# Vererbungshierarchie fuer Zeiteintraege
# =====================================================================

class ZeitEintrag:
    """
    Abstrakte Basisklasse fuer alle zeitbasierten Eintraege.

    Gemeinsame Attribute (datum, start_zeit, modul_id) werden hier
    definiert. Die Methode dauer() muss von jeder Unterklasse
    implementiert werden, um die jeweilige Dauer in Minuten zu liefern.
    """

    def __init__(self, datum: datetime, start_zeit: datetime,
                 modul_id: Optional[int] = None) -> None:
        """
        Parameter:
            datum:      Datum des Eintrags
            start_zeit: Startzeitpunkt
            modul_id:   ID des zugeordneten Moduls (optional)
        """
        self.datum: datetime = datum
        self.start_zeit: datetime = start_zeit
        self.modul_id: Optional[int] = modul_id
        self.id: Optional[int] = None

    def dauer(self) -> int:
        """Gibt die Dauer in Minuten zurueck. Muss in Unterklassen ueberschrieben werden."""
        raise NotImplementedError("Muss in Unterklasse implementiert werden.")


class Lerntermin(ZeitEintrag):
    """
    Geplanter Lerntermin mit voraussichtlicher Dauer und Beschreibung.

    Ein Lerntermin kann spaeter bestaetigt und in eine Lernsession
    umgewandelt werden, sobald die tatsaechliche Lernzeit feststeht.
    """

    def __init__(self, datum: datetime, start_zeit: datetime,
                 geplante_dauer: int, beschreibung: str,
                 modul_id: Optional[int] = None) -> None:
        """
        Parameter:
            geplante_dauer:  Geplante Lernzeit in Minuten
            beschreibung:    Kurzbeschreibung des Lerninhalts
        """
        super().__init__(datum, start_zeit, modul_id)
        self.geplante_dauer: int = geplante_dauer
        self.beschreibung: str = beschreibung

    def dauer(self) -> int:
        """Gibt die geplante Dauer in Minuten zurueck."""
        return self.geplante_dauer

    def __repr__(self) -> str:
        datum_str = self.datum.strftime('%d.%m.%Y')
        return f"Lerntermin({datum_str}, {self.geplante_dauer}min, '{self.beschreibung}')"


class Lernsession(ZeitEintrag):
    """
    Tatsaechlich absolvierte Lernsession mit Start- und Endzeit.

    Die Dauer wird automatisch aus der Differenz von End- und
    Startzeit berechnet und als tatsaechliche_dauer gespeichert.
    """

    def __init__(self, datum: datetime, start_zeit: datetime,
                 end_zeit: datetime,
                 modul_id: Optional[int] = None) -> None:
        """
        Parameter:
            end_zeit: Endzeitpunkt der Session
        """
        super().__init__(datum, start_zeit, modul_id)
        self.end_zeit: datetime = end_zeit
        self.tatsaechliche_dauer: int = self._berechne_dauer()

    def _berechne_dauer(self) -> int:
        """Berechnet die Dauer in Minuten aus der Zeitdifferenz."""
        differenz = self.end_zeit - self.start_zeit
        return int(differenz.total_seconds() / 60)

    def dauer(self) -> int:
        """Gibt die tatsaechliche Dauer in Minuten zurueck."""
        return self.tatsaechliche_dauer

    def __repr__(self) -> str:
        datum_str = self.datum.strftime('%d.%m.%Y')
        return f"Lernsession({datum_str}, {self.tatsaechliche_dauer}min)"


class Semester:
    """
    Repraesentiert ein Semester mit Nummer, Start- und Enddatum.

    Bietet Hilfsmethoden zur Pruefung, ob das Semester aktuell ist,
    und zur Berechnung des Notendurchschnitts der zugehoerigen Module.
    """

    def __init__(self, nummer: int, start_datum: datetime,
                 end_datum: datetime) -> None:
        """
        Parameter:
            nummer:       Semesternummer (1, 2, 3, ...)
            start_datum:  Beginn des Semesters
            end_datum:    Ende des Semesters
        """
        self.nummer: int = nummer
        self.start_datum: datetime = start_datum
        self.end_datum: datetime = end_datum
        self.id: Optional[int] = None

    def ist_aktuell(self) -> bool:
        """Prueft, ob das heutige Datum innerhalb dieses Semesters liegt."""
        jetzt = datetime.now()
        return self.start_datum <= jetzt <= self.end_datum

    def berechne_notendurchschnitt(self, module: List[Modul]) -> float:
        """
        Berechnet den Notendurchschnitt aller bestandenen Module dieses Semesters.

        Es wird jeweils die letzte (= aktuelle) Note eines bestandenen
        Moduls herangezogen. Gibt 0.0 zurueck, falls keine Noten vorliegen.
        """
        noten: List[float] = []
        for m in module:
            if m.geplantes_semester == self.nummer and m.ist_bestanden():
                if m.pruefungsleistungen:
                    noten.append(m.pruefungsleistungen[-1].note)
        if not noten:
            return 0.0
        return round(sum(noten) / len(noten), 2)

    def __repr__(self) -> str:
        start = self.start_datum.strftime('%d.%m.%Y')
        ende = self.end_datum.strftime('%d.%m.%Y')
        return f"Semester {self.nummer} ({start} - {ende})"


class Studiengang:
    """
    Zentrales Aggregat des Domaenenmodells.

    Ein Studiengang verwaltet seine Semester und Module (Komposition).
    Er bietet Methoden zur automatischen Semester-Generierung, zur
    Berechnung des ECTS-Fortschritts und des Notendurchschnitts.
    Beim Loeschen werden alle zugehoerigen Daten mitentfernt.
    """

    def __init__(self, name: str, regelstudienzeit: int = 6,
                 zielschnitt: float = 2.0) -> None:
        """
        Parameter:
            name:              Name des Studiengangs (z. B. 'Informatik B.Sc.')
            regelstudienzeit:  Anzahl der Semester (Standard: 6)
            zielschnitt:       Angestrebter Notendurchschnitt (Standard: 2.0)
        """
        self.name: str = name
        self.regelstudienzeit: int = regelstudienzeit
        self.zielschnitt: float = zielschnitt
        self.semester_liste: List[Semester] = []
        self.module: List[Modul] = []
        self.id: Optional[int] = None

    def generiere_semester(self, start_datum: datetime) -> None:
        """
        Erzeugt automatisch Semester-Objekte (jeweils 6 Monate).

        Ausgehend vom uebergebenen Startdatum werden so viele Semester
        generiert, wie die Regelstudienzeit vorgibt.
        """
        self.semester_liste = []
        aktueller_start = start_datum

        for i in range(1, self.regelstudienzeit + 1):
            monat = aktueller_start.month + 6
            jahr = aktueller_start.year

            # Jahresueberlauf behandeln (z. B. Oktober + 6 = April naechstes Jahr)
            while monat > 12:
                monat = monat - 12
                jahr = jahr + 1

            naechster_start = aktueller_start.replace(year=jahr, month=monat)
            ende = naechster_start - timedelta(days=1)

            self.semester_liste.append(Semester(i, aktueller_start, ende))
            aktueller_start = naechster_start

    def get_aktuelles_semester(self) -> int:
        """
        Ermittelt die Nummer des aktuellen Semesters anhand des heutigen Datums.

        Liegt das Datum vor Studienbeginn, wird Semester 1 zurueckgegeben.
        Liegt es nach dem letzten Semester, wird die Regelstudienzeit zurueckgegeben.
        """
        for sem in self.semester_liste:
            if sem.ist_aktuell():
                return sem.nummer
        if self.semester_liste:
            jetzt = datetime.now()
            if jetzt < self.semester_liste[0].start_datum:
                return 1
        return self.regelstudienzeit

    def berechne_gesamt_fortschritt(self) -> int:
        """Berechnet die Summe der ECTS-Punkte aller bestandenen Module."""
        summe = 0
        for modul in self.module:
            if modul.ist_bestanden():
                summe = summe + modul.ects
        return summe

    def berechne_durchschnitt(self) -> float:
        """
        Berechnet den arithmetischen Notendurchschnitt ueber alle
        bestandenen Module (jeweils die letzte Note).

        Gibt 0.0 zurueck, falls noch keine bestandenen Module vorliegen.
        """
        noten: List[float] = []
        for modul in self.module:
            if modul.ist_bestanden() and modul.pruefungsleistungen:
                letzte_note = modul.pruefungsleistungen[-1].note
                noten.append(letzte_note)

        if not noten:
            return 0.0

        durchschnitt = sum(noten) / len(noten)
        return round(durchschnitt, 2)

    def ist_abgeschlossen(self) -> bool:
        """Prueft, ob alle Module des Studiengangs bestanden sind."""
        if not self.module:
            return False
        for modul in self.module:
            if not modul.ist_bestanden():
                return False
        return True

    def __repr__(self) -> str:
        return f"Studiengang('{self.name}', Module={len(self.module)})"
