# src/ascii_ui/commands.py - slash command router for ASCII terminal
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.animal_companion_manager import AnimalCompanionManager
from src.campaign_state_manager import campaign_state_manager
from src.character_manager import character_manager
from src.character_models import NPC
from src.database import (
    create_new_chat_session,
    get_campaign_by_name,
    get_chat_session_with_campaign,
    get_full_conversation_history,
    get_or_create_chat_session,
    add_session_summary,
)
from src.dice_roller import dice_roller
from src.enhanced_spell_system import enhanced_spell_manager

from .render_character import render_character_list, render_character_sheet
from .render_companion import pick_primary_companion, render_companion, render_companion_list
from .render_npc import render_npc, render_npc_list
from .render_spell import render_spell, render_spell_list
from .render_status import render_help, render_status


@dataclass
class TerminalCommandResult:
    ok: bool = True
    log_lines: List[str] = field(default_factory=list)
    detail_frame: Optional[str] = None


def _result(
    *log_lines: str,
    detail_frame: Optional[str] = None,
    ok: bool = True,
) -> TerminalCommandResult:
    return TerminalCommandResult(ok=ok, log_lines=list(log_lines), detail_frame=detail_frame)


async def handle_terminal_command(
    command: str,
    db: AsyncSession,
    user_id: str = "player1",
    session_id: Optional[str] = None,
    connection_manager: Any = None,
) -> TerminalCommandResult:
    raw = (command or "").strip()
    if not raw:
        return _result("ERROR: empty command", ok=False)
    if not raw.startswith("/"):
        return _result("ERROR: commands must start with / (chat goes over WebSocket)", ok=False)

    parts = raw[1:].split()
    if not parts:
        return _result("ERROR: empty command", ok=False)

    verb = parts[0].lower()
    args = parts[1:]

    handlers = {
        "help": _cmd_help,
        "?": _cmd_help,
        "status": _cmd_status,
        "campaigns": _cmd_campaigns,
        "load": _cmd_load,
        "session": _cmd_session,
        "chars": _cmd_chars,
        "characters": _cmd_chars,
        "active": _cmd_active,
        "sheet": _cmd_sheet,
        "companion": _cmd_companion,
        "npcs": _cmd_npcs,
        "npc": _cmd_npc,
        "spells": _cmd_spells,
        "cast": _cmd_cast,
        "prepare": _cmd_prepare,
        "unprepare": _cmd_unprepare,
        "rest": _cmd_rest,
        "roll": _cmd_roll,
    }

    handler = handlers.get(verb)
    if not handler:
        return _result(f"ERROR: unknown command /{verb}. Try /help", ok=False)

    return await handler(args, db=db, user_id=user_id, session_id=session_id, connection_manager=connection_manager)


async def _cmd_help(args, **kwargs) -> TerminalCommandResult:
    return _result("Help loaded.", detail_frame=render_help())


async def _resolve_campaign(db: AsyncSession):
    state = campaign_state_manager.current_state
    if not state or not state.campaign_name:
        return None, None
    campaign = await get_campaign_by_name(db, state.campaign_name)
    return state, campaign


async def _active_character(db: AsyncSession, user_id: str):
    state, campaign = await _resolve_campaign(db)
    if not campaign:
        return None, None, None
    character = await character_manager.get_active_character(db, user_id, campaign.id)
    return state, campaign, character


