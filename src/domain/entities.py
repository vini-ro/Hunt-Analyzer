from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Monster:
    name: str
    amount: int
    hunt_id: Optional[int] = None

@dataclass
class Hunt:
    id: Optional[int]
    character: str
    location: str
    date: str  # YYYY-MM-DD
    start_time: str
    end_time: str
    duration_min: int
    raw_xp_gain: int
    xp_gain: int
    loot: int
    supplies: int
    balance: int
    damage: int
    healing: int
    raw_text: str
    monsters: List[Monster]
    
    @property
    def payment(self) -> int:
        # Business logic: Payment is equal to negative balance (waste)
        return abs(self.balance) if self.balance < 0 else 0
