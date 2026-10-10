"""Onde o Hunt Analyzer guarda os dados do usuário.

O banco (tibia_hunts.db) e a configuração (config.json) ficam numa pasta de
dados do sistema, fora do repositório:

- macOS:   ~/Library/Application Support/HuntAnalyzer
- Windows: %APPDATA%\\HuntAnalyzer
- Linux:   ~/.local/share/HuntAnalyzer

Assim, atualizar o projeto com `git pull` nunca apaga as hunts e os dados
pessoais não vão para o GitHub por acidente. A variável de ambiente
HUNT_ANALYZER_DATA_DIR permite escolher outra pasta.

Migração: se o arquivo ainda não existir na pasta de dados, mas existir na
pasta do projeto (local antigo), ele é COPIADO para a pasta nova. O original
não é apagado e continua servindo de backup.
"""
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "HuntAnalyzer"
DB_FILENAME = "tibia_hunts.db"
CONFIG_FILENAME = "config.json"


def data_dir() -> Path:
    override = os.environ.get("HUNT_ANALYZER_DATA_DIR")
    if override:
        base = Path(override).expanduser()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def project_dir() -> Path:
    # src/infrastructure/app_paths.py -> raiz do projeto
    return Path(__file__).resolve().parents[2]


def _legacy_dirs() -> list:
    dirs = []
    for d in (project_dir(), Path.cwd()):
        if d not in dirs:
            dirs.append(d)
    return dirs


def _resolve(filename: str) -> Path:
    target = data_dir() / filename
    if not target.exists():
        for folder in _legacy_dirs():
            legacy = folder / filename
            if legacy.is_file():
                shutil.copy2(legacy, target)
                print(f"[Hunt Analyzer] {filename} copiado de {legacy} para {target}")
                break
    return target


def db_path() -> str:
    return str(_resolve(DB_FILENAME))


def config_path() -> str:
    return str(_resolve(CONFIG_FILENAME))
