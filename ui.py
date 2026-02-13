import sys
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, cast, Any

from models import Studiengang, Semester, Modul, Pruefungsleistung, Status, Lerntermin, Lernsession # type: ignore
from database import DatabaseManager # type: ignore

class BenutzerMenue:
    """
    Zuständig für die Interaktion mit dem Benutzer.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.studiengaenge = []
        self.zeiteintraege = []
        self.aktueller_studiengang: Optional[Studiengang] = None
        self.archiv_offen = False # Für das ausklappbare Archiv

    def daten_laden(self):
        """Lädt Daten und stellt die letzte Session wieder her."""
        daten = self.db.laden()
        self.studiengaenge = daten['studiengaenge']
        self.zeiteintraege = daten['zeiteintraege']
        
        # Session wiederherstellen
        last_id_str = self.db.get_setting("active_studiengang_id")
        found_sg = None
        if last_id_str:
            for sg in self.studiengaenge:
                if sg.id and str(sg.id) == last_id_str:
                    found_sg = sg
                    break
        
        # Falls aktuell gesetzt, aber Daten neu geladen -> Referenz auffrischen
        sg_current = self.aktueller_studiengang
        if sg_current is not None:
            current_id = sg_current.id
            if current_id:
                for sg in self.studiengaenge:
                    if sg.id == current_id:
                        self.aktueller_studiengang = sg
                        found_sg = sg
                        break
        
        if found_sg:
            self.aktueller_studiengang = found_sg

    def _modul_auswaehlen(self) -> Optional[int]:
        """Lässt den User ein Modul aus dem aktuellen Studiengang wählen."""
        sg = self.aktueller_studiengang
        if sg is None:
            return None
        if not sg.module:
            return None
        
        # Lokale Referenz nutzen für Linter
        module_liste = sg.module
        
        print("\nFür welches Modul? (0 für kein Modul):")
        for i, mod in enumerate(module_liste):
            print(f"{i+1}. {mod.titel}")
        
        wahl = self._input_int("Wahl")
        if wahl and 1 <= wahl <= len(module_liste):
            return module_liste[wahl-1].id
        return None

    def _zeige_modul_liste(self, sg: Studiengang, archiv_offen: bool):
        """Hilfsmethode zur Anzeige der Modulliste (Offen / Abgeschlossen)."""
        offen = [m for m in sg.module if m.status != Status.BESTANDEN]
        bestanden = [m for m in sg.module if m.status == Status.BESTANDEN]

        print(f"\n[ ] OFFENE MODULE")
        if not offen:
            print("    Keine offenen Module.")
        else:
            for mod in offen:
                idx = sg.module.index(mod) + 1
                grade_str = ""
                if mod.pruefungsleistungen:
                    grade_str = f" | Note: {mod.pruefungsleistungen[-1].note}"
                print(f"    {idx}. {mod.titel} (ECTS: {mod.ects}, Sem: {mod.geplantes_semester}{grade_str})")

        status_archiv = "▲ Einklappen" if archiv_offen else "▼ Ausklappen"
        print(f"\n[✓] ABGESCHLOSSENE MODULE ({len(bestanden)}) - [v] {status_archiv}")
        
        if archiv_offen:
            if not bestanden:
                print("    Noch keine Module abgeschlossen.")
            else:
                for mod in bestanden:
                    idx = sg.module.index(mod) + 1
                    grade_str = ""
                    if mod.pruefungsleistungen:
                        grade_str = f" | Note: {mod.pruefungsleistungen[-1].note}"
                    print(f"    {idx}. [✓] {mod.titel} (ECTS: {mod.ects}{grade_str})")

    def _update_session(self):
        """Speichert den aktuellen Studiengang in den Settings."""
        sg = self.aktueller_studiengang
        if sg and sg.id:
            self.db.save_setting("active_studiengang_id", str(sg.id))

    def _input_int(self, prompt: str) -> Optional[int]:
        while True:
            inp = input(f"{prompt} ('a' für Abbrechen): ").strip().lower()
            if inp == 'a' or inp == '': return None
            try:
                return int(inp)
            except ValueError:
                print("Bitte eine gültige Zahl eingeben.")

    def _input_float(self, prompt: str) -> Optional[float]:
        while True:
            inp = input(f"{prompt} ('a' für Abbrechen): ").strip().lower()
            if inp == 'a' or inp == '': return None
            try:
                return float(inp.replace(',', '.'))
            except ValueError:
                print("Bitte eine gültige Zahl (z.B. 1,3) eingeben.")

    def _input_datum(self, prompt: str) -> Optional[datetime]:
        while True:
            inp_str = input(f"{prompt} (TT.MM.JJJJ) ('a' für Abbrechen): ").strip().lower()
            if inp_str == 'a' or inp_str == '': return None
            try:
                # Flexibles Parsen: 8-stellig (DDMMYYYY) oder 6-stellig (DDMMYY)
                # Zuerst als Zahl prüfen, um Formatfehler auszuschließen.
                # Um Linter-Fehler beim String-Zugriff zu vermeiden, wird der Einzelzeichen-Zugriff verwendet:
                if len(inp_str) == 8 and inp_str.isdigit():
                    # d = inp_str[0:2], m = inp_str[2:4]
                    # Slicing wird vermieden, da dies hier zu Fehlermeldungen führen kann
                    d = inp_str[0] + inp_str[1]
                    m = inp_str[2] + inp_str[3]
                    y = inp_str[4] + inp_str[5] + inp_str[6] + inp_str[7]
                    inp_str = f"{d}.{m}.{y}"
                elif len(inp_str) == 6 and inp_str.isdigit():
                    d = inp_str[0] + inp_str[1]
                    m = inp_str[2] + inp_str[3]
                    y = inp_str[4] + inp_str[5]
                    inp_str = f"{d}.{m}.20{y}"

                # Prüfen auf Format
                # Slicing wird auch für die Formatprüfung vermieden
                if len(inp_str) != 10:
                    raise ValueError("Falsches Format: Länge falsch")
                if inp_str[2] != '.':
                    raise ValueError("Falsches Format: Punkt fehlt an Pos 2")
                if inp_str[5] != '.':
                    raise ValueError("Falsches Format: Punkt fehlt an Pos 5")
                
                return datetime.strptime(inp_str, "%d.%m.%Y")
            except ValueError as e:
                if "day is out of range" in str(e) or "month must be in" in str(e):
                    print(f"Dieses Datum existiert nicht! (Tipp: 2026 ist kein Schaltjahr).")
                else:
                    print("Ungültiges Format. Bitte TT.MM.JJJJ (z.B. 01.03.2026) oder DDMMYYYY (z.B. 01032026) verwenden.")

    def _input_zeit(self, prompt: str) -> Optional[datetime]:
        while True:
            inp = input(f"{prompt} (HH:MM oder HH) ('a' für Abbrechen): ").strip().lower()
            if inp == 'a' or inp == '': return None
            
            # Format-Unterstützung: Nur Stunde eingegeben (z.B. "11")
            if inp.isdigit():
                val = int(inp)
                if 0 <= val <= 23:
                    inp = f"{val:02d}:00"
                else:
                    print("Stunde muss zwischen 0 und 23 liegen.")
                    continue

            try:
                return datetime.strptime(inp, "%H:%M")
            except ValueError:
                print("Ungültiges Format. Bitte HH:MM (z.B. 11:30) oder HH (z.B. 11) verwenden.")

    def _input_dauer(self, prompt: str) -> Optional[int]:
        while True:
            inp = input(f"{prompt} (z.B. '120', '2h', '1.5h') ('a' für Abbrechen): ").strip().lower()
            if inp == 'a' or inp == '': return None
            
            # Komma durch Punkt ersetzen für Float-Parsing
            inp = inp.replace(',', '.')
            
            # Regex für Teile wie "2h", "30min", "1.5 std"
            parts = re.findall(r'(\d+(?:\.\d+)?)\s*([a-zäüöß]*)', inp)
            
            if not parts:
                print("Ungültiges Format.")
                continue
                
            total_minutes = 0.0
            found_valid = False
            
            for amount_str, unit in parts:
                if not amount_str: continue
                
                try:
                    amount = float(amount_str)
                    unit = unit.strip()
                    
                    # Logik für Einheiten
                    if not unit:
                        # Keine Einheit -> Minuten (Standard)
                        total_minutes += amount
                        found_valid = True
                    elif 'h' in unit or 'std' in unit or 'stunde' in unit: # Stunden
                        total_minutes += amount * 60
                        found_valid = True
                    elif 'm' in unit: # Minuten
                        total_minutes += amount
                        found_valid = True
                except ValueError:
                    continue
            
            if found_valid:
                return int(round(total_minutes))
            
            print("Konnte die Eingabe nicht verstehen. Bitte Minuten oder Stunden (z.B. '2h') angeben.")

    def start(self):
        """Startet die Hauptschleife."""
        self.daten_laden()
        print("\nWillkommen beim Studenten-Dashboard!")

        while True:
            self._zeige_hauptmenue()
            wahl = input("Ihre Wahl: ")

            try:
                if wahl == "1":
                    self._menu_studiengang_verwalten()
                elif wahl == "2":
                    self._menu_semester_einstellungen()
                elif wahl == "3":
                    self._menu_module_verwalten()
                elif wahl == "4":
                    self._menu_note_eintragen()
                elif wahl == "5":
                    self._menu_lerntermine_verwalten()
                elif wahl == "6":
                    self._menu_lernsessions_verwalten()
                elif wahl == "7":
                    self._zeige_statistik()
                elif wahl == "0":
                    print("Programm wird beendet.")
                    self.db.close()
                    sys.exit()
                else:
                    print("Ungültige Eingabe.")
            except Exception as e:
                print(f"Ein Fehler ist aufgetreten: {e}")

    def _zeige_hauptmenue(self):
        sg = self.aktueller_studiengang
        if sg:
            current = sg.get_aktuelles_semester_nr()
            total = sg.regelstudienzeit
            next_start = sg.get_naechstes_semester_start()
            next_str = next_start.strftime('%d.%m.%Y') if next_start else "Abschluss"
            semester_label = f"Semester ({current}/{total}, {next_str})"
            title = sg.name
            avg = sg.berechne_durchschnitt() # type: ignore
            target = sg.zielschnitt # type: ignore
            color = self._get_avg_color(avg, target)
            reset = "\033[0m" if color else ""
            print(f"\n--- Hauptmenü (Aktueller Studiengang: {title}) Schnitt: {color}{avg:.1f}{reset} ---")
        else:
            title = "Keiner ausgewählt"
            semester_label = "Semester-Einstellungen"
            print(f"\n--- Hauptmenü (Aktueller Studiengang: {title}) ---")
        print("1. Studiengang bearbeiten")
        print(f"2. {semester_label}")
        print("3. Module bearbeiten")
        print("4. Note eintragen")
        print("5. Lerntermine verwalten")
        print("6. Lernsessions verwalten")
        print("7. Statistik & Übersicht anzeigen")
        print("0. Beenden")

    def _menu_studiengang_verwalten(self):
        while True:
            sg = self.aktueller_studiengang
            print("\n--- Studiengang Verwalten ---")
            if sg:
                print(f"Aktueller Studiengang: {sg.name}")
                print("\nOptionen:")
                print(" (b) Bearbeiten (Umbenennen)")
                print(" (z) Zielschnitt festlegen")
                print(" (w) Anderen Studiengang wählen")
                print(" (n) Neuen Studiengang anlegen")
                print(" (l) Löschen")
                print(" (0) Zurück")
                wahl = input("\nIhre Wahl: ").strip().lower()
            else:
                print("(Keine Studiengänge vorhanden)")
                wahl = input("Möchten Sie einen neuen anlegen (n)? ('0' für Zurück): ").strip().lower()

            if wahl == "0":
                break
            elif wahl == "b" and sg:
                self._studiengang_umbenennen()
            elif wahl == "z" and sg:
                self._zielschnitt_festlegen()
            elif wahl == "w":
                self._studiengang_waehlen()
            elif wahl == "n":
                self._studiengang_anlegen()
            elif wahl == "l" and sg:
                self._studiengang_loeschen()
            else:
                if wahl != '0':
                    print("Ungültige Wahl.")

    def _studiengang_waehlen(self):
        if not self.studiengaenge:
            print("Keine Studiengänge zum Wählen vorhanden.")
            return
        
        print("\nVerfügbare Studiengänge:")
        for i, sg in enumerate(self.studiengaenge):
            print(f"{i+1}. {sg.name}")
        
        wahl = self._input_int("Welchen Studiengang möchten Sie wählen?")
        if wahl and 1 <= wahl <= len(self.studiengaenge):
            chosen = self.studiengaenge[wahl-1]
            self.aktueller_studiengang = chosen
            self._update_session()
            print(f"'{chosen.name}' ausgewählt.")
        elif wahl is not None:
            print("Ungültige Nummer.")

    def _studiengang_umbenennen(self):
        sg = self.aktueller_studiengang
        if not sg: return
        neu = input(f"Neuer Name für '{sg.name}' ('a' für Abbrechen): ").strip()
        if neu and neu.lower() != 'a':
            sg.name = neu
            self.db.speichern(sg)
            print("Name aktualisiert.")

    def _studiengang_loeschen(self):
        sg = self.aktueller_studiengang
        if not sg: return
        best = input(f"Möchten Sie '{sg.name}' wirklich löschen? (j/n): ").lower()
        if best == 'j' and sg.id:
            self.db.delete_studiengang(sg.id)
            self.studiengaenge.remove(sg)
            self.aktueller_studiengang = self.studiengaenge[0] if self.studiengaenge else None
            self._update_session()
            print("Erfolgreich gelöscht.")

    def _studiengang_anlegen(self):
        name = input("Name des Studiengangs ('a' für Abbrechen): ").strip()
        if not name or name.lower() == 'a': return
        
        start = self._input_datum("Startdatum des 1. Semesters")
        if not start: return
        
        neu_sg = Studiengang(name)
        neu_sg.generiere_semester(start)
        self.db.speichern(neu_sg)
        
        # ID für Session-Management holen (neu laden)
        self.daten_laden()
        # Den neuen als aktiv setzen
        for sg in self.studiengaenge:
            if sg.name == name:
                self.aktueller_studiengang = sg
                break
        self._update_session()
        print(f"Studiengang '{name}' mit 6 Semestern angelegt.")

    def _zielschnitt_festlegen(self):
        if not self._check_studiengang(): return
        sg = self.aktueller_studiengang
        if not isinstance(sg, Studiengang): return
        
        print(f"Aktueller Zielschnitt: {sg.zielschnitt:.1f}") # type: ignore
        ziel = self._input_float("Neuer Zielschnitt (z.B. 2.0)")
        if ziel is not None:
            sg.zielschnitt = ziel # type: ignore
            self.db.speichern(sg)
            print(f"Zielschnitt auf {ziel:.1f} festgelegt.")

    def _check_studiengang(self) -> bool:
        if not self.aktueller_studiengang:
            print("Bitte zuerst einen Studiengang auswählen (Menüpunkt 1).")
            return False
        return True

    def _menu_semester_einstellungen(self):
        sg = self.aktueller_studiengang
        if not sg:
            print("Zuerst einen Studiengang wählen.")
            return

        while True:
            print(f"\n--- Semester-Einstellungen: {sg.name} ---")
            print(f"Aktuelle Regelstudienzeit: {sg.regelstudienzeit} Semester")
            if sg.semester_liste:
                print(f"Aktuelles Startdatum: {sg.semester_liste[0].start_datum.strftime('%d.%m.%Y')}")

            print("\nWas möchten Sie tun?")
            print("1. Dauer & Startdatum neu festlegen (Autom. Berechnung)")
            print("0. Zurück")
            
            wahl = input("Ihre Wahl: ").strip()
            if wahl == "1":
                dauer = self._input_int("Wie viele Semester insgesamt?")
                if dauer:
                    start = self._input_datum("Wann beginnt das Studium?")
                    if start:
                        sg.regelstudienzeit = dauer
                        sg.generiere_semester(start)
                        self.db.speichern(sg)
                        print(f"Timeline wurde für {dauer} Semester neu berechnet!")
            elif wahl == "0":
                break
            else:
                print("Ungültige Wahl.")
        
    def _menu_module_verwalten(self):
        """Umfangreiches Menü zur Modulverwaltung."""
        if not self._check_studiengang(): return
        sg = cast(Studiengang, self.aktueller_studiengang)
        
        while True:
            offen = [m for m in sg.module if m.status != Status.BESTANDEN]
            bestanden = [m for m in sg.module if m.status == Status.BESTANDEN]

            print(f"\n--- Module verwalten: {sg.name} ---")
            self._zeige_modul_liste(sg, self.archiv_offen)
            
            print("\nOptionen:")
            print("n. Neues Modul hinzufügen")
            print("l. Modul löschen")
            print("u. Modul umbenennen")
            print("e. Note bearbeiten")
            print("v. Archiv aus/einklappen")
            print("0. Zurück")
            
            wahl = input("Ihre Wahl: ").strip().lower()
            if wahl == 'n':
                self._menu_modul_hinzufuegen()
            elif wahl == 'l':
                self._modul_loeschen()
            elif wahl == 'u':
                self._modul_umbenennen()
            elif wahl == 'e':
                self._modul_note_bearbeiten()
            elif wahl == 'v':
                self.archiv_offen = not self.archiv_offen
            elif wahl == '0':
                break
            else:
                print("Ungültige Wahl.")

    def _modul_loeschen(self):
        sg = cast(Studiengang, self.aktueller_studiengang)
        if not sg.module: return
        
        idx = self._input_int("Nummer des Moduls zum Löschen")
        if idx and 1 <= idx <= len(sg.module):
            mod = sg.module[idx-1]
            best = input(f"Modul '{mod.titel}' wirklich löschen? (j/n): ").lower()
            if best == 'j':
                if mod.id:
                    self.db.delete_modul(mod.id)
                sg.module.remove(mod)
                print("Modul gelöscht.")
        else:
            print("Ungültige Nummer.")

    def _modul_umbenennen(self):
        sg = cast(Studiengang, self.aktueller_studiengang)
        if not sg.module: return
        
        idx = self._input_int("Nummer des Moduls zum Umbenennen")
        if idx and 1 <= idx <= len(sg.module):
            mod = sg.module[idx-1]
            neu = input(f"Neuer Name für '{mod.titel}' ('a' für Abbrechen): ").strip()
            if neu and neu.lower() != 'a':
                mod.titel = neu
                self.db.speichern(sg)
                print("Name aktualisiert.")
        else:
            print("Ungültige Nummer.")

    def _modul_note_bearbeiten(self):
        sg = self.aktueller_studiengang
        if sg is None: return # type: ignore
        if not sg.module: return # type: ignore
        
        mod: Optional[Modul] = None
        while True:
            print("\n--- Modul für Noten-Korrektur wählen ---")
            self._zeige_modul_liste(sg, self.archiv_offen)
            
            print("\nOptionen:")
            print("v. Archiv aus/einklappen")
            print("0. Zurück / Abbrechen")
            
            wahl_raw = input("Zahl des Moduls oder Option: ").strip().lower()
            if wahl_raw == '0':
                return
            elif wahl_raw == 'v':
                self.archiv_offen = not self.archiv_offen
                continue
            
            try:
                assert sg is not None
                idx = int(wahl_raw)
                if 1 <= idx <= len(sg.module): # type: ignore
                    mod = sg.module[idx-1] # type: ignore
                    break
                else:
                    print("Ungültige Nummer.")
            except ValueError:
                print("Bitte eine Zahl oder 'v' eingeben.")

        if mod:
            assert mod is not None
            if not mod.pruefungsleistungen:
                # Hilfestellung: Falls noch keine Note da ist, direkt zum Eintragen springen
                print(f"'{mod.titel}' hat noch keine Note.")
                ja_nein = input("Möchten Sie jetzt eine Note für dieses Modul eintragen? (j/n): ").lower()
                if ja_nein == 'j':
                    note = self._input_float(f"Note für '{mod.titel}'")
                    if note is not None:
                        try:
                            mod.neue_pruefungsleistung(note)
                            self.db.speichern(sg)
                            print(f"Note {note} wurde erfolgreich eingetragen.")
                        except ValueError as e:
                            print(f"Fehler: {e}")
                return

            print(f"\n--- Note bearbeiten: {mod.titel} ---")
            for i, pl in enumerate(mod.pruefungsleistungen):
                print(f"{i+1}. Versuch: {pl.note}")
            
            v_idx = self._input_int("Nummer des Versuchs (meistens 1)")
            if v_idx and 1 <= v_idx <= len(mod.pruefungsleistungen):
                pl = mod.pruefungsleistungen[v_idx-1]
                print(f"Aktuelle Note: {pl.note}")
                
                wahl_action = input("Neue Note eingeben (n) oder diesen Eintrag löschen (l)? ").strip().lower()
                
                if wahl_action == 'l':
                    check = input(f"Wirklich löschen? (j/n): ").strip().lower()
                    if check == 'j':
                        mod.pruefungsleistungen.remove(pl)
                        if pl.id:
                            self.db.delete_pruefungsleistung(pl.id)
                        
                        # Status neu berechnen
                        if not mod.pruefungsleistungen:
                            mod.status = Status.OFFEN
                        else:
                            last = mod.pruefungsleistungen[-1]
                            if last.note <= 4.0:
                                mod.status = Status.BESTANDEN
                            elif len(mod.pruefungsleistungen) >= 3:
                                mod.status = Status.NICHT_BESTANDEN
                            else:
                                mod.status = Status.OFFEN
                        
                        self.db.speichern(sg)
                        print("Prüfungsleistung gelöscht.")
                
                else:
                    neue_note = self._input_float("Neue Note (z.B. 1,3 oder 1.3)")
                    if neue_note is not None:
                        try:
                            pl.note = neue_note # Löst ggf. ValueError aus
                            # Status aktualisieren: Prüfen ob das Modul mit dieser Note bestanden ist.
                            if pl == mod.pruefungsleistungen[-1]:
                                if neue_note <= 4.0:
                                    mod.status = Status.BESTANDEN
                                else:
                                    # Bei nicht bestandener Note: Status ist "Nicht bestanden" erst ab dem 3. Versuch,
                                    # ansonsten bleibt das Modul "Offen".
                                    if len(mod.pruefungsleistungen) >= 3:
                                        mod.status = Status.NICHT_BESTANDEN
                                    else:
                                        mod.status = Status.OFFEN
                            
                            self.db.speichern(sg)
                            print("Note wurde erfolgreich korrigiert.")
                        except ValueError as e:
                            print(f"Fehler: {e}")
            else:
                print("Ungültiger Versuch.")
        else:
            print("Ungültige Nummer.")

    def _menu_semester_hinzufuegen(self):
        """Wird durch generiere_semester meist nicht gebraucht, aber für Spezialfälle."""
        if not self._check_studiengang(): return
        sg = cast(Studiengang, self.aktueller_studiengang)

        nr = self._input_int("Semesternummer")
        if nr is None: return
        start = self._input_datum("Startdatum")
        if not start: return
        end = self._input_datum("Enddatum")
        if not end: return
        
        sg.semester_liste.append(Semester(nr, start, end))
        self.db.speichern(sg)
        print("Manuelles Semester hinzugefügt.")

    def _menu_modul_hinzufuegen(self):
        if not self._check_studiengang(): return
        sg = cast(Studiengang, self.aktueller_studiengang)
        
        titel = input("Modul-Titel ('a' für Abbrechen): ").strip()
        if not titel or titel.lower() == 'a': return
        
        ects = self._input_int("ECTS")
        if ects is None: return
        
        sem = self._input_int("Geplantes Semester (1-6)")
        if sem is None: return
        
        mod = Modul(titel, ects, geplantes_semester=sem)
        sg.module.append(mod)
        self.db.speichern(sg)
        print(f"Modul '{titel}' hinzugefügt.")

    def _menu_note_eintragen(self):
        if not self._check_studiengang(): return
        sg = self.aktueller_studiengang
        if sg is None: return # type: ignore
        
        # Die globale Variable self.archiv_offen wird verwendet, damit die Einstellung in allen Menüs gleich bleibt.
        
        while True:
            print(f"\n--- Note eintragen: {sg.name} ---") # type: ignore
            self._zeige_modul_liste(sg, self.archiv_offen)
            
            print("\nOptionen:")
            print("v. Archiv aus/einklappen")
            print("0. Zurück")
            
            wahl_raw = input("Zahl des Moduls oder Option: ").strip().lower()
            if wahl_raw == '0':
                break
            elif wahl_raw == 'v':
                self.archiv_offen = not self.archiv_offen
                continue
            
            # Versuch als Zahl zu parsen
            try:
                wahl = int(wahl_raw)
                if 1 <= wahl <= len(sg.module):
                    mod = sg.module[wahl-1]
                    print(f"Gewählt: {mod.titel}")
                    note = self._input_float(f"Note für '{mod.titel}'")
                    if note is not None:
                        try:
                            # Warnung wenn Modul schon bestanden?
                            if mod.status == Status.BESTANDEN:
                                check = input("Modul ist bereits bestanden. Wirklich neue Note eintragen? (j/n): ").lower()
                                if check != 'j': continue

                            mod.neue_pruefungsleistung(note)
                            self.db.speichern(sg)
                            print(f"Note {note} eingetragen. Neuer Status: {mod.status.value}")
                        except ValueError as e:
                            print(f"Fehler: {e}")
                else:
                    print("Ungültige Auswahl.")
            except ValueError:
                print("Ungültige Eingabe.")

    def _menu_lerntermine_verwalten(self):
        while True:
            termine: List[Lerntermin] = [t for t in self.zeiteintraege if isinstance(t, Lerntermin)]
            print("\n--- Lerntermine verwalten ---")
            if not termine:
                print("Keine geplanten Termine.")
            else:
                for i, t in enumerate(termine):
                    mod_info = ""
                    sg = self.aktueller_studiengang
                    if t.modul_id and sg:
                        # Modulname finden
                        mod = next((m for m in sg.module if m.id == t.modul_id), None)
                        if mod: mod_info = f" [{mod.titel}]"
                    print(f"{i+1}. {t.datum.strftime('%d.%m.%Y')} {t.start_zeit.strftime('%H:%M')} - {t.beschreibung} ({t.geplante_dauer} Min){mod_info}")
            
            print("\nOptionen:")
            print("n. Neuen Termin planen")
            print("e. Termin bearbeiten")
            print("c. Termin bestätigen (in Session umwandeln)")
            print("l. Termin löschen")
            print("0. Zurück")
            
            wahl = input("Ihre Wahl: ").strip().lower()
            if wahl == '0': break
            elif wahl == 'n':
                self._menu_lerntermin_planen()
            elif wahl == 'l':
                idx = self._input_int("Nummer des Termins zum Löschen")
                if idx and 1 <= idx <= len(termine):
                    termin: Lerntermin = termine[idx-1]
                    self.zeiteintraege.remove(termin)
                    if termin.id: self.db.delete_zeit_eintrag(termin.id)
                    print("Termin gelöscht.")
                else:
                    print("Ungültige Nummer.")
            elif wahl == 'e':
                self._lerntermin_bearbeiten(termine)
            elif wahl == 'c':
                self._lerntermin_bestaetigen(termine)

    def _lerntermin_bearbeiten(self, termine: List[Lerntermin]):
        idx = self._input_int("Nummer des Termins zum Bearbeiten")
        # Sicherstellen, dass idx eine Ganzzahl ist, um Fehleranzeigen zu vermeiden
        if idx is None:
            print("Ungültige Nummer.")
            return
            
        if not (1 <= idx <= len(termine)):
            print("Ungültige Nummer.")
            return

        termin = termine[idx-1]
        print(f"\nBearbeite Termin: {termin}")
        print("1. Datum")
        print("2. Startzeit")
        print("3. Dauer")
        print("4. Beschreibung")
        print("5. Modul")
        print("0. Zurück")

        wahl = input("Was möchten Sie ändern? (1-5): ").strip()
        
        changed = False
        if wahl == '1':
            neues_datum = self._input_datum("Neues Datum")
            if neues_datum:
                # Zeitkomponente erhalten
                zeit = termin.start_zeit.time()
                termin.datum = neues_datum
                termin.start_zeit = datetime.combine(neues_datum.date(), zeit)
                changed = True
        elif wahl == '2':
            neue_zeit = self._input_zeit("Neue Startzeit")
            if neue_zeit:
                termin.start_zeit = datetime.combine(termin.datum.date(), neue_zeit.time())
                changed = True
        elif wahl == '3':
            neue_dauer = self._input_dauer("Neue Dauer")
            if neue_dauer:
                termin.geplante_dauer = neue_dauer
                changed = True
        elif wahl == '4':
            neue_desc = input("Neue Beschreibung: ").strip()
            if neue_desc:
                termin.beschreibung = neue_desc
                changed = True
        elif wahl == '5':
            neue_mod_id = self._modul_auswaehlen()
            termin.modul_id = neue_mod_id
            changed = True
        elif wahl == '0':
            return
        else:
            print("Ungültige Auswahl.")

        if changed:
            self.db.speichern(termin)
            print("Termin aktualisiert.")

    def _lerntermin_bestaetigen(self, termine: List[Lerntermin]):
        idx = self._input_int("Nummer des Termins zum Bestätigen")
        if idx is None:
            print("Ungültige Nummer.")
            return
            
        if not (1 <= idx <= len(termine)):
            print("Ungültige Nummer.")
            return

        termin = termine[idx-1]
        print(f"\nBestätige Termin: {termin.beschreibung} (Geplant: {termin.geplante_dauer} min)")
        
        tatsaechlich = self._input_dauer("Tatsächliche Dauer")
        if tatsaechlich is None: return

        # Neue Session erstellen
        end_zeit = termin.start_zeit + timedelta(minutes=tatsaechlich)
        session = Lernsession(termin.datum, termin.start_zeit, end_zeit)
        # Manuelles Setzen der berechneten Dauer, falls Abweichungen durch Rundung etc.
        session.tatsaechliche_dauer = tatsaechlich

        # 1. Termin löschen
        if termin in self.zeiteintraege:
            self.zeiteintraege.remove(termin)
        if termin.id:
            self.db.delete_zeit_eintrag(termin.id)
        
        # 2. Session speichern
        session.modul_id = termin.modul_id # Modul-Verknüpfung übernehmen
        self.zeiteintraege.append(session)
        self.db.speichern(session)

        print(f"Termin als Session ({tatsaechlich} Min) bestätigt und gespeichert.")


    def _menu_lerntermin_planen(self):
        datum = self._input_datum("Datum")
        if not datum: return
        
        zeit = self._input_zeit("Startzeit")
        if not zeit: return
        
        # Datum und Zeit kombinieren
        full_zeit = datetime.combine(datum.date(), zeit.time())
            
        duration = self._input_dauer("Dauer")
        if duration is None: return
        
        mod_id = self._modul_auswaehlen()
        
        desc = input("Beschreibung: ").strip()
        
        termin = Lerntermin(datum, full_zeit, duration, desc, modul_id=mod_id)
        self.zeiteintraege.append(termin)
        self.db.speichern(termin)
        print("Termin gespeichert.")

    def _menu_lernsessions_verwalten(self):
        while True:
            sessions: List[Lernsession] = [s for s in self.zeiteintraege if isinstance(s, Lernsession)]
            print("\n--- Lernsessions verwalten ---")
            if not sessions:
                print("Keine erfassten Sessions.")
            else:
                for i, s in enumerate(sessions):
                    mod_info = ""
                    sg = self.aktueller_studiengang
                    if s.modul_id and sg:
                        mod = next((m for m in sg.module if m.id == s.modul_id), None)
                        if mod: mod_info = f" [{mod.titel}]"
                    print(f"{i+1}. {s.datum.strftime('%d.%m.%Y')} {s.start_zeit.strftime('%H:%M')} - {s.end_zeit.strftime('%H:%M')} ({s.tatsaechliche_dauer} Min){mod_info}")
            
            print("\nOptionen:")
            print("n. Neue Session erfassen")
            print("s. Timer starten (Live)")
            print("b. Session bearbeiten")
            print("l. Session löschen")
            print("0. Zurück")
            
            wahl = input("Ihre Wahl: ").strip().lower()
            if wahl == '0': break
            elif wahl == 'n':
                self._menu_lernsession_erfassen()
            elif wahl == 's':
                self._menu_lernsession_timer()
            elif wahl == 'b':
                self._menu_lernsession_bearbeiten()
            elif wahl == 'l':
                idx = self._input_int("Nummer der Session zum Löschen")
                if idx and 1 <= idx <= len(sessions):
                    sess: Lernsession = sessions[idx-1]
                    self.zeiteintraege.remove(sess)
                    if sess.id: self.db.delete_zeit_eintrag(sess.id)
                    print("Session gelöscht.")
                else:
                    print("Ungültige Nummer.")

    def _menu_lernsession_bearbeiten(self):
        sessions: List[Lernsession] = [s for s in self.zeiteintraege if isinstance(s, Lernsession)]
        if not sessions:
            print("Keine Sessions vorhanden.")
            return

        idx = self._input_int("Nummer der Session zum Bearbeiten")
        if idx is None or not (1 <= idx <= len(sessions)):
            print("Ungültige Nummer.")
            return

        assert idx is not None
        sess: Lernsession = sessions[idx-1]
        print(f"\n--- Session Bearbeiten ---")
        print(f"Aktuell: {sess.datum.strftime('%d.%m.%Y')} {sess.start_zeit.strftime('%H:%M')} - {sess.end_zeit.strftime('%H:%M')}")
        
        # Datum ändern
        datum_neu = self._input_datum("Neues Datum (Leer lassen für unverändert)")
        if datum_neu:
            sess.datum = datum_neu
        
        # Zeiten ändern
        t_start = self._input_zeit("Neue Startzeit (Leer lassen für unverändert)")
        t_end = self._input_zeit("Neue Endzeit (Leer lassen für unverändert)")

        # Basis-Datum für Start/Ende
        base_date = sess.datum.date()

        if t_start:
            sess.start_zeit = datetime.combine(base_date, t_start.time())
        elif datum_neu:
             # Datum geändert, Zeit gleich -> Startzeit Datum anpassen
             sess.start_zeit = datetime.combine(base_date, sess.start_zeit.time())

        if t_end:
            sess.end_zeit = datetime.combine(base_date, t_end.time())
        elif datum_neu:
            # Datum geändert, Zeit gleich -> Endzeit Datum anpassen
            sess.end_zeit = datetime.combine(base_date, sess.end_zeit.time())

        # Modul ändern
        print(f"Aktuelles Modul-ID: {sess.modul_id if sess.modul_id else 'Keines'}")
        if input("Modul ändern? (j/N): ").strip().lower() == 'j':
            neue_mod_id = self._modul_auswaehlen()
            sess.modul_id = neue_mod_id

        # Validierung
        if sess.end_zeit <= sess.start_zeit:
            print("Fehler: Endzeit muss nach Startzeit liegen. Änderungen verworfen.")
            print("Bitte korrigieren Sie die Zeiten manuell erneut.")
        else:
            # Dauer update
            sess.tatsaechliche_dauer = sess._berechne_dauer()
            self.db.speichern(sess)
            print(f"Session aktualisiert ({sess.tatsaechliche_dauer} Min).")

    def _menu_lernsession_erfassen(self):
        datum = self._input_datum("Datum")
        if not datum: return
        
        start = self._input_zeit("Startzeit")
        if not start: return
        
        ende = self._input_zeit("Endzeit")
        if not ende: return

        # Datum kombinieren
        full_start = datetime.combine(datum.date(), start.time())
        full_ende = datetime.combine(datum.date(), ende.time())
        
        if full_ende <= full_start:
            print("Fehler: Endzeit muss nach der Startzeit liegen.")
            return

        mod_id = self._modul_auswaehlen()
        session = Lernsession(datum, full_start, full_ende, modul_id=mod_id)
        self.zeiteintraege.append(session)
        self.db.speichern(session)
        print(f"Session erfasst ({session.tatsaechliche_dauer} Min).")

    def _menu_lernsession_timer(self):
        print("\n--- Live Lernsession Timer ---")
        start_zeit = datetime.now()
        elapsed_before_pause = 0.0
        is_paused = False
        pause_start = 0.0
        
        last_tick = time.time()
        
        print(f"Start um {start_zeit.strftime('%H:%M:%S')}")
        mod_id = self._modul_auswaehlen()
        print("Befehle: (p) Pause/Weiter, (s) Stop & Speichern, (a) Abbrechen")
        
        try:
            while True:
                if not is_paused:
                    # Da die Funktion input() den Programmablauf blockiert, wird die Zeit
                    # nicht kontinuierlich aktualisiert, sondern bei jeder Eingabe neu berechnet.
                    # (Eine Live-Anzeige würde komplexere Techniken wie Threads erfordern.)
                    pass
                
                current_total = int((elapsed_before_pause + (0 if is_paused else time.time() - last_tick)) / 60)
                status_text = "PAUSIERT" if is_paused else "LÄUFT"
                wahl = input(f"\n[Timer {status_text}: {current_total} Min] Wahl (p=Pause/Weiter, s=Stop, a=Abbruch): ").strip().lower()
                
                if wahl == 'p':
                    if not is_paused:
                        # Pausieren
                        elapsed_before_pause += (time.time() - last_tick)
                        is_paused = True
                        print(f"Timer pausiert. (lief bisher {int(elapsed_before_pause/60)} Min)")
                    else:
                        # Fortsetzen
                        last_tick = time.time()
                        is_paused = False
                        print("Timer läuft weiter...")
                
                elif wahl == 's':
                    # Beenden & Speichern
                    if not is_paused:
                        elapsed_before_pause += (time.time() - last_tick)
                    
                    minuten = int(elapsed_before_pause / 60)
                    if minuten < 1:
                        print("Session zu kurz zum Speichern (unter 1 Minute).")
                    else:
                        ende_zeit = datetime.now()
                        # start_zeit ist der Zeitpunkt des Timer-Starts
                        session = Lernsession(start_zeit, start_zeit, ende_zeit, modul_id=mod_id)
                        session.tatsaechliche_dauer = minuten
                        self.zeiteintraege.append(session)
                        self.db.speichern(session)
                        print(f"Lernsession gespeichert: {minuten} Minuten.")
                    break
                
                elif wahl == 'a':
                    print("Timer abgebrochen. Nichts gespeichert.")
                    break
        except KeyboardInterrupt:
            print("\nTimer abgebrochen.")


    def _get_avg_color(self, avg: float, target: float) -> str:
        """Gibt den ANSI Color Code basierend auf Schnitt vs Ziel zurück."""
        if avg == 0.0: return "" # Noch keine Noten
        
        green = "\033[92m"
        orange = "\033[93m"
        red = "\033[91m"
        
        if avg <= target:
            return green
        elif avg <= 3.0:
            return orange
        else:
            return red


    def _zeige_statistik(self):
        if not self._check_studiengang(): return
        sg = self.aktueller_studiengang
        if sg is None: return # type: ignore
        
        print(f"\n--- Studium-Übersicht: {sg.name} ---") # type: ignore
        print(f"Fortschritt: {sg.berechne_fortschritt()} ECTS") # type: ignore
        
        avg = sg.berechne_durchschnitt() # type: ignore
        target = sg.zielschnitt # type: ignore
        
        color_code = self._get_avg_color(avg, target)
        reset = "\033[0m" if color_code else ""
            
        print(f"Schnitt: {avg:.1f} | {color_code}Ziel: {target:.1f}{reset}")
        
        # Lernzeit pro Semester vorberechnen
        sessions: List[Lernsession] = [z for z in self.zeiteintraege if isinstance(z, Lernsession)]
        sem_minutes: dict[int, int] = {} 
        total_global = 0

        for sess in sessions:
            dur = int(sess.tatsaechliche_dauer)
            total_global += dur
            # Semester finden
            found = False
            for sem in sg.semester_liste: # type: ignore
                # Datum-Vergleich (alles datetime)
                if sem.start_datum <= sess.datum <= sem.end_datum:
                    sem_minutes[sem.nummer] = sem_minutes.get(sem.nummer, 0) + dur
                    found = True
                    break
        
        print("\n--- Semester-Plan ---")
        # Module gruppieren
        by_sem: dict[int, list[Modul]] = {}
        for m in sg.module: # type: ignore
            s_num = m.geplantes_semester
            if s_num not in by_sem:
                by_sem[s_num] = []
            by_sem[s_num].append(m)
            
        for s in range(1, sg.regelstudienzeit + 1): # type: ignore
            sem_data = next((sem for sem in sg.semester_liste if sem.nummer == s), None) # type: ignore
            zeit = f"({sem_data})" if sem_data else ""
            print(f"\nSemester {s} {zeit}:")
            
            # Module anzeigen
            mods = by_sem.get(s, [])
            if not mods:
                print("  (Keine Module)")
            else:
                for mm in mods:
                    note_str = ""
                    if mm.status == Status.BESTANDEN and mm.pruefungsleistungen:
                        # Letzte Note anzeigen (davon ausgehend, dass diese die bestanden Note ist)
                        note_str = f" | Note: {mm.pruefungsleistungen[-1].note}"
                    print(f"  - {mm.titel}: {mm.status.value} ({mm.ects} ECTS){note_str}")
            
            # Lernzeit für dieses Semester anzeigen
            mins = sem_minutes.get(s, 0)
            print(f"  Lernzeit: {mins // 60}h {mins % 60}min")

        print("\n--- Gesamt-Lernzeit ---")
        total_global_int: int = total_global
        print(f"Gesamt: {total_global_int // 60}h {total_global_int % 60}min")
