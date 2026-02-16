"""
ui.py – Konsolenbasierte Benutzeroberflaeche fuer das Studenten-Dashboard.

Dieses Modul stellt die gesamte Benutzerinteraktion bereit. Die Struktur
gliedert sich in spezialisierte Klassen, um Uebersichtlichkeit zu wahren:

    Hilfsklassen:
        - EingabeHelper:   Validierte Benutzereingaben (Zahlen, Noten, Daten)
        - AnzeigeHelper:   Formatierte Konsolenausgaben und Farbdarstellung

    Untermenues (je ein Fachbereich):
        - StudiengangMenue:   Studiengang anlegen, wechseln, loeschen
        - ModulMenue:         Module hinzufuegen, loeschen, umbenennen
        - NotenMenue:         Noten eintragen, korrigieren, loeschen
        - LernterminMenue:    Lerntermine planen, bearbeiten, bestaetigen
        - LernsessionMenue:   Lernsessions manuell erfassen und loeschen
        - DashboardAnzeige:   Statistische Gesamtuebersicht

    Hauptmenue:
        - BenutzerMenue:  Orchestriert alle Untermenues und steuert
                          die Hauptschleife der Anwendung
"""

import sys
from datetime import datetime, timedelta
from typing import List, Optional
from models import (Studiengang, Modul, Status,
                    Lerntermin, Lernsession, ZeitEintrag)


# =====================================================================
# ANSI-Farbcodes fuer farbige Konsolenausgabe
# =====================================================================
GRUEN = "\033[92m"
ORANGE = "\033[93m"
ROT = "\033[91m"
RESET = "\033[0m"


# =====================================================================
# EingabeHelper – Validierte Benutzereingaben
# =====================================================================

class EingabeHelper:
    """
    Stellt Methoden fuer validierte Benutzereingaben bereit.

    Jede Methode fragt den Benutzer in einer Schleife, bis eine
    gueltige Eingabe erfolgt oder mit 'a' abgebrochen wird.
    """

    @staticmethod
    def eingabe_zahl(text: str) -> Optional[int]:
        """Fragt nach einer ganzen Zahl. Gibt None bei Abbruch zurueck."""
        while True:
            eingabe = input(f"{text} ('a' = Abbrechen): ").strip()
            if eingabe.lower() == 'a' or eingabe == '':
                return None
            try:
                return int(eingabe)
            except ValueError:
                print("Bitte eine gueltige Zahl eingeben.")

    @staticmethod
    def eingabe_note(text: str) -> Optional[float]:
        """Fragt nach einer Note (1.0-5.0). Akzeptiert Komma und Punkt als Dezimalzeichen."""
        while True:
            eingabe = input(f"{text} ('a' = Abbrechen): ").strip()
            if eingabe.lower() == 'a' or eingabe == '':
                return None
            eingabe = eingabe.replace(',', '.')
            try:
                return float(eingabe)
            except ValueError:
                print("Bitte eine gueltige Note eingeben (z.B. 1,3 oder 2.0).")

    @staticmethod
    def eingabe_datum(text: str) -> Optional[datetime]:
        """Fragt nach einem Datum im Format TT.MM.JJJJ."""
        while True:
            eingabe = input(f"{text} (TT.MM.JJJJ, 'a' = Abbrechen): ").strip()
            if eingabe.lower() == 'a' or eingabe == '':
                return None
            try:
                return datetime.strptime(eingabe, "%d.%m.%Y")
            except ValueError:
                print("Ungueltiges Datum. Bitte TT.MM.JJJJ verwenden (z.B. 01.10.2025).")

    @staticmethod
    def eingabe_zeit(text: str) -> Optional[datetime]:
        """Fragt nach einer Uhrzeit im Format HH:MM."""
        while True:
            eingabe = input(f"{text} (HH:MM, 'a' = Abbrechen): ").strip()
            if eingabe.lower() == 'a' or eingabe == '':
                return None
            try:
                return datetime.strptime(eingabe, "%H:%M")
            except ValueError:
                print("Ungueltiges Format. Bitte HH:MM verwenden (z.B. 14:30).")


# =====================================================================
# AnzeigeHelper – Formatierte Konsolenausgaben
# =====================================================================

class AnzeigeHelper:
    """
    Stellt Methoden fuer formatierte, farbige Konsolenausgaben bereit.
    """

    @staticmethod
    def note_farbig(schnitt: float, zielschnitt: float) -> str:
        """
        Formatiert den Notendurchschnitt mit ANSI-Farbcodes.

        Gruen:  besser oder gleich dem Zielschnitt
        Orange: bis zu 1.0 schlechter als der Zielschnitt
        Rot:    mehr als 1.0 schlechter als der Zielschnitt
        """
        if schnitt == 0.0:
            return "---"
        if schnitt <= zielschnitt:
            return f"{GRUEN}{schnitt:.1f}{RESET}"
        elif schnitt <= zielschnitt + 1.0:
            return f"{ORANGE}{schnitt:.1f}{RESET}"
        else:
            return f"{ROT}{schnitt:.1f}{RESET}"

    @staticmethod
    def zeige_modulliste(sg: Studiengang, archiv_offen: bool) -> None:
        """
        Zeigt Module in zwei Gruppen: offene und bestandene Module.

        Bestandene Module werden in einem ein-/ausklappbaren Archiv
        dargestellt, gesteuert ueber den Parameter archiv_offen.
        """
        offen = [m for m in sg.module if m.status != Status.BESTANDEN]
        bestanden = [m for m in sg.module if m.status == Status.BESTANDEN]

        print("\n  [ ] OFFENE MODULE:")
        if not offen:
            print("      Keine offenen Module.")
        else:
            for mod in offen:
                nr = sg.module.index(mod) + 1
                note_str = ""
                if mod.pruefungsleistungen:
                    note_str = f" | Letzter Versuch: {mod.pruefungsleistungen[-1].note}"
                print(f"      {nr}. {mod.titel} ({mod.ects} ECTS, "
                      f"Sem {mod.geplantes_semester}{note_str})")

        status_text = "Einklappen" if archiv_offen else "Ausklappen"
        print(f"\n  [x] ABGESCHLOSSEN ({len(bestanden)}) "
              f"- Eingabe 'v' zum {status_text}")

        if archiv_offen:
            if not bestanden:
                print("      Noch keine Module abgeschlossen.")
            else:
                for mod in bestanden:
                    nr = sg.module.index(mod) + 1
                    note_str = ""
                    if mod.pruefungsleistungen:
                        note_str = f" | Note: {mod.pruefungsleistungen[-1].note}"
                    print(f"      {nr}. [x] {mod.titel} ({mod.ects} ECTS{note_str})")

    @staticmethod
    def modulname_fuer_id(sg: Optional[Studiengang], modul_id: Optional[int]) -> str:
        """Gibt den Modulnamen fuer eine gegebene Modul-ID zurueck (oder leer)."""
        if sg and modul_id:
            for m in sg.module:
                if m.id == modul_id:
                    return m.titel
        return ""


