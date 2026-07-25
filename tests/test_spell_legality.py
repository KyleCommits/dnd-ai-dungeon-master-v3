# tests/test_spell_legality.py
"""Spell legality checks on GameActions.consume_spell_slot (no live LLM)."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.mark.asyncio
async def test_fighter_cannot_cast_fireball():
    from src.game_actions import GameActions

    actions = GameActions()
    fake_spell = SimpleNamespace(name="Fireball", level=3)

    with patch("src.enhanced_spell_system.enhanced_spell_manager") as em, patch(
        "src.game_actions.async_session_scope"
    ) as scope:
        em.initialize = MagicMock()
        em.get_spell = MagicMock(return_value=fake_spell)
        em.get_class_spells = MagicMock(return_value=[])
        db = AsyncMock()
        scope.return_value.__aenter__ = AsyncMock(return_value=db)
        scope.return_value.__aexit__ = AsyncMock(return_value=False)

        actions.spell_manager.get_character_spells = AsyncMock(
            return_value={
                "character_id": 1,
                "character_name": "Test Fighter",
                "class_name": "Fighter",
                "is_spellcaster": False,
                "spells_by_level": {},
            }
        )

        result = await actions.consume_spell_slot(
            "1", 3, spell_name="Fireball", reason="illegal"
        )
        assert result.get("success") is False
        assert "cannot cast" in (result.get("error") or result.get("message") or "").lower()
        actions.spell_manager.consume_spell_slot = AsyncMock()
        # Slot must not be consumed on illegal cast — ensure we never got success path
        assert result.get("success") is False


@pytest.mark.asyncio
async def test_wizard_prepared_fireball_passes_validation():
    from src.game_actions import GameActions

    actions = GameActions()
    fake_spell = SimpleNamespace(name="Fireball", level=3)

    with patch("src.enhanced_spell_system.enhanced_spell_manager") as em:
        em.initialize = MagicMock()
        em.get_spell = MagicMock(return_value=fake_spell)
        em.get_class_spells = MagicMock(return_value=[fake_spell])

        actions.spell_manager.get_character_spells = AsyncMock(
            return_value={
                "character_id": 2,
                "character_name": "Test Wizard",
                "class_name": "Wizard",
                "is_spellcaster": True,
                "spells_by_level": {
                    3: [{
                        "spell": fake_spell,
                        "is_known": True,
                        "is_prepared": True,
                    }]
                },
            }
        )
        actions.spell_manager.consume_spell_slot = AsyncMock(
            return_value={"success": True, "message": "consumed level 3 slot"}
        )

        with patch("src.game_actions.async_session_scope") as scope:
            db = AsyncMock()
            scope.return_value.__aenter__ = AsyncMock(return_value=db)
            scope.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await actions.consume_spell_slot(
                "2", 3, spell_name="Fireball"
            )
            assert result.get("success") is True
            actions.spell_manager.consume_spell_slot.assert_awaited()


@pytest.mark.asyncio
async def test_consume_without_spell_name_skips_legality():
    """Legacy / test path: no spell_name means no legality gate."""
    from src.game_actions import GameActions

    actions = GameActions()
    actions.spell_manager.consume_spell_slot = AsyncMock(
        return_value={"success": True, "message": "ok"}
    )
    actions._validate_spell_cast = AsyncMock(
        return_value={"success": False, "error": "should not run"}
    )

    with patch("src.game_actions.async_session_scope") as scope:
        db = AsyncMock()
        scope.return_value.__aenter__ = AsyncMock(return_value=db)
        scope.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await actions.consume_spell_slot("1", 1, reason="test cast")
        assert result.get("success") is True
        actions._validate_spell_cast.assert_not_awaited()