def _character_to_sheet_dict(character, spell_slots=None) -> Dict[str, Any]:
    abilities = character.abilities[0] if character.abilities else None
    conditions = []
    raw_conditions = getattr(character, "conditions_json", None) or "[]"
    try:
        conditions = json.loads(raw_conditions) if isinstance(raw_conditions, str) else raw_conditions
    except Exception:
        conditions = []

    data = {
        "id": character.id,
        "name": character.name,
        "race": character.race,
        "class_name": character.class_name,
        "level": character.level,
        "background": character.background,
        "current_hp": character.current_hp,
        "max_hp": character.max_hp,
        "armor_class": character.armor_class,
        "speed": character.speed,
        "proficiency_bonus": character.proficiency_bonus,
        "is_alive": character.is_alive,
        "is_unconscious": character.is_unconscious,
        "conditions": conditions,
        "abilities": {
            "strength": abilities.strength if abilities else 10,
            "dexterity": abilities.dexterity if abilities else 10,
            "constitution": abilities.constitution if abilities else 10,
            "intelligence": abilities.intelligence if abilities else 10,
            "wisdom": abilities.wisdom if abilities else 10,
            "charisma": abilities.charisma if abilities else 10,
        },
        "skills": [
            {
                "name": skill.skill_name,
                "proficient": skill.proficient,
                "expertise": skill.expertise,
            }
            for skill in (character.skills or [])
        ],
        "equipment": [
            {
                "name": item.item_name,
                "quantity": item.quantity,
                "equipped": item.equipped,
            }
            for item in (character.equipment or [])
        ],
    }
    if spell_slots is not None:
        data["spell_slots"] = spell_slots
    return data


async def _cmd_status(args, db: AsyncSession, user_id: str, session_id=None, **kwargs) -> TerminalCommandResult:
    state, campaign, character = await _active_character(db, user_id)
    campaign_info = {}
    if state:
        campaign_info = {
            "name": state.campaign_name,
            "act": state.current_act,
            "location": state.location,
            "session": state.session_count,
        }
    active = None
    if character:
        active = {
            "id": character.id,
            "name": character.name,
            "current_hp": character.current_hp,
            "max_hp": character.max_hp,
            "armor_class": character.armor_class,
        }
    frame = render_status(campaign_info, active, session_id=session_id)
    return _result("Status.", detail_frame=frame)


async def _cmd_campaigns(args, **kwargs) -> TerminalCommandResult:
    campaigns_dir = "dnd_src_material/custom_campaigns"
    names = []
    if os.path.exists(campaigns_dir):
        for file in os.listdir(campaigns_dir):
            if file.endswith(".md"):
                names.append(file[:-3])
    if not names:
        return _result("No campaigns found.", detail_frame=render_status({"name": "(none)"}))
    lines = [f"- {n}" for n in sorted(names)]
    from .frames import box

    return _result(f"{len(names)} campaign(s).", detail_frame=box(lines, title="Campaigns"))


async def _cmd_load(args, db: AsyncSession, connection_manager=None, **kwargs) -> TerminalCommandResult:
    if not args:
        return _result("ERROR: usage /load <campaign_name>", ok=False)
    name = " ".join(args)
    success = await campaign_state_manager.load_campaign(name)
    if not success:
        return _result(f"ERROR: failed to load '{name}'", ok=False)
    if connection_manager:
        msg = {
            "type": "system",
            "message": f"Campaign loaded: {name}",
            "user_id": "system",
        }
        try:
            await connection_manager.broadcast(json.dumps(msg))
        except Exception:
            pass
    return await _cmd_status([], db=db, user_id=kwargs.get("user_id", "player1"), session_id=kwargs.get("session_id"))


