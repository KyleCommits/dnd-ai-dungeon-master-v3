# d&d ai dungeon master

so this is my attempt at building an ai dungeon master that can actually run a proper d&d campaign. not just some basic chatbot that pretends to know the rules, but something that can handle character sheets, spell casting, combat, and all the mechanical stuff while still being creative with the story.

## what this thing does

- runs full d&d 5e campaigns with proper rule enforcement
- generates detailed campaigns (like 7000+ lines of content)
- handles character creation, leveling, spell management, animal companions
- ai can directly modify your hp, apply conditions, roll dice, consume spell slots
- tracks campaign state, npcs, plot threads, all that dm stuff
- has a decent web interface that doesnt look like garbage
- remembers what happened in previous sessions via summaries

## tech stack

honestly this got way more complicated than i originally planned:

**frontend**: react + typescript with websockets for real-time chat
**backend**: fastapi with async everything
**database**: postgresql for main stuff, sqlite for spells
**ai models**: google gemini 2.5 flash-lite (primary), local transformers (backup)
**d&d data**: official srd api integration for spells, custom campaign system

## getting started

you'll need python 3.11 and a gemini api key. also postgres running locally.

```bash
# clone and setup
git clone [your-repo-url]
cd dungeon_master_discord_bot_v3

# virtual env (i use llama_env_311 but whatever)
python -m venv llama_env_311
llama_env_311\Scripts\activate  # windows
source llama_env_311/bin/activate  # linux/mac

# install stuff
pip install -r requirements.txt

# database setup
# create a postgres db called 'dnd_bot_v3'
# run the sql files in queries/ folder

# config
cp src/config_template.py src/config.py
# edit config.py with your api keys and database settings

# start the system
python start_web_system.py
```

then go to http://localhost:3000 and http://localhost:8080 should be your api.

## project structure

```
src/                    # main backend code
  dynamic_dm.py         # the ai dm brain
  game_actions.py       # ai function calling for mechanics
  character_manager.py  # handles character sheets
  spell_integration.py  # all 319 d&d spells
  campaign_state_manager.py  # tracks story progression

web/                    # react frontend
  src/components/       # ui components

dnd_src_material/       # campaign content
  custom_campaigns/     # generated campaign files

tests/                  # test scripts
```

## how it works

the core idea is that gemini can actually execute game mechanics instead of just describing them. so when you take damage, the ai calls `modify_hp(character_id, -10, "goblin sword")` and your hp actually goes down. same with spell casting, conditions, dice rolls, etc.

campaigns are generated using a multi-stage pipeline: xai generates the outline, gemini fleshes it out, then local llm adds the final details. results in campaigns that are actually playable and not just random nonsense.

the character system handles full d&d 5e mechanics including spell slots, prepared spells, animal companions, all ability scores, etc. spell system has all 319 srd spells with proper casting mechanics.

## current status

this is an ongoing project that i work on when i have time. definitely still a work in progress but the core systems are solid:

- spell system: complete
- character management: complete
- ai function calling: complete
- campaign generation: complete
- session management: complete
- web interface: functional but could be prettier

## known issues

- sometimes the ai gets confused about whose turn it is
- spell damage calculation could be more automated
- equipment system exists but isnt fully integrated
- no multiplayer support yet (single player only)
- combat positioning is purely narrative (no battle map)

## testing

there are test scripts in the tests/ folder for validating different systems:

```bash
python tests/test_ai_function_calling.py    # test ai mechanics
python tests/test_session_summaries.py      # test session storage
python tests/test_spells.py                 # test spell system
```

## contributing

if you want to mess with this feel free to fork it. the code could definitely use some cleanup and there are tons of features that could be added. just try to follow the existing patterns and dont break the ai function calling system cause that took forever to get working.

## license

mit or whatever. just dont sell it as your own thing.

---

built because i wanted to play d&d but scheduling with humans is impossible.