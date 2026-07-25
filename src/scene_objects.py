# src/scene_objects.py
"""In-memory scene objects (furniture, doors, etc.) for attack resolution MVP.

Lifespan matches combat encounters: lost on process restart. Persistence later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class SceneObject:
    name: str
    ac: int
    max_hp: int
    current_hp: int
    material: str = "wood"
    destroyed: bool = False

    def apply_damage(self, amount: int) -> int:
        if self.destroyed or amount <= 0:
            return 0
        dealt = min(amount, self.current_hp)
        self.current_hp -= dealt
        if self.current_hp <= 0:
            self.current_hp = 0
            self.destroyed = True
        return dealt


# Default profiles for common improvised targets (not a full PHB catalog).
_OBJECT_PROFILES = {
    "table": {"ac": 15, "hp": 10, "material": "wood"},
    "wooden table": {"ac": 15, "hp": 10, "material": "wood"},
    "chair": {"ac": 13, "hp": 5, "material": "wood"},
    "door": {"ac": 15, "hp": 18, "material": "wood"},
    "wooden door": {"ac": 15, "hp": 18, "material": "wood"},
    "crate": {"ac": 12, "hp": 8, "material": "wood"},
    "barrel": {"ac": 14, "hp": 12, "material": "wood"},
    "window": {"ac": 12, "hp": 4, "material": "glass"},
    "chest": {"ac": 15, "hp": 15, "material": "wood"},
}


def default_profile(name: str) -> Dict:
    key = (name or "object").strip().lower()
    if key in _OBJECT_PROFILES:
        return dict(_OBJECT_PROFILES[key])
    # Heuristic fallback for unknown objects
    return {"ac": 13, "hp": 8, "material": "wood"}


class SceneObjectStore:
    """campaign_key -> location_key -> object_name -> SceneObject"""

    def __init__(self) -> None:
        self._scenes: Dict[str, Dict[str, Dict[str, SceneObject]]] = {}

    def _keys(self, campaign: str, location: str) -> Tuple[str, str]:
        return (campaign or "default").strip().lower(), (location or "here").strip().lower()

    def get_or_create(
        self,
        campaign: str,
        location: str,
        object_name: str,
        profile: Optional[Dict] = None,
    ) -> SceneObject:
        ck, lk = self._keys(campaign, location)
        name = (object_name or "object").strip()
        name_key = name.lower()
        scene = self._scenes.setdefault(ck, {}).setdefault(lk, {})
        if name_key not in scene:
            prof = profile or default_profile(name)
            hp = int(prof.get("hp", 8))
            scene[name_key] = SceneObject(
                name=name,
                ac=int(prof.get("ac", 13)),
                max_hp=hp,
                current_hp=hp,
                material=str(prof.get("material", "wood")),
            )
        return scene[name_key]

    def get(self, campaign: str, location: str, object_name: str) -> Optional[SceneObject]:
        ck, lk = self._keys(campaign, location)
        return self._scenes.get(ck, {}).get(lk, {}).get((object_name or "").strip().lower())

    def clear_campaign(self, campaign: str) -> None:
        ck, _ = self._keys(campaign, "")
        self._scenes.pop(ck, None)


scene_object_store = SceneObjectStore()