# =====================================================================
# StudiengangMenue – Studiengang-Verwaltung
# =====================================================================

class StudiengangMenue:
    """
    Untermenue fuer die Verwaltung von Studiengaengen.

    Ermoeglicht das Anlegen neuer Studiengaenge, Wechseln zwischen
    vorhandenen, Aendern des Zielschnitts und Loeschen.
    """

    def __init__(self, db_manager, eingabe: EingabeHelper) -> None:
        self.db = db_manager
        self.eingabe: EingabeHelper = eingabe

    def anzeigen(self, studiengaenge: List[Studiengang],
                 aktueller_studiengang: Optional[Studiengang]
                 ) -> tuple:
        """
        Zeigt das Studiengang-Menue in einer Schleife an.

        Gibt das aktualisierte Tupel (studiengaenge, aktueller_studiengang)
        zurueck, da diese Daten vom aufrufenden BenutzerMenue verwaltet werden.
        """
        while True:
            print("\n--- Studiengang verwalten ---")
            if aktueller_studiengang:
                print(f"Aktuell: {aktueller_studiengang.name}")
            if len(studiengaenge) > 1:
                print(f"({len(studiengaenge)} Studiengaenge vorhanden)")

            print("\n(n) Neuen Studiengang anlegen")
            print("(w) Studiengang wechseln")
            print("(z) Zielschnitt aendern")
            print("(l) Studiengang loeschen")
            print("(0) Zurueck")

            wahl = input("Wahl: ").strip().lower()
            if wahl == 'n':
                studiengaenge, aktueller_studiengang = self._anlegen(
                    studiengaenge, aktueller_studiengang)
            elif wahl == 'w':
                aktueller_studiengang = self._wechseln(
                    studiengaenge, aktueller_studiengang)
            elif wahl == 'z':
                self._zielschnitt_aendern(aktueller_studiengang)
            elif wahl == 'l':
                studiengaenge, aktueller_studiengang = self._loeschen(
                    studiengaenge, aktueller_studiengang)
            elif wahl == '0':
                break

        return studiengaenge, aktueller_studiengang

    def _anlegen(self, studiengaenge: List[Studiengang],
                 aktueller: Optional[Studiengang]
                 ) -> tuple:
        """Erstellt einen neuen Studiengang mit Semestern."""
        name = input("Name des Studiengangs ('a' = Abbrechen): ").strip()
        if not name or name.lower() == 'a':
            return studiengaenge, aktueller

        regelstudienzeit = self.eingabe.eingabe_zahl(
            "Regelstudienzeit in Semestern (z.B. 6)")
        if regelstudienzeit is None:
            return studiengaenge, aktueller

        start = self.eingabe.eingabe_datum("Startdatum des 1. Semesters")
        if start is None:
            return studiengaenge, aktueller

        sg = Studiengang(name, regelstudienzeit)
        sg.generiere_semester(start)
        self.db.speichern(sg)
        studiengaenge.append(sg)
        aktueller = sg
        print(f"\nStudiengang '{name}' mit {regelstudienzeit} Semestern angelegt!")
        return studiengaenge, aktueller

    def _wechseln(self, studiengaenge: List[Studiengang],
                   aktueller: Optional[Studiengang]
                   ) -> Optional[Studiengang]:
        """Wechselt den aktiven Studiengang durch Auswahl aus der Liste."""
        if len(studiengaenge) < 2:
            print("Nur ein Studiengang vorhanden. Nichts zum Wechseln.")
            return aktueller

        print("\nVerfuegbare Studiengaenge:")
        for i, sg in enumerate(studiengaenge):
            aktuell_marker = " <-- aktuell" if sg == aktueller else ""
            print(f"  {i + 1}. {sg.name}{aktuell_marker}")

        wahl = self.eingabe.eingabe_zahl("Welchen Studiengang waehlen?")
        if wahl and 1 <= wahl <= len(studiengaenge):
            aktueller = studiengaenge[wahl - 1]
            print(f"Gewechselt zu: {aktueller.name}")
        return aktueller

    def _zielschnitt_aendern(self, sg: Optional[Studiengang]) -> None:
        """Aendert den Zielschnitt des aktuellen Studiengangs."""
        if not sg:
            print("Kein Studiengang vorhanden.")
            return

        print(f"Aktueller Zielschnitt: {sg.zielschnitt}")
        neuer_schnitt = self.eingabe.eingabe_note("Neuer Zielschnitt")
        if neuer_schnitt is not None:
            sg.zielschnitt = neuer_schnitt
            self.db.speichern(sg)
            print(f"Zielschnitt auf {neuer_schnitt} gesetzt.")

    def _loeschen(self, studiengaenge: List[Studiengang],
                   aktueller: Optional[Studiengang]
                   ) -> tuple:
        """Loescht den aktuellen Studiengang nach Bestaetigung."""
        if not aktueller:
            print("Kein Studiengang vorhanden.")
            return studiengaenge, aktueller

        antwort = input(
            f"'{aktueller.name}' wirklich loeschen? "
            f"Alle Module werden entfernt! (j/n): "
        ).lower()
        if antwort == 'j' and aktueller.id:
            self.db.loeschen_studiengang(aktueller.id)
            studiengaenge.remove(aktueller)
            aktueller = studiengaenge[0] if studiengaenge else None
            print("Studiengang geloescht.")

        return studiengaenge, aktueller


