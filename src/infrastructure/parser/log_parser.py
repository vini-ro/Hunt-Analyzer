import re
from typing import Any, Dict, List, Tuple

class LogParser:
    @staticmethod
    def safe_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            try:
                return int(float(value))
            except Exception:
                return 0

    @staticmethod
    def _search(text: str, pattern: str, flags=0, default="0") -> str:
        m = re.search(pattern, text, flags)
        if not m:
            return default
        val = m.group(1)
        val = val.replace(",", "").replace("−", "-").replace("–", "-").strip()
        return val

    def extract_monsters(self, text: str) -> List[Tuple[str, int]]:
        m = re.search(r"Killed Monsters:\s*(.*?)(?:Looted Items:|$)", text, re.DOTALL | re.IGNORECASE)
        trecho = m.group(1) if m else ""
        padrao = re.compile(r'^\s*(\d+)\s*x\s+(.+?)\s*$', re.MULTILINE | re.IGNORECASE)
        monstros = padrao.findall(trecho)
        return [(nome.strip(), self.safe_int(qtd)) for qtd, nome in monstros]

    def parse_hunt_data(self, text: str) -> Dict[str, Any]:
        duracao_min = 0
        m = re.search(r"Session:\s+(\d{2}):(\d{2})h", text)
        if m:
            try:
                h, mm = int(m.group(1)), int(m.group(2))
                duracao_min = h * 60 + mm
            except Exception:
                duracao_min = 0

        raw_xp = self.safe_int(self._search(text, r"Raw XP Gain:\s*([\d,.]+)"))
        xp = self.safe_int(self._search(text, r"^XP Gain:\s*([\d,.]+)", flags=re.MULTILINE))
        loot = self.safe_int(self._search(text, r"Loot:\s*([-\d,−–]+)"))
        supplies = self.safe_int(self._search(text, r"Supplies:\s*([-\d,−–]+)"))
        balance = self.safe_int(self._search(text, r"Balance:\s*([-\d,−–]+)"))
        damage = self.safe_int(self._search(text, r"Damage:\s*([-\d,−–]+)"))
        healing = self.safe_int(self._search(text, r"Healing:\s*([-\d,−–]+)"))

        data_inicio = self._search(text, r"From\s+(\d{4}-\d{2}-\d{2}),", default="")
        hora_inicio = self._search(text, r"From\s+\d{4}-\d{2}-\d{2},\s+(\d{2}:\d{2}:\d{2})", default="")
        hora_fim = self._search(text, r"to\s+\d{4}-\d{2}-\d{2},\s+(\d{2}:\d{2}:\d{2})", default="")

        return {
            "duracao_min": duracao_min,
            "raw_xp_gain": raw_xp,
            "xp_gain": xp,
            "loot": loot,
            "supplies": supplies,
            "balance": balance,
            "damage": damage,
            "healing": healing,
            "data_inicio": data_inicio,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
        }
