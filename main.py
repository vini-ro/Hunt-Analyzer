import sys
from pathlib import Path
from src.infrastructure.database.sqlite_repository import SQLiteHuntRepository
from src.infrastructure.parser.log_parser import LogParser
from src.ui.main_window import MainApp

# Placeholder for the future Main Entry Point using Clean Architecture
# Ideally, you will instantiate SQLiteHuntRepository here, pass it to a Controller/ViewModel
# And the ViewModel will be passed to the Tkinter View.

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = Path(__file__).parent # adjust based on location
    return Path(base_path) / relative_path

if __name__ == "__main__":
    # Dependency Injection Container (Manually)
    db_path = "tibia_hunts.db"
    repository = SQLiteHuntRepository(db_path)
    parser = LogParser()
    
    app = MainApp(repository=repository, parser=parser)
    app.mainloop()