# =====================================================================
# ModulMenue – Modul-Verwaltung
# =====================================================================

class ModulMenue:
    """
    Untermenue fuer die Verwaltung von Modulen.

    Ermoeglicht das Hinzufuegen, Loeschen und Umbenennen von Modulen
    innerhalb des aktuellen Studiengangs.
    """

    def __init__(self, db_manager, eingabe: EingabeHelper,
                 anzeige: AnzeigeHelper) -> None:
        self.db = db_manager
        self.eingabe: EingabeHelper = eingabe
        self.anzeige: AnzeigeHelper = anzeige

    def anzeigen(self, sg: Studiengang) -> bool:
        """Zeigt das Modul-Menue. Gibt den Archiv-Status zurueck."""
        archiv_offen = False

        while True:
            print(f"\n--- Module: {sg.name} ---")
            self.anzeige.zeige_modulliste(sg, archiv_offen)

            print("\n(n) Neues Modul hinzufuegen")
            print("(l) Modul loeschen")
            print("(u) Modul umbenennen")
            print("(v) Archiv ein-/ausklappen")
            print("(0) Zurueck")

            wahl = input("Wahl: ").strip().lower()
            if wahl == 'n':
                self._hinzufuegen(sg)
            elif wahl == 'l':
                self._loeschen(sg)
            elif wahl == 'u':
                self._umbenennen(sg)
            elif wahl == 'v':
                archiv_offen = not archiv_offen
            elif wahl == '0':
                break

        return archiv_offen

    def _hinzufuegen(self, sg: Studiengang) -> None:
        """Fuegt ein neues Modul zum Studiengang hinzu."""
        titel = input("Modul-Titel ('a' = Abbrechen): ").strip()
        if not titel or titel.lower() == 'a':
            return

        ects = self.eingabe.eingabe_zahl("ECTS-Punkte")
        if ects is None:
            return

        semester = self.eingabe.eingabe_zahl("Geplantes Semester")
        if semester is None:
            return

        modul = Modul(titel, ects, geplantes_semester=semester)
        sg.module.append(modul)
        self.db.speichern(sg)
        print(f"Modul '{titel}' hinzugefuegt.")

    def _loeschen(self, sg: Studiengang) -> None:
        """Loescht ein Modul nach Bestaetigung."""
        if not sg.module:
            print("Keine Module vorhanden.")
            return

        nr = self.eingabe.eingabe_zahl("Nummer des Moduls zum Loeschen")
        if nr and 1 <= nr <= len(sg.module):
            modul = sg.module[nr - 1]
            antwort = input(f"'{modul.titel}' wirklich loeschen? (j/n): ").lower()
            if antwort == 'j':
                if modul.id:
                    self.db.loeschen_modul(modul.id)
                sg.module.remove(modul)
                print("Modul geloescht.")
        else:
            print("Ungueltige Nummer.")

    def _umbenennen(self, sg: Studiengang) -> None:
        """Benennt ein vorhandenes Modul um."""
        if not sg.module:
            print("Keine Module vorhanden.")
            return

        nr = self.eingabe.eingabe_zahl("Nummer des Moduls zum Umbenennen")
        if nr and 1 <= nr <= len(sg.module):
            modul = sg.module[nr - 1]
            neuer_name = input(
                f"Neuer Name fuer '{modul.titel}' ('a' = Abbrechen): "
            ).strip()
            if neuer_name and neuer_name.lower() != 'a':
                modul.titel = neuer_name
                self.db.speichern(sg)
                print("Name aktualisiert.")
        else:
            print("Ungueltige Nummer.")


# =====================================================================
# NotenMenue – Noten-Verwaltung
# =====================================================================