async def _cmd_session(args, db: AsyncSession, user_id: str, session_id=None, connection_manager=None, **kwargs) -> TerminalCommandResult:
    if not args:
        return _result("ERROR: usage /session start|end", ok=False)
    action = args[0].lower()
    state, campaign = await _resolve_campaign(db)
    if not campaign:
        return _result("ERROR: no campaign loaded", ok=False)

    if action in ("start", "new"):
        new_session = await create_new_chat_session(db, user_id, campaign.id)
        if connection_manager and hasattr(connection_manager, "set_user_session"):
            connection_manager.set_user_session(user_id, new_session.session_id)
            try:
                await connection_manager.broadcast(
                    json.dumps(
                        {
                            "type": "session_change",
                            "message": "New session started",
                            "session_id": new_session.session_id,
                        }
                    )
                )
            except Exception:
                pass
        return _result(
            f"SUCCESS: new session {new_session.session_id}",
            detail_frame=render_status(
                {
                    "name": state.campaign_name if state else None,
                    "act": state.current_act if state else "-",
                    "location": state.location if state else "-",
                    "session": state.session_count if state else "-",
                },
                session_id=new_session.session_id,
            ),
        )

    if action == "end":
        sid = session_id or user_id
        chat_session = await get_chat_session_with_campaign(db, sid)
        if not chat_session:
            chat_session = await get_or_create_chat_session(db, sid, campaign.id)
        history = await get_full_conversation_history(db, chat_session.session_id)
        summary_text = ""
        if history:
            formatted = "\n".join([f"{m.message_type}: {m.content}" for m in history])
            try:
                from src.llm_manager import llm_manager

                summary_text = await llm_manager.generate(
                    f"Summarize this D&D session briefly:\n{formatted[:8000]}"
                )
            except Exception:
                summary_text = "(summary unavailable)"
            try:
                await add_session_summary(db, campaign.id, summary_text or "(empty session)")
            except Exception:
                pass
        return _result(
            "SUCCESS: session ended.",
            detail_frame=render_status(
                {"name": state.campaign_name if state else None},
                session_id=chat_session.session_id,
                extra={"Summary": (summary_text or "(empty)")[:200]},
            ),
        )

    return _result("ERROR: usage /session start|end", ok=False)


