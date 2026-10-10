import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from src.infrastructure.app_paths import db_path as default_db_path
from src.infrastructure.database.sqlite_repository import SQLiteHuntRepository
from src.infrastructure.parser.log_parser import LogParser
from src.ui.main_window import MainApp

SAMPLE_DB = Path(__file__).parent / "samples" / "sample_hunts.db"


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = Path(__file__).parent  # adjust based on location
    return Path(base_path) / relative_path


def parse_args():
    parser = argparse.ArgumentParser(description="Hunt Analyzer — análise de sessões de caça do Tibia")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo", action="store_true",
                       help="abre uma cópia temporária do banco de exemplo (samples/sample_hunts.db)")
    group.add_argument("--db", metavar="CAMINHO", help="usa um arquivo de banco específico")
    return parser.parse_args()


def resolve_db(args) -> str:
    if args.demo:
        # Copia o banco de exemplo para um arquivo temporário, para não alterá-lo
        tmp = Path(tempfile.gettempdir()) / "hunt_analyzer_demo.db"
        shutil.copy2(SAMPLE_DB, tmp)
        print(f"[Hunt Analyzer] Modo demo: {tmp}")
        return str(tmp)
    if args.db:
        return args.db
    return default_db_path()


if __name__ == "__main__":
    args = parse_args()
    db_path = resolve_db(args)
    print(f"[Hunt Analyzer] Banco de dados: {db_path}")

    # Dependency Injection Container (Manually)
    repository = SQLiteHuntRepository(db_path)
    parser = LogParser()

    app = MainApp(repository=repository, parser=parser)
    app.mainloop()