class NotenMenue:
    """
    Untermenue fuer die Verwaltung von Pruefungsnoten.

    Ermoeglicht das Eintragen neuer Noten sowie das Korrigieren
    und Loeschen bestehender Noten. Die Statusberechnung des Moduls
    erfolgt automatisch ueber modul.aktualisiere_status().
    """

    def __init__(self, db_manager, eingabe: EingabeHelper,
                 anzeige: AnzeigeHelper) -> None:
        self.db = db_manager
        self.eingabe: EingabeHelper = eingabe
        self.anzeige: AnzeigeHelper = anzeige

    def anzeigen(self, sg: Studiengang) -> bool:
        """Zeigt das Noten-Menue. Gibt den Archiv-Status zurueck."""
        archiv_offen = False

        while True:
            print(f"\n--- Noten: {sg.name} ---")
            self.anzeige.zeige_modulliste(sg, archiv_offen)

            print("\n(e) Note eintragen")
            print("(b) Note bearbeiten / loeschen")
            print("(v) Archiv ein-/ausklappen")
            print("(0) Zurueck")

            wahl = input("Wahl: ").strip().lower()
            if wahl == 'e':
                self._eintragen(sg)
            elif wahl == 'b':
                self._bearbeiten(sg)
            elif wahl == 'v':
                archiv_offen = not archiv_offen
            elif wahl == '0':
                break

        return archiv_offen

    def _eintragen(self, sg: Studiengang) -> None:
        """Traegt eine neue Note fuer ein ausgewaehltes Modul ein."""
        if not sg.module:
            print("Keine Module vorhanden.")
            return

        nr = self.eingabe.eingabe_zahl("Nummer des Moduls")
        if nr is None or not (1 <= nr <= len(sg.module)):
            print("Ungueltige Nummer.")
            return

        modul = sg.module[nr - 1]

        # Warnung bei bereits bestandenem Modul
        if modul.ist_bestanden():
            antwort = input(
                "Modul ist bereits bestanden. Trotzdem Note eintragen? (j/n): "
            ).lower()
            if antwort != 'j':
                return

        note = self.eingabe.eingabe_note(f"Note fuer '{modul.titel}'")
        if note is not None:
            try:
                modul.neue_pruefungsleistung(note)
                self.db.speichern(sg)
                print(f"Note {note} eingetragen. Status: {modul.status.value}")
            except ValueError as fehler:
                print(f"Fehler: {fehler}")

    def _bearbeiten(self, sg: Studiengang) -> None:
        """Zeigt die Noten eines Moduls und bietet Korrektur/Loeschung an."""
        if not sg.module:
            print("Keine Module vorhanden.")
            return

        nr = self.eingabe.eingabe_zahl("Nummer des Moduls")
        if nr is None or not (1 <= nr <= len(sg.module)):
            print("Ungueltige Nummer.")
            return

        modul = sg.module[nr - 1]
        if not modul.pruefungsleistungen:
            print(f"'{modul.titel}' hat noch keine Noten.")
            return

        # Alle Versuche anzeigen
        print(f"\nNoten fuer '{modul.titel}':")
        for i, pl in enumerate(modul.pruefungsleistungen):
            print(f"  Versuch {pl.versuchs_nummer}: {pl.note}")

        print("\n(k) Note korrigieren")
        print("(l) Note loeschen")
        print("(0) Zurueck")

        aktion = input("Wahl: ").strip().lower()

        if aktion == 'k':
            self._note_korrigieren(sg, modul)
        elif aktion == 'l':
            self._note_loeschen(sg, modul)

    def _note_korrigieren(self, sg: Studiengang, modul: Modul) -> None:
        """Korrigiert die Note eines bestimmten Versuchs."""
        v_nr = self.eingabe.eingabe_zahl("Welchen Versuch korrigieren?")
        if v_nr and 1 <= v_nr <= len(modul.pruefungsleistungen):
            neue_note = self.eingabe.eingabe_note("Neue Note")
            if neue_note is not None:
                try:
                    modul.pruefungsleistungen[v_nr - 1].note = neue_note
                    modul.aktualisiere_status()
                    self.db.speichern(sg)
                    print("Note korrigiert.")
                except ValueError as fehler:
                    print(f"Fehler: {fehler}")

    def _note_loeschen(self, sg: Studiengang, modul: Modul) -> None:
        """Loescht einen Pruefungsversuch nach Bestaetigung."""
        v_nr = self.eingabe.eingabe_zahl("Welchen Versuch loeschen?")
        if v_nr and 1 <= v_nr <= len(modul.pruefungsleistungen):
            pl = modul.pruefungsleistungen[v_nr - 1]
            antwort = input(
                f"Versuch {pl.versuchs_nummer} (Note {pl.note}) "
                f"wirklich loeschen? (j/n): "
            ).lower()
            if antwort == 'j':
                if pl.id:
                    self.db.loeschen_pruefungsleistung(pl.id)
                modul.pruefungsleistungen.remove(pl)
                modul.aktualisiere_status()
                self.db.speichern(sg)
                print("Note geloescht.")


# =====================================================================
# LernterminMenue – Lerntermin-Verwaltung
# =====================================================================

