import sqlite3
from typing import List, Optional, Dict, Tuple
from contextlib import closing
from src.domain.entities import Hunt, Monster
from src.application.interfaces.repository import HuntRepository

class SQLiteHuntRepository(HuntRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable name-based access
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        with closing(self._get_connection()) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS Characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS Locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS Hunts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem TEXT NOT NULL,
                local TEXT NOT NULL,
                data TEXT,
                hora_inicio TEXT,
                hora_fim TEXT,
                duracao_min INTEGER,
                raw_xp_gain INTEGER,
                xp_gain INTEGER,
                loot INTEGER,
                supplies INTEGER,
                pagamento INTEGER,
                balance INTEGER,
                damage INTEGER,
                healing INTEGER,
                raw_text TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS Hunts_Monstros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hunt_id INTEGER NOT NULL,
                personagem TEXT NOT NULL,
                criatura TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                FOREIGN KEY(hunt_id) REFERENCES Hunts(id) ON DELETE CASCADE
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS Settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)

            cursor = conn.execute("SELECT COUNT(*) FROM Characters")
            if cursor.fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO Characters (nome, is_default) VALUES (?, 1)",
                    ("Nerdola Farmador",),
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM Characters WHERE is_default = 1")
                if cursor.fetchone()[0] == 0:
                    conn.execute(
                        "UPDATE Characters SET is_default = 1 WHERE id = (SELECT id FROM Characters LIMIT 1)"
                    )
            conn.commit()

    def save(self, hunt: Hunt) -> int:
        with closing(self._get_connection()) as conn:
            with conn: # Transaction context
                # Ensure Character and Location exist
                conn.execute("INSERT OR IGNORE INTO Characters (nome) VALUES (?)", (hunt.character,))
                conn.execute("INSERT OR IGNORE INTO Locations (nome) VALUES (?)", (hunt.location,))
                
                cur = conn.execute(
                    """
                    INSERT INTO Hunts (
                        personagem, local, data, hora_inicio, hora_fim, duracao_min,
                        raw_xp_gain, xp_gain, loot, supplies, pagamento, balance, damage, healing, raw_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        hunt.character, hunt.location, hunt.date, hunt.start_time, hunt.end_time,
                        hunt.duration_min, hunt.raw_xp_gain, hunt.xp_gain, hunt.loot, hunt.supplies,
                        hunt.payment, hunt.balance, hunt.damage, hunt.healing, hunt.raw_text
                    ),
                )
                hunt_id = cur.lastrowid
                
                if hunt.monsters:
                    data_monsters = [
                        (hunt_id, hunt.character, m.name, m.amount)
                        for m in hunt.monsters
                    ]
                    conn.executemany(
                        "INSERT INTO Hunts_Monstros (hunt_id, personagem, criatura, quantidade) VALUES (?, ?, ?, ?)",
                        data_monsters
                    )
                return hunt_id

    def _row_to_hunt(self, row, monsters: List[Monster] = None) -> Hunt:
        return Hunt(
            id=row["id"],
            character=row["personagem"],
            location=row["local"],
            date=row["data"],
            start_time=row["hora_inicio"],
            end_time=row["hora_fim"],
            duration_min=row["duracao_min"],
            raw_xp_gain=row["raw_xp_gain"],
            xp_gain=row["xp_gain"],
            loot=row["loot"],
            supplies=row["supplies"],
            balance=row["balance"],
            damage=row["damage"],
            healing=row["healing"],
            raw_text=row["raw_text"] if "raw_text" in row.keys() else "",
            monsters=monsters or []
        )

    def get_all(self, filters: dict) -> List[Hunt]:
        where = []
        params = []
        if filters.get("character") and filters["character"] != "Todos":
            where.append("personagem = ?")
            params.append(filters["character"])
        if filters.get("location_like"):
            where.append("local LIKE ?")
            params.append(f"%{filters['location_like']}%")
        
        # Date range filtering
        if filters.get("date_start"):
            where.append("data >= ?")
            params.append(filters["date_start"])
        if filters.get("date_end"):
            where.append("data <= ?")
            params.append(filters["date_end"])
        
        # Specific exact match (for auto-check/duplicates)
        if filters.get("date"):
            where.append("data = ?")
            params.append(filters["date"])
        if filters.get("start_time"):
            where.append("hora_inicio = ?")
            params.append(filters["start_time"])

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        
        sql = f"""
            SELECT id, data, hora_inicio, hora_fim, duracao_min, personagem, local,
                   xp_gain, loot, supplies, pagamento, balance, raw_xp_gain, damage, healing, raw_text
            FROM Hunts
            {where_sql}
            ORDER BY COALESCE(data,'9999-99-99') DESC, COALESCE(hora_inicio,'00:00:00') DESC, id DESC
        """
        
        with closing(self._get_connection()) as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [self._row_to_hunt(row) for row in rows]

    def get_by_id(self, hunt_id: int) -> Optional[Hunt]:
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT * FROM Hunts WHERE id = ?", (hunt_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            m_cursor = conn.execute(
                "SELECT criatura, quantidade FROM Hunts_Monstros WHERE hunt_id = ? ORDER BY quantidade DESC",
                (hunt_id,)
            )
            monsters = [Monster(name=r["criatura"], amount=r["quantidade"], hunt_id=hunt_id) for r in m_cursor.fetchall()]
            
            return self._row_to_hunt(row, monsters)

    def delete_many(self, item_ids: List[int]) -> None:
         with closing(self._get_connection()) as conn:
             with conn:
                placeholders = ",".join("?" for _ in item_ids)
                conn.execute(f"DELETE FROM Hunts WHERE id IN ({placeholders})", tuple(item_ids))

    def update(self, hunt: Hunt) -> None:
         with closing(self._get_connection()) as conn:
            with conn:
                conn.execute("INSERT OR IGNORE INTO Characters (nome) VALUES (?)", (hunt.character,))
                conn.execute("INSERT OR IGNORE INTO Locations (nome) VALUES (?)", (hunt.location,))

                conn.execute("""
                    UPDATE Hunts
                    SET personagem=?, local=?, data=?, hora_inicio=?, hora_fim=?, duracao_min=?,
                        raw_xp_gain=?, xp_gain=?, loot=?, supplies=?, pagamento=?, balance=?, damage=?, healing=?
                    WHERE id = ?
                """, (
                    hunt.character, hunt.location, hunt.date, hunt.start_time, hunt.end_time,
                    hunt.duration_min, hunt.raw_xp_gain, hunt.xp_gain, hunt.loot, hunt.supplies,
                    hunt.payment, hunt.balance, hunt.damage, hunt.healing, hunt.id
                ))
                conn.execute("UPDATE Hunts_Monstros SET personagem=? WHERE hunt_id=?", (hunt.character, hunt.id))

    def update_many(self, ids: List[int], updates: dict) -> None:
         with closing(self._get_connection()) as conn:
            with conn:
                qmarks = ",".join("?" for _ in ids)
                
                if "character" in updates:
                     conn.execute("INSERT OR IGNORE INTO Characters (nome) VALUES (?)", (updates["character"],))
                     conn.execute(f"UPDATE Hunts SET personagem=? WHERE id IN ({qmarks})", tuple([updates["character"]] + ids))
                     conn.execute(f"UPDATE Hunts_Monstros SET personagem=? WHERE hunt_id IN ({qmarks})", tuple([updates["character"]] + ids))
                
                if "location" in updates:
                     conn.execute("INSERT OR IGNORE INTO Locations (nome) VALUES (?)", (updates["location"],))
                     conn.execute(f"UPDATE Hunts SET local=? WHERE id IN ({qmarks})", tuple([updates["location"]] + ids))

    def get_analytics(self, filters: dict) -> dict:
        where = []
        params = []
        if filters.get("character") and filters["character"] != "Todos":
            where.append("h.personagem = ?")
            params.append(filters["character"])
        
        if filters.get("date_start") and filters.get("date_end"):
            where.append("h.data >= ? AND h.data <= ?")
            params.extend([filters["date_start"], filters["date_end"]])

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
            SELECT
                COUNT(*),
                COALESCE(SUM(h.duracao_min),0),
                COALESCE(SUM(h.xp_gain),0),
                COALESCE(SUM(h.raw_xp_gain),0),
                COALESCE(SUM(h.supplies),0),
                COALESCE(SUM(h.pagamento),0),
                COALESCE(SUM(h.balance),0)
            FROM Hunts h
            {where_sql}
        """
        
        with closing(self._get_connection()) as conn:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            qtd, total_min, total_xp, total_raw_xp, total_supplies, total_pagto, total_balance = row, 0, 0, 0, 0, 0, 0
            if row:
                qtd, total_min, total_xp, total_raw_xp, total_supplies, total_pagto, total_balance = row

            k_sql = f"""
                SELECT COALESCE(SUM(hm.quantidade),0) as total_kills
                FROM Hunts h LEFT JOIN Hunts_Monstros hm ON hm.hunt_id = h.id
                {where_sql}
            """
            cursor = conn.execute(k_sql, params)
            total_kills = int(cursor.fetchone()[0] or 0)

        return {
            "count": qtd,
            "total_min": total_min,
            "total_xp": total_xp,
            "total_raw_xp": total_raw_xp,
            "total_supplies": total_supplies,
            "total_pagto": total_pagto,
            "total_balance": total_balance,
            "total_kills": total_kills
        }

    def get_monster_aggregates(self, filters: dict) -> List[Tuple[str, int]]:
        where = []
        params = []
        if filters.get("character") and filters["character"] != "Todos":
            where.append("h.personagem = ?")
            params.append(filters["character"])
        
        if filters.get("date_start") and filters.get("date_end"):
            where.append("h.data >= ? AND h.data <= ?")
            params.extend([filters["date_start"], filters["date_end"]])

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        
        sql = f"""
            SELECT hm.criatura, SUM(hm.quantidade) as total
            FROM Hunts_Monstros hm
            JOIN Hunts h ON h.id = hm.hunt_id
            {where_sql}
            GROUP BY hm.criatura
            ORDER BY total DESC
        """
        
        with closing(self._get_connection()) as conn:
            cursor = conn.execute(sql, params)
            return [(row["criatura"], row["total"]) for row in cursor.fetchall()]

    def get_chart_data(self, filters: dict) -> List[dict]:
        where = []
        params = []
        if filters.get("character") and filters["character"] != "Todos":
            where.append("personagem = ?")
            params.append(filters["character"])
        
        if filters.get("date_start") and filters.get("date_end"):
            where.append("data >= ? AND data <= ?")
            params.extend([filters["date_start"], filters["date_end"]])

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        
        sql = f"""
            SELECT data, hora_inicio, raw_xp_gain, balance, duracao_min
            FROM Hunts
            {where_sql}
            ORDER BY data, hora_inicio
        """
        
        with closing(self._get_connection()) as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def list_characters(self) -> List[str]:
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT nome, is_default FROM Characters ORDER BY nome")
            rows = cursor.fetchall()
        default = [r["nome"] for r in rows if r["is_default"]]
        others = [r["nome"] for r in rows if not r["is_default"]]
        return default + others

    def get_default_character(self) -> str:
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT nome FROM Characters WHERE is_default = 1 LIMIT 1")
            r = cursor.fetchone()
            return r["nome"] if r else ""

    def set_default_character(self, name: str) -> None:
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute("UPDATE Characters SET is_default = 0")
                conn.execute("UPDATE Characters SET is_default = 1 WHERE nome = ?", (name,))

    def add_character(self, name: str) -> None:
        if not name.strip(): return
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute("INSERT OR IGNORE INTO Characters (nome) VALUES (?)", (name.strip(),))

    def delete_character(self, name: str) -> None:
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute("DELETE FROM Characters WHERE nome = ?", (name,))

    def list_locations(self) -> List[str]:
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT nome FROM Locations ORDER BY nome")
            return [r["nome"] for r in cursor.fetchall()]

    def add_location(self, name: str) -> None:
        if not name.strip(): return
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute("INSERT OR IGNORE INTO Locations (nome) VALUES (?)", (name.strip(),))

    def delete_location(self, name: str) -> None:
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute("DELETE FROM Locations WHERE nome = ?", (name,))

    def get_setting(self, key: str) -> Optional[str]:
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT value FROM Settings WHERE key=?", (key,))
            res = cursor.fetchone()
            return res["value"] if res else None

    def set_setting(self, key: str, value: str) -> None:
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO Settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