async def _cmd_chars(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    state, campaign = await _resolve_campaign(db)
    if not campaign:
        return _result("ERROR: no campaign loaded", ok=False)
    characters = await character_manager.get_user_characters(db, user_id, campaign.id)
    active = await character_manager.get_active_character(db, user_id, campaign.id)
    char_dicts = [
        {
            "id": c.id,
            "name": c.name,
            "race": c.race,
            "class_name": c.class_name,
            "level": c.level,
            "current_hp": c.current_hp,
            "max_hp": c.max_hp,
        }
        for c in characters
    ]
    frame = render_character_list(char_dicts, active_id=active.id if active else None)
    return _result(f"{len(char_dicts)} character(s).", detail_frame=frame)


async def _cmd_active(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    if not args:
        return _result("ERROR: usage /active <id|name>", ok=False)
    state, campaign = await _resolve_campaign(db)
    if not campaign:
        return _result("ERROR: no campaign loaded", ok=False)
    characters = await character_manager.get_user_characters(db, user_id, campaign.id)
    target = " ".join(args)
    chosen = None
    if target.isdigit():
        cid = int(target)
        chosen = next((c for c in characters if c.id == cid), None)
    else:
        lowered = target.lower()
        chosen = next((c for c in characters if c.name.lower() == lowered), None)
        if not chosen:
            chosen = next((c for c in characters if lowered in c.name.lower()), None)
    if not chosen:
        return _result(f"ERROR: character '{target}' not found", ok=False)
    await character_manager.set_active_character(db, user_id, campaign.id, chosen.id)
    full = await character_manager.get_character_full(db, chosen.id)
    return _result(
        f"SUCCESS: active character is {chosen.name}",
        detail_frame=render_character_sheet(_character_to_sheet_dict(full)),
    )


async def _cmd_sheet(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    state, campaign, character = await _active_character(db, user_id)
    if not character:
        return _result("ERROR: no active character (use /chars and /active)", ok=False)
    full = await character_manager.get_character_full(db, character.id)
    spell_slots = None
    try:
        spell_data = await character_manager.get_character_spells(db, character.id)
        spell_slots = spell_data.get("spell_slots")
    except Exception:
        pass
    return _result(
        f"Sheet: {full.name}",
        detail_frame=render_character_sheet(_character_to_sheet_dict(full, spell_slots=spell_slots)),
    )


async def _cmd_companion(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    state, campaign, character = await _active_character(db, user_id)
    if not character:
        return _result("ERROR: no active character", ok=False)

    companion_manager = AnimalCompanionManager(db)
    companions = await companion_manager.get_character_companions(character.id, include_dead=True)
    if isinstance(companions, dict):
        return _result(f"ERROR: {companions.get('error', 'companion lookup failed')}", ok=False)

    if not args:
        primary = pick_primary_companion(companions)
        if not primary:
            return _result("No companions.", detail_frame=render_companion_list([]))
        detail = await companion_manager.get_companion_full_stats(primary["id"])
        if "error" in detail:
            return _result(f"ERROR: {detail['error']}", detail_frame=render_companion_list(companions), ok=False)
        return _result(
            f"Companion: {detail.get('name')}",
            detail_frame=render_companion(detail),
        )

    action = args[0].lower()
    primary = pick_primary_companion(companions)
    if not primary:
        return _result("ERROR: no companion", ok=False)

    if action == "list":
        return _result("Companions.", detail_frame=render_companion_list(companions))

    if action in ("heal", "damage") and len(args) >= 2:
        try:
            amount = int(args[1])
        except ValueError:
            return _result("ERROR: amount must be an integer", ok=False)
        if action == "heal":
            result = await companion_manager.heal_companion(primary["id"], amount)
        else:
            result = await companion_manager.damage_companion(primary["id"], amount)
        if not result.get("success"):
            return _result(f"ERROR: {result.get('error', 'failed')}", ok=False)
        detail = await companion_manager.get_companion_full_stats(primary["id"])
        return _result(
            f"SUCCESS: companion {action} {amount}",
            detail_frame=render_companion(detail),
        )

    return _result("ERROR: usage /companion [list|heal N|damage N]", ok=False)


def _npc_to_dict(npc: NPC) -> Dict[str, Any]:
    abilities = npc.abilities[0] if npc.abilities else None
    return {
        "id": npc.id,
        "name": npc.name,
        "race": npc.race,
        "class_name": npc.class_name,
        "level": npc.level,
        "npc_type": npc.npc_type,
        "current_hp": npc.current_hp,
        "max_hp": npc.max_hp,
        "armor_class": npc.armor_class,
        "speed": npc.speed,
        "is_alive": npc.is_alive,
        "is_active": npc.is_active,
        "abilities": {
            "strength": abilities.strength if abilities else 10,
            "dexterity": abilities.dexterity if abilities else 10,
            "constitution": abilities.constitution if abilities else 10,
            "intelligence": abilities.intelligence if abilities else 10,
            "wisdom": abilities.wisdom if abilities else 10,
            "charisma": abilities.charisma if abilities else 10,
        }
        if abilities
        else {},
    }


async def _list_campaign_npcs(db: AsyncSession, campaign_id: int) -> List[Dict[str, Any]]:
    result = await db.execute(select(NPC).where(NPC.campaign_id == campaign_id))
    npcs = result.scalars().all()
    return [_npc_to_dict(n) for n in npcs]


async def _cmd_npcs(args, db: AsyncSession, **kwargs) -> TerminalCommandResult:
    state, campaign = await _resolve_campaign(db)
    rows: List[Dict[str, Any]] = []
    if campaign:
        rows.extend(await _list_campaign_npcs(db, campaign.id))
    # also surface campaign-state relationship names if DB empty
    if state and getattr(state, "npc_relationships", None):
        known = {r["name"].lower() for r in rows}
        for name, info in state.npc_relationships.items():
            if name.lower() in known:
                continue
            if isinstance(info, dict):
                rows.append(
                    {
                        "id": "-",
                        "name": name,
                        "npc_type": info.get("attitude", info.get("type", "unknown")),
                        "current_hp": info.get("current_hp", "?"),
                        "max_hp": info.get("max_hp", "?"),
                        "is_alive": True,
                        "relationship": info.get("relationship") or info.get("notes"),
                    }
                )
            else:
                rows.append({"id": "-", "name": name, "npc_type": str(info), "is_alive": True})
    return _result(f"{len(rows)} NPC(s).", detail_frame=render_npc_list(rows))


async def _cmd_npc(args, db: AsyncSession, **kwargs) -> TerminalCommandResult:
    if not args:
        return await _cmd_npcs([], db=db, **kwargs)
    state, campaign = await _resolve_campaign(db)
    target = " ".join(args)
    rows = await _list_campaign_npcs(db, campaign.id) if campaign else []

    chosen = None
    if target.isdigit() and campaign:
        result = await db.execute(
            select(NPC).where(NPC.id == int(target), NPC.campaign_id == campaign.id)
        )
        npc = result.scalar_one_or_none()
        if npc:
            # ensure abilities loaded
            await db.refresh(npc, ["abilities"])
            chosen = _npc_to_dict(npc)
    if not chosen:
        lowered = target.lower()
        chosen = next((n for n in rows if str(n.get("name", "")).lower() == lowered), None)
        if not chosen:
            chosen = next((n for n in rows if lowered in str(n.get("name", "")).lower()), None)

    if not chosen and state and getattr(state, "npc_relationships", None):
        for name, info in state.npc_relationships.items():
            if target.lower() in name.lower():
                if isinstance(info, dict):
                    chosen = {"name": name, **info, "npc_type": info.get("attitude", "unknown")}
                else:
                    chosen = {"name": name, "npc_type": str(info)}
                break

    if not chosen:
        return _result(f"ERROR: NPC '{target}' not found", ok=False)
    return _result(f"NPC: {chosen.get('name')}", detail_frame=render_npc(chosen))


def _spell_obj_to_dict(spell) -> Dict[str, Any]:
    if isinstance(spell, dict):
        return spell
    data = {
        "name": getattr(spell, "name", str(spell)),
        "level": getattr(spell, "level", 0),
        "school": getattr(spell, "school", ""),
        "casting_time": getattr(spell, "casting_time", ""),
        "range": getattr(spell, "range", ""),
        "components": getattr(spell, "components", ""),
        "duration": getattr(spell, "duration", ""),
        "description": getattr(spell, "description", ""),
        "ritual": getattr(spell, "ritual", False),
        "concentration": getattr(spell, "concentration", False),
    }
    damage = getattr(spell, "damage", None)
    if damage:
        data["damage"] = getattr(damage, "damage_type", str(damage))
    return data


async def _cmd_spells(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    enhanced_spell_manager.initialize()
    query = " ".join(args).strip() if args else ""

    # If query looks like a single spell name with no active char needed, try detail
    if query and len(args) == 1:
        spell = enhanced_spell_manager.get_spell(query)
        if spell:
            return _result(f"Spell: {spell.name}", detail_frame=render_spell(_spell_obj_to_dict(spell)))

    state, campaign, character = await _active_character(db, user_id)
    if character and not query:
        spell_data = await character_manager.get_character_spells(db, character.id)
        spells: List[Dict[str, Any]] = []
        for level_str, level_spells in (spell_data.get("spells_by_level") or {}).items():
            for entry in level_spells:
                spell_obj = entry.get("spell")
                d = _spell_obj_to_dict(spell_obj) if spell_obj else {"name": entry.get("name", "?")}
                d["level"] = int(level_str)
                d["is_prepared"] = entry.get("is_prepared", False)
                d["is_known"] = entry.get("is_known", False)
                spells.append(d)
        spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))
        return _result(
            f"{len(spells)} spell(s) for {character.name}",
            detail_frame=render_spell_list(
                f"Spells: {character.name}",
                spells,
                slots=spell_data.get("spell_slots"),
            ),
        )

    if query:
        results = enhanced_spell_manager.search_spells(name_contains=query)
        spell_dicts = [_spell_obj_to_dict(s) for s in (results or [])[:40]]
        if len(spell_dicts) == 1:
            return _result(
                f"Spell: {spell_dicts[0].get('name')}",
                detail_frame=render_spell(spell_dicts[0]),
            )
        return _result(
            f"{len(spell_dicts)} match(es) for '{query}'",
            detail_frame=render_spell_list(f"Search: {query}", spell_dicts),
        )

    return _result("ERROR: no active character and no query. Use /spells <name>", ok=False)


async def _cmd_cast(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    if not args:
        return _result("ERROR: usage /cast <spell name> [slot_level]", ok=False)
    state, campaign, character = await _active_character(db, user_id)
    if not character:
        return _result("ERROR: no active character", ok=False)

    slot_level = None
    name_parts = list(args)
    if name_parts and name_parts[-1].isdigit():
        slot_level = int(name_parts[-1])
        name_parts = name_parts[:-1]
    spell_name = " ".join(name_parts)
    if not spell_name:
        return _result("ERROR: usage /cast <spell name> [slot_level]", ok=False)

    enhanced_spell_manager.initialize()
    if slot_level is None:
        spell = enhanced_spell_manager.get_spell(spell_name)
        slot_level = spell.level if spell else 1
        if slot_level == 0:
            slot_level = 0

    result = await character_manager.cast_spell(db, character.id, spell_name, slot_level)
    if not result.get("success"):
        return _result(f"ERROR: {result.get('error', 'cast failed')}", ok=False)

    spell = result.get("spell")
    detail = render_spell(_spell_obj_to_dict(spell)) if spell else None
    dmg = ""
    effects = result.get("spell_effects") or {}
    if "damage" in effects and effects["damage"].get("dice"):
        roll = dice_roller.parse_dice_notation(effects["damage"]["dice"])
        dmg = f" Damage: {roll.total} {effects['damage'].get('type', '')}"
    return _result(
        f"SUCCESS: cast {getattr(spell, 'name', spell_name)} (slot {result.get('slot_level_used', slot_level)}).{dmg}",
        detail_frame=detail,
    )


async def _cmd_prepare(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    return await _prepare_toggle(args, db, user_id, prepare=True)


async def _cmd_unprepare(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    return await _prepare_toggle(args, db, user_id, prepare=False)


async def _prepare_toggle(args, db, user_id, prepare: bool) -> TerminalCommandResult:
    if not args:
        return _result("ERROR: usage /prepare <spell name>", ok=False)
    state, campaign, character = await _active_character(db, user_id)
    if not character:
        return _result("ERROR: no active character", ok=False)
    spell_name = " ".join(args)
    result = await character_manager.prepare_spell(db, character.id, spell_name, prepare)
    if not result.get("success"):
        return _result(f"ERROR: {result.get('error', 'failed')}", ok=False)
    # refresh spell list frame
    return await _cmd_spells([], db=db, user_id=user_id)


async def _cmd_rest(args, db: AsyncSession, user_id: str, **kwargs) -> TerminalCommandResult:
    if not args or args[0].lower() not in ("short", "long"):
        return _result("ERROR: usage /rest short|long", ok=False)
    state, campaign, character = await _active_character(db, user_id)
    if not character:
        return _result("ERROR: no active character", ok=False)
    rest_type = args[0].lower()
    result = await character_manager.character_rest(db, character.id, rest_type)
    if not result.get("success"):
        return _result(f"ERROR: {result.get('error', 'rest failed')}", ok=False)
    full = await character_manager.get_character_full(db, character.id)
    return _result(
        f"SUCCESS: {rest_type} rest complete.",
        detail_frame=render_character_sheet(_character_to_sheet_dict(full)),
    )


async def _cmd_roll(args, **kwargs) -> TerminalCommandResult:
    if not args:
        return _result("ERROR: usage /roll <NdM[+/-K]>  e.g. /roll 2d6+3", ok=False)
    notation = "".join(args)
    try:
        result = dice_roller.parse_dice_notation(notation)
    except Exception as e:
        return _result(f"ERROR: {e}", ok=False)
    from .frames import box

    rows = [
        f"Notation: {result.dice_notation}",
        f"Rolls:    {result.individual_rolls}",
        f"Modifier: {result.modifier}",
        f"Total:    {result.total}",
    ]
    return _result(f"Rolled {notation} = {result.total}", detail_frame=box(rows, title="Dice"))