class LernterminMenue:
    """
    Untermenue fuer die Verwaltung von geplanten Lernterminen.

    Ermoeglicht das Planen neuer Termine, Bearbeiten bestehender,
    Bestaetigen (Umwandlung in Lernsession) und Loeschen.
    """

    def __init__(self, db_manager, eingabe: EingabeHelper,
                 anzeige: AnzeigeHelper) -> None:
        self.db = db_manager
        self.eingabe: EingabeHelper = eingabe
        self.anzeige: AnzeigeHelper = anzeige

    def anzeigen(self, zeiteintraege: List[ZeitEintrag],
                 sg: Optional[Studiengang]) -> List[ZeitEintrag]:
        """Zeigt das Lerntermin-Menue. Gibt die aktualisierte Zeiteintrags-Liste zurueck."""
        while True:
            termine = [t for t in zeiteintraege if isinstance(t, Lerntermin)]

            print("\n--- Lerntermine ---")
            if not termine:
                print("  Keine geplanten Termine.")
            else:
                for i, t in enumerate(termine):
                    modul_str = ""
                    name = self.anzeige.modulname_fuer_id(sg, t.modul_id)
                    if name:
                        modul_str = f" [{name}]"
                    print(f"  {i + 1}. {t.datum.strftime('%d.%m.%Y')} "
                          f"{t.start_zeit.strftime('%H:%M')}"
                          f" - {t.beschreibung} ({t.geplante_dauer} Min){modul_str}")

            print("\n(n) Neuen Termin planen")
            print("(b) Termin bearbeiten")
            print("(c) Termin bestaetigen (-> wird zur Session)")
            print("(l) Termin loeschen")
            print("(0) Zurueck")

            wahl = input("Wahl: ").strip().lower()
            if wahl == 'n':
                zeiteintraege = self._planen(zeiteintraege, sg)
            elif wahl == 'b':
                self._bearbeiten(zeiteintraege)
            elif wahl == 'c':
                zeiteintraege = self._bestaetigen(zeiteintraege)
            elif wahl == 'l':
                zeiteintraege = self._loeschen(zeiteintraege)
            elif wahl == '0':
                break

        return zeiteintraege

    def _modul_auswaehlen(self, sg: Optional[Studiengang]) -> Optional[int]:
        """Zeigt eine Modulauswahl und gibt die gewaehlte Modul-ID zurueck."""
        if not sg or not sg.module:
            return None

        print("\nModul zuordnen? (0 = kein Modul)")
        for i, mod in enumerate(sg.module):
            print(f"  {i + 1}. {mod.titel}")

        wahl = self.eingabe.eingabe_zahl("Wahl")
        if wahl and 1 <= wahl <= len(sg.module):
            return sg.module[wahl - 1].id
        return None

    def _planen(self, zeiteintraege: List[ZeitEintrag],
                sg: Optional[Studiengang]) -> List[ZeitEintrag]:
        """Erstellt einen neuen Lerntermin mit Datum, Zeit, Dauer und Beschreibung."""
        datum = self.eingabe.eingabe_datum("Datum")
        if not datum:
            return zeiteintraege

        zeit = self.eingabe.eingabe_zeit("Startzeit")
        if not zeit:
            return zeiteintraege

        dauer = self.eingabe.eingabe_zahl("Geplante Dauer in Minuten")
        if dauer is None:
            return zeiteintraege

        beschreibung = input("Beschreibung: ").strip()
        modul_id = self._modul_auswaehlen(sg)

        start_zeit = datetime.combine(datum.date(), zeit.time())
        termin = Lerntermin(datum, start_zeit, dauer, beschreibung, modul_id)
        zeiteintraege.append(termin)
        self.db.speichern_zeiteintrag(termin)
        print("Lerntermin gespeichert.")
        return zeiteintraege

    def _bearbeiten(self, zeiteintraege: List[ZeitEintrag]) -> None:
        """Bearbeitet einzelne Felder eines bestehenden Lerntermins."""
        termine = [t for t in zeiteintraege if isinstance(t, Lerntermin)]
        if not termine:
            print("Keine Termine vorhanden.")
            return

        nr = self.eingabe.eingabe_zahl("Nummer des Termins zum Bearbeiten")
        if nr is None or not (1 <= nr <= len(termine)):
            print("Ungueltige Nummer.")
            return

        termin = termine[nr - 1]
        print(f"\nBearbeite: {termin}")
        print("1. Datum aendern")
        print("2. Startzeit aendern")
        print("3. Dauer aendern")
        print("4. Beschreibung aendern")
        print("0. Zurueck")

        wahl = input("Was aendern? ").strip()

        if wahl == '1':
            neues_datum = self.eingabe.eingabe_datum("Neues Datum")
            if neues_datum:
                termin.datum = neues_datum
                termin.start_zeit = datetime.combine(
                    neues_datum.date(), termin.start_zeit.time())
        elif wahl == '2':
            neue_zeit = self.eingabe.eingabe_zeit("Neue Startzeit")
            if neue_zeit:
                termin.start_zeit = datetime.combine(
                    termin.datum.date(), neue_zeit.time())
        elif wahl == '3':
            neue_dauer = self.eingabe.eingabe_zahl("Neue Dauer in Minuten")
            if neue_dauer:
                termin.geplante_dauer = neue_dauer
        elif wahl == '4':
            neue_beschr = input("Neue Beschreibung: ").strip()
            if neue_beschr:
                termin.beschreibung = neue_beschr
        elif wahl == '0':
            return
        else:
            print("Ungueltige Wahl.")
            return

        self.db.speichern_zeiteintrag(termin)
        print("Termin aktualisiert.")

    def _bestaetigen(self, zeiteintraege: List[ZeitEintrag]) -> List[ZeitEintrag]:
        """
        Bestaetigt einen Lerntermin und wandelt ihn in eine Lernsession um.

        Der Benutzer gibt die tatsaechlich gelernte Zeit an. Der alte
        Termin wird geloescht und eine neue Session wird erstellt.
        """
        termine = [t for t in zeiteintraege if isinstance(t, Lerntermin)]
        if not termine:
            print("Keine Termine zum Bestaetigen vorhanden.")
            return zeiteintraege

        nr = self.eingabe.eingabe_zahl("Nummer des Termins zum Bestaetigen")
        if nr is None or not (1 <= nr <= len(termine)):
            print("Ungueltige Nummer.")
            return zeiteintraege

        termin = termine[nr - 1]
        print(f"\nBestaetigen: {termin.beschreibung} "
              f"(Geplant: {termin.geplante_dauer} Min)")

        tatsaechlich = self.eingabe.eingabe_zahl(
            "Wie viele Minuten hast du tatsaechlich gelernt?")
        if tatsaechlich is None:
            return zeiteintraege

        # Neue Lernsession aus dem Termin erzeugen
        end_zeit = termin.start_zeit + timedelta(minutes=tatsaechlich)
        session = Lernsession(termin.datum, termin.start_zeit, end_zeit, termin.modul_id)
        session.tatsaechliche_dauer = tatsaechlich
        zeiteintraege.append(session)
        self.db.speichern_zeiteintrag(session)

        # Alten Termin entfernen
        zeiteintraege.remove(termin)
        if termin.id:
            self.db.loeschen_zeiteintrag(termin.id)

        print(f"Termin als Session ({tatsaechlich} Min) gespeichert!")
        return zeiteintraege

    def _loeschen(self, zeiteintraege: List[ZeitEintrag]) -> List[ZeitEintrag]:
        """Loescht einen Lerntermin nach Bestaetigung."""
        termine = [t for t in zeiteintraege if isinstance(t, Lerntermin)]
        if not termine:
            print("Keine Termine vorhanden.")
            return zeiteintraege

        nr = self.eingabe.eingabe_zahl("Nummer des Termins zum Loeschen")
        if nr and 1 <= nr <= len(termine):
            termin = termine[nr - 1]
            antwort = input(
                f"'{termin.beschreibung}' wirklich loeschen? (j/n): "
            ).lower()
            if antwort == 'j':
                zeiteintraege.remove(termin)
                if termin.id:
                    self.db.loeschen_zeiteintrag(termin.id)
                print("Termin geloescht.")
        else:
            print("Ungueltige Nummer.")
        return zeiteintraege


