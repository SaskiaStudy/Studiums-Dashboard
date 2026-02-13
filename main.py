from database import DatabaseManager # type: ignore
from ui import BenutzerMenue # type: ignore

def main():
    # Datenbank-Manager initialisieren
    db_manager = DatabaseManager("dashboard.db")
    
    # Stellen sicher, dass Tabellen existieren
    print("Initialisiere Datenbank...")
    db_manager.tabellen_erstellen()
    
    # Menü erstellen und starten
    menue = BenutzerMenue(db_manager)
    menue.start()

if __name__ == "__main__":
    main()