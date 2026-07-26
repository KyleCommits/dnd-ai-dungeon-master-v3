from src.intent_slots import fill

WEAPONS = ["Longsword", "Dagger", "Shortbow"]
NPCS = ["Mira", "Garrick the Smith"]
SPELLS = ["Fireball", "Cure Wounds"]


def _fill(text, action):
    return fill(text, action, weapon_names=WEAPONS, npc_names=NPCS, spell_names=SPELLS)


def test_attack_on_object_extracts_target():
    s = _fill("i attack the table", "attack")
    assert s.target == "table"
    assert s.resolved is True


def test_attack_on_known_npc_matches_canonical_name():
    s = _fill("i attack mira", "attack")
    assert s.target == "Mira", "should snap to the canonical NPC name"
    assert s.resolved is True


def test_npc_partial_name_matches():
    s = _fill("i attack garrick", "attack")
    assert s.target == "Garrick the Smith"
    assert s.resolved is True


def test_weapon_in_inventory_is_kept():
    s = _fill("i attack the table with my longsword", "attack")
    assert s.weapon_hint == "Longsword"
    assert s.method == "weapon"
    assert s.resolved is True


def test_weapon_not_in_inventory_is_dropped():
    s = _fill("i attack the table with my warhammer", "attack")
    assert s.weapon_hint is None, "warhammer is not in inventory"
    assert s.resolved is True, "target still resolves; weapon choice happens downstream"


def test_unarmed_is_recognized_without_inventory():
    s = _fill("i punch the guard", "attack")
    assert s.method == "unarmed"
    assert s.weapon_hint is None
    assert s.resolved is True


def test_attack_without_any_target_does_not_resolve():
    s = _fill("i attack", "attack")
    assert s.target is None
    assert s.resolved is False


def test_pronoun_target_does_not_resolve():
    s = _fill("i attack him", "attack")
    assert s.resolved is False, "pronouns are not world entities"


def test_cast_extracts_known_spell():
    s = _fill("i cast fireball", "cast")
    assert s.spell_name == "Fireball"
    assert s.resolved is True


def test_cast_unknown_spell_does_not_resolve():
    s = _fill("i cast meteor swarm", "cast")
    assert s.resolved is False


def test_cast_resolves_when_no_spell_list_is_supplied():
    """No spellbook on hand means defer to the engine, not silently swallow the cast."""
    s = fill("i cast fireball", "cast", weapon_names=WEAPONS, npc_names=NPCS)
    assert s.spell_name == "Fireball"
    assert s.resolved is True


def test_cast_with_empty_spell_list_does_not_resolve():
    """An empty list is a real answer: this character knows no spells."""
    s = fill("i cast fireball", "cast", weapon_names=WEAPONS, npc_names=NPCS,
             spell_names=[])
    assert s.resolved is False


def test_non_mechanics_action_always_resolves():
    s = _fill("hello there", "speak")
    assert s.resolved is True
    assert s.target is None