# =====================================================================
# LernsessionMenue – Lernsession-Verwaltung
# =====================================================================

class LernsessionMenue:
    """
    Untermenue fuer die Verwaltung von Lernsessions.

    Ermoeglicht das manuelle Erfassen und Loeschen von Lernsessions.
    """

    def __init__(self, db_manager, eingabe: EingabeHelper,
                 anzeige: AnzeigeHelper) -> None:
        self.db = db_manager
        self.eingabe: EingabeHelper = eingabe
        self.anzeige: AnzeigeHelper = anzeige

    def anzeigen(self, zeiteintraege: List[ZeitEintrag],
                 sg: Optional[Studiengang]) -> List[ZeitEintrag]:
        """Zeigt das Lernsession-Menue."""
        while True:
            sessions = [s for s in zeiteintraege if isinstance(s, Lernsession)]

            print("\n--- Lernsessions ---")
            if not sessions:
                print("  Keine Sessions erfasst.")
            else:
                for i, s in enumerate(sessions):
                    modul_str = ""
                    name = self.anzeige.modulname_fuer_id(sg, s.modul_id)
                    if name:
                        modul_str = f" [{name}]"
                    print(f"  {i + 1}. {s.datum.strftime('%d.%m.%Y')} "
                          f"{s.start_zeit.strftime('%H:%M')}-"
                          f"{s.end_zeit.strftime('%H:%M')} "
                          f"({s.tatsaechliche_dauer} Min){modul_str}")

            print("\n(n) Neue Session manuell erfassen")
            print("(l) Session loeschen")
            print("(0) Zurueck")

            wahl = input("Wahl: ").strip().lower()
            if wahl == 'n':
                zeiteintraege = self._erfassen(zeiteintraege, sg)
            elif wahl == 'l':
                zeiteintraege = self._loeschen(zeiteintraege)
            elif wahl == '0':
                break

        return zeiteintraege

    def _modul_auswaehlen(self, sg: Optional[Studiengang]) -> Optional[int]:
        """Zeigt eine Modulauswahl und gibt die gewaehlte Modul-ID zurueck."""
        if not sg or not sg.module:
            return None

        print("\nModul zuordnen? (0 = kein Modul)")
        for i, mod in enumerate(sg.module):
            print(f"  {i + 1}. {mod.titel}")

        wahl = self.eingabe.eingabe_zahl("Wahl")
        if wahl and 1 <= wahl <= len(sg.module):
            return sg.module[wahl - 1].id
        return None

    def _erfassen(self, zeiteintraege: List[ZeitEintrag],
                  sg: Optional[Studiengang]) -> List[ZeitEintrag]:
        """Erfasst eine neue Lernsession mit Datum, Start- und Endzeit."""
        datum = self.eingabe.eingabe_datum("Datum")
        if not datum:
            return zeiteintraege

        start = self.eingabe.eingabe_zeit("Startzeit")
        if not start:
            return zeiteintraege

        ende = self.eingabe.eingabe_zeit("Endzeit")
        if not ende:
            return zeiteintraege

        start_zeit = datetime.combine(datum.date(), start.time())
        end_zeit = datetime.combine(datum.date(), ende.time())

        # Plausibilitaetspruefung: Endzeit muss nach Startzeit liegen
        if end_zeit <= start_zeit:
            print("Fehler: Endzeit muss nach der Startzeit liegen.")
            return zeiteintraege

        modul_id = self._modul_auswaehlen(sg)

        session = Lernsession(datum, start_zeit, end_zeit, modul_id)
        zeiteintraege.append(session)
        self.db.speichern_zeiteintrag(session)
        print(f"Session erfasst ({session.tatsaechliche_dauer} Minuten).")
        return zeiteintraege

    def _loeschen(self, zeiteintraege: List[ZeitEintrag]) -> List[ZeitEintrag]:
        """Loescht eine Lernsession nach Bestaetigung."""
        sessions = [s for s in zeiteintraege if isinstance(s, Lernsession)]
        if not sessions:
            print("Keine Sessions vorhanden.")
            return zeiteintraege

        nr = self.eingabe.eingabe_zahl("Nummer der Session zum Loeschen")
        if nr and 1 <= nr <= len(sessions):
            session = sessions[nr - 1]
            antwort = input("Wirklich loeschen? (j/n): ").lower()
            if antwort == 'j':
                zeiteintraege.remove(session)
                if session.id:
                    self.db.loeschen_zeiteintrag(session.id)
                print("Session geloescht.")
        else:
            print("Ungueltige Nummer.")
        return zeiteintraege


