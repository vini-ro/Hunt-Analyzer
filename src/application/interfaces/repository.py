from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities import Hunt

class HuntRepository(ABC):
    @abstractmethod
    def save(self, hunt: Hunt) -> int:
        pass

    @abstractmethod
    def get_all(self, filters: dict) -> List[Hunt]:
        pass

    @abstractmethod
    def get_by_id(self, hunt_id: int) -> Optional[Hunt]:
        pass

    @abstractmethod
    def delete_many(self, item_ids: List[int]) -> None:
        pass

    @abstractmethod
    def update(self, hunt: Hunt) -> None:
        pass

    @abstractmethod
    def update_many(self, ids: List[int], updates: dict) -> None:
        pass
    
    @abstractmethod
    def get_analytics(self, filters: dict) -> dict:
        pass

    @abstractmethod
    def get_monster_aggregates(self, filters: dict) -> List[tuple]:
        pass

    @abstractmethod
    def list_characters(self) -> List[str]:
        pass

    @abstractmethod
    def get_default_character(self) -> str:
        pass

    @abstractmethod
    def set_default_character(self, name: str) -> None:
        pass

    @abstractmethod
    def add_character(self, name: str) -> None:
        pass

    @abstractmethod
    def delete_character(self, name: str) -> None:
        pass

    @abstractmethod
    def list_locations(self) -> List[str]:
        pass

    @abstractmethod
    def add_location(self, name: str) -> None:
        pass

    @abstractmethod
    def delete_location(self, name: str) -> None:
        pass

    @abstractmethod
    def get_setting(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def set_setting(self, key: str, value: str) -> None:
        pass
