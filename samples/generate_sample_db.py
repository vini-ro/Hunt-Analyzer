"""Gera samples/sample_hunts.db com hunts fictícias para demonstração.

Uso (a partir da raiz do projeto):
    python3 samples/generate_sample_db.py

Os logs são gerados no mesmo formato da janela "Hunting Session" do Tibia e
passam pelo LogParser do app, então o banco de exemplo exercita o mesmo
caminho de importação usado com logs reais. Personagens e números são
inventados.
"""
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.entities import Hunt, Monster  # noqa: E402
from src.infrastructure.database.sqlite_repository import SQLiteHuntRepository  # noqa: E402
from src.infrastructure.parser.log_parser import LogParser  # noqa: E402

OUT = ROOT / "samples" / "sample_hunts.db"
SEED = 42
N_HUNTS = 60
END_DATE = date(2026, 10, 10)

CHARACTERS = {"Demo Knight": 1.0, "Demo Druid": 0.8}
SPOTS = {
    "Cobra Bastion": (["Cobra Assassin", "Cobra Scout", "Cobra Vizier"], 4_500_000, 220_000),
    "Falcon Bastion": (["Falcon Knight", "Falcon Paladin"], 5_200_000, 260_000),
    "Roshamuul Prison": (["Guzzlemaw", "Frazzlemaw", "Silencer"], 3_800_000, 150_000),
    "Issavi Sewers": (["Lavafungus", "Lavaworm", "Streaked Devourer"], 3_000_000, 120_000),
    "Soul War": (["Vibrant Phantom", "Courage Leech", "Bony Sea Devil"], 7_000_000, 380_000),
}


def fmt(n: int) -> str:
    return f"{n:,}"


def build_log(start: datetime, minutes: int, raw_xp: int, loot: int, supplies: int,
              damage: int, healing: int, monsters: list) -> str:
    end = start + timedelta(minutes=minutes)
    lines = [
        f"Session data: From {start:%Y-%m-%d, %H:%M:%S} to {end:%Y-%m-%d, %H:%M:%S}",
        f"Session: {minutes // 60:02d}:{minutes % 60:02d}h",
        f"Raw XP Gain: {fmt(raw_xp)}",
        f"XP Gain: {fmt(int(raw_xp * 1.5))}",
        f"Raw XP/h: {fmt(int(raw_xp * 60 / minutes))}",
        f"XP/h: {fmt(int(raw_xp * 1.5 * 60 / minutes))}",
        f"Loot: {fmt(loot)}",
        f"Supplies: {fmt(supplies)}",
        f"Balance: {fmt(loot - supplies)}",
        f"Damage: {fmt(damage)}",
        f"Damage/h: {fmt(int(damage * 60 / minutes))}",
        f"Healing: {fmt(healing)}",
        f"Healing/h: {fmt(int(healing * 60 / minutes))}",
        "Killed Monsters:",
        *[f"  {qty}x {name}" for name, qty in monsters],
        "Looted Items:",
        "  None",
    ]
    return "\n".join(lines)


def main() -> None:
    random.seed(SEED)
    if OUT.exists():
        OUT.unlink()
    repo = SQLiteHuntRepository(str(OUT))
    parser = LogParser()

    for _ in range(N_HUNTS):
        char = random.choice(list(CHARACTERS))
        spot = random.choice(list(SPOTS))
        mobs, xp_per_hour, profit_per_hour = SPOTS[spot]
        skill = CHARACTERS[char] * random.uniform(0.75, 1.25)
        minutes = random.choice([45, 60, 75, 90, 120, 150])
        day = END_DATE - timedelta(days=random.randint(0, 120))
        start = datetime(day.year, day.month, day.day, random.randint(8, 23), random.randint(0, 59), 0)

        raw_xp = int(xp_per_hour * skill * minutes / 60)
        supplies = int(random.uniform(60_000, 140_000) * minutes / 60)
        loot = supplies + int(profit_per_hour * skill * random.uniform(-0.3, 1.4) * minutes / 60)
        damage = int(raw_xp * random.uniform(0.9, 1.4))
        healing = int(damage * random.uniform(0.4, 0.8))
        monsters = [(m, int(random.uniform(150, 600) * minutes / 60)) for m in mobs]

        text = build_log(start, minutes, raw_xp, loot, supplies, damage, healing, monsters)
        info = parser.parse_hunt_data(text)
        repo.save(Hunt(
            id=None, character=char, location=spot,
            date=info["data_inicio"], start_time=info["hora_inicio"], end_time=info["hora_fim"],
            duration_min=info["duracao_min"], raw_xp_gain=info["raw_xp_gain"], xp_gain=info["xp_gain"],
            loot=info["loot"], supplies=info["supplies"], balance=info["balance"],
            damage=info["damage"], healing=info["healing"], raw_text=text,
            monsters=[Monster(name=n, amount=q) for n, q in parser.extract_monsters(text)],
        ))

    # Deixa só os personagens fictícios, com "Demo Knight" como padrão
    with sqlite3.connect(OUT) as conn:
        names = list(CHARACTERS)
        conn.execute(f"DELETE FROM Characters WHERE nome NOT IN ({','.join('?' * len(names))})", names)
        conn.execute("UPDATE Characters SET is_default = (nome = 'Demo Knight')")
        conn.execute("DELETE FROM Locations WHERE nome NOT IN (SELECT DISTINCT local FROM Hunts)")
    with sqlite3.connect(OUT) as conn:
        conn.execute("VACUUM")
    print(f"{OUT} gerado com {N_HUNTS} hunts fictícias")


if __name__ == "__main__":
    main()