# =====================================================================
# DashboardAnzeige – Statistische Gesamtuebersicht
# =====================================================================

class DashboardAnzeige:
    """
    Zeigt eine ausfuehrliche Dashboard-Uebersicht mit Semesterplan,
    ECTS-Fortschritt, Notendurchschnitt und Lernzeit-Statistiken.
    """

    def __init__(self, anzeige: AnzeigeHelper) -> None:
        self.anzeige: AnzeigeHelper = anzeige

    def zeigen(self, sg: Studiengang,
               zeiteintraege: List[ZeitEintrag]) -> None:
        """Zeigt die vollstaendige Dashboard-Uebersicht fuer einen Studiengang."""
        print("\n" + "=" * 60)
        print(f"  DASHBOARD: {sg.name}")
        print("=" * 60)

        # Aktuelles Semester und zeitlicher Fortschritt
        aktuelles_sem = sg.get_aktuelles_semester()
        print(f"\n  Aktuelles Semester: {aktuelles_sem} von {sg.regelstudienzeit}")

        # ECTS-Fortschritt (erreichte / geplante ECTS)
        gesamt_ects = sum(m.ects for m in sg.module)
        erreicht_ects = sg.berechne_gesamt_fortschritt()
        prozent = round(erreicht_ects / gesamt_ects * 100) if gesamt_ects > 0 else 0
        print(f"  ECTS-Fortschritt: {erreicht_ects} / {gesamt_ects} ({prozent}%)")

        # Notendurchschnitt mit farbiger Darstellung
        schnitt = sg.berechne_durchschnitt()
        schnitt_anzeige = self.anzeige.note_farbig(schnitt, sg.zielschnitt)
        print(f"  Notendurchschnitt: {schnitt_anzeige} (Ziel: {sg.zielschnitt})")

        # Detaillierter Semesterplan
        self._zeige_semester_plan(sg, zeiteintraege, aktuelles_sem)

        # Gesamte Lernzeit mit Aufschluesselung
        sessions = [s for s in zeiteintraege if isinstance(s, Lernsession)]
        self._zeige_lernzeit(sg, sessions)

        print("\n" + "=" * 60)

    def _zeige_semester_plan(self, sg: Studiengang,
                             zeiteintraege: List[ZeitEintrag],
                             aktuelles_sem: int) -> None:
        """Zeigt den Semesterplan mit Modulen, Status und Lernzeit pro Semester."""
        print("\n  --- Semester-Plan ---")

        # Module nach Semesternummer gruppieren
        module_pro_semester = {}
        for modul in sg.module:
            sem_nr = modul.geplantes_semester
            if sem_nr not in module_pro_semester:
                module_pro_semester[sem_nr] = []
            module_pro_semester[sem_nr].append(modul)

        sessions = [s for s in zeiteintraege if isinstance(s, Lernsession)]

        for nr in range(1, sg.regelstudienzeit + 1):
            # Semester-Objekt fuer den Zeitraum finden
            sem_obj = None
            for s in sg.semester_liste:
                if s.nummer == nr:
                    sem_obj = s
                    break

            zeitraum = ""
            if sem_obj:
                zeitraum = (f"({sem_obj.start_datum.strftime('%d.%m.%Y')} - "
                           f"{sem_obj.end_datum.strftime('%d.%m.%Y')})")

            markierung = " <-- aktuell" if nr == aktuelles_sem else ""
            print(f"\n  Semester {nr} {zeitraum}{markierung}")

            # Module dieses Semesters anzeigen
            module = module_pro_semester.get(nr, [])
            if not module:
                print("    (Keine Module geplant)")
            else:
                for m in module:
                    note_str = ""
                    if m.ist_bestanden() and m.pruefungsleistungen:
                        note_str = f" - Note: {m.pruefungsleistungen[-1].note}"
                    print(f"    - {m.titel}: {m.status.value} "
                          f"({m.ects} ECTS){note_str}")

            # Lernzeit innerhalb des Semester-Zeitraums summieren
            if sem_obj:
                minuten = 0
                for sess in sessions:
                    if sem_obj.start_datum <= sess.datum <= sem_obj.end_datum:
                        minuten = minuten + sess.dauer()
                if minuten > 0:
                    print(f"    Lernzeit: {minuten // 60}h {minuten % 60}min")

    def _zeige_lernzeit(self, sg: Studiengang,
                        sessions: List[Lernsession]) -> None:
        """Zeigt die Gesamt-Lernzeit und die Lernzeit pro Modul."""
        if sessions:
            gesamt_min = sum(s.dauer() for s in sessions)
            print(f"\n  --- Gesamt-Lernzeit: "
                  f"{gesamt_min // 60}h {gesamt_min % 60}min ---")

            print("\n  Lernzeit pro Modul:")
            for modul in sg.module:
                aufwand = modul.berechne_aufwand(sessions)
                if aufwand > 0:
                    print(f"    {modul.titel}: "
                          f"{aufwand // 60}h {aufwand % 60}min")


# =====================================================================
# BenutzerMenue – Hauptmenue und Orchestrierung
# =====================================================================

class BenutzerMenue:
    """
    Zentrales Hauptmenue der Anwendung.

    Koordiniert alle spezialisierten Untermenues und steuert die
    Hauptschleife. Der DatenbankManager wird per Konstruktor
    uebergeben, alle Untermenues werden intern erstellt.
    """

    def __init__(self, db_manager) -> None:
        """
        Parameter:
            db_manager: DatenbankManager-Instanz fuer Datenbankzugriffe
        """
        self.db = db_manager
        self.studiengaenge: List[Studiengang] = []
        self.zeiteintraege: List[ZeitEintrag] = []
        self.aktueller_studiengang: Optional[Studiengang] = None
        self.archiv_offen: bool = False

        # Hilfsklassen und spezialisierte Untermenues erstellen
        self.eingabe: EingabeHelper = EingabeHelper()
        self.anzeige: AnzeigeHelper = AnzeigeHelper()
        self.sg_menue: StudiengangMenue = StudiengangMenue(db_manager, self.eingabe)
        self.modul_menue: ModulMenue = ModulMenue(db_manager, self.eingabe, self.anzeige)
        self.noten_menue: NotenMenue = NotenMenue(db_manager, self.eingabe, self.anzeige)
        self.termin_menue: LernterminMenue = LernterminMenue(
            db_manager, self.eingabe, self.anzeige)
        self.session_menue: LernsessionMenue = LernsessionMenue(
            db_manager, self.eingabe, self.anzeige)
        self.dashboard: DashboardAnzeige = DashboardAnzeige(self.anzeige)

    def daten_laden(self) -> None:
        """
        Laedt alle gespeicherten Daten aus der Datenbank und
        stellt den aktuellen Studiengang wieder her.
        """
        daten = self.db.laden()
        self.studiengaenge = daten["studiengaenge"]
        self.zeiteintraege = daten["zeiteintraege"]

        # Aktuellen Studiengang setzen oder wiederherstellen
        if self.studiengaenge and self.aktueller_studiengang is None:
            self.aktueller_studiengang = self.studiengaenge[0]

        if self.aktueller_studiengang:
            gefunden = False
            for sg in self.studiengaenge:
                if sg.id == self.aktueller_studiengang.id:
                    self.aktueller_studiengang = sg
                    gefunden = True
                    break
            if not gefunden:
                self.aktueller_studiengang = (
                    self.studiengaenge[0] if self.studiengaenge else None
                )

    def start(self) -> None:
        """Startet die interaktive Hauptschleife der Anwendung."""
        self.daten_laden()
        print("\nWillkommen beim Studenten-Dashboard!")

        while True:
            self._zeige_hauptmenue()
            wahl = input("Ihre Wahl: ").strip()

            try:
                if wahl == "1":
                    self._handle_studiengang()
                elif wahl == "2":
                    self._handle_module()
                elif wahl == "3":
                    self._handle_noten()
                elif wahl == "4":
                    self._handle_lerntermine()
                elif wahl == "5":
                    self._handle_lernsessions()
                elif wahl == "6":
                    self._handle_dashboard()
                elif wahl == "0":
                    print("Auf Wiedersehen!")
                    self.db.schliessen()
                    sys.exit()
                else:
                    print("Ungueltige Eingabe.")
            except Exception as fehler:
                print(f"Ein Fehler ist aufgetreten: {fehler}")

    def _zeige_hauptmenue(self) -> None:
        """Zeigt das Hauptmenue mit einer Kurzuebersicht des aktuellen Studiengangs."""
        sg = self.aktueller_studiengang

        print("\n" + "=" * 55)
        if sg:
            semester = sg.get_aktuelles_semester()
            schnitt = sg.berechne_durchschnitt()
            schnitt_anzeige = self.anzeige.note_farbig(schnitt, sg.zielschnitt)
            print(f"  {sg.name} | Semester {semester}/{sg.regelstudienzeit}"
                  f" | Schnitt: {schnitt_anzeige}")
        else:
            print("  Kein Studiengang ausgewaehlt")
        print("=" * 55)

        print("1. Studiengang verwalten")
        print("2. Module verwalten")
        print("3. Noten eintragen / bearbeiten")
        print("4. Lerntermine verwalten")
        print("5. Lernsessions verwalten")
        print("6. Dashboard-Uebersicht anzeigen")
        print("0. Beenden")

    def _check_studiengang(self) -> bool:
        """Prueft, ob ein Studiengang ausgewaehlt ist, und gibt eine Meldung aus."""
        if not self.aktueller_studiengang:
            print("Bitte zuerst einen Studiengang anlegen (Menuepunkt 1).")
            return False
        return True

    # --- Delegation an spezialisierte Untermenues ---

    def _handle_studiengang(self) -> None:
        """Oeffnet das Studiengang-Untermenue."""
        self.studiengaenge, self.aktueller_studiengang = self.sg_menue.anzeigen(
            self.studiengaenge, self.aktueller_studiengang
        )

    def _handle_module(self) -> None:
        """Oeffnet das Modul-Untermenue."""
        if self._check_studiengang():
            self.archiv_offen = self.modul_menue.anzeigen(
                self.aktueller_studiengang)

    def _handle_noten(self) -> None:
        """Oeffnet das Noten-Untermenue."""
        if self._check_studiengang():
            self.archiv_offen = self.noten_menue.anzeigen(
                self.aktueller_studiengang)

    def _handle_lerntermine(self) -> None:
        """Oeffnet das Lerntermin-Untermenue."""
        self.zeiteintraege = self.termin_menue.anzeigen(
            self.zeiteintraege, self.aktueller_studiengang)

    def _handle_lernsessions(self) -> None:
        """Oeffnet das Lernsession-Untermenue."""
        self.zeiteintraege = self.session_menue.anzeigen(
            self.zeiteintraege, self.aktueller_studiengang)

    def _handle_dashboard(self) -> None:
        """Oeffnet die Dashboard-Uebersicht."""
        if self._check_studiengang():
            self.dashboard.zeigen(
                self.aktueller_studiengang, self.zeiteintraege)
