# D&D AI Dungeon Master

An intelligent AI Dungeon Master system that runs complete D&D 5e campaigns with full mechanical support. Built to handle everything from character creation and spell casting to combat resolution and narrative storytelling.

## Features

- **Complete D&D 5e Rules Engine**: Proper enforcement of character creation, spell slots, conditions, and combat mechanics
- **Dynamic Campaign Generation**: Creates detailed, playable campaigns with 7000+ lines of content using multi-stage AI pipeline
- **Character Management**: Full character sheet support including leveling, spell preparation, animal companions, and stat tracking
- **AI-Driven Game Mechanics**: Gemini directly executes game actions (HP modification, spell casting, dice rolling, condition application)
- **Campaign State Persistence**: Tracks NPCs, plot threads, relationships, and session history with automatic summaries
- **Modern Web Interface**: Real-time React frontend with WebSocket-powered chat and professional D&D aesthetic
- **Session Memory System**: Maintains continuity between sessions through conversation history and narrative summaries

## Technology Stack

**Frontend**: React + TypeScript with WebSocket real-time communication
**Backend**: FastAPI with async request handling
**Databases**: PostgreSQL (primary), SQLite (spell data)
**AI Models**: Google Gemini 2.5 Flash-Lite (primary), Local Transformers (fallback)
**D&D Data**: Official SRD API integration + custom campaign system

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL database server
- Google Gemini API key

### Setup

```bash
# Clone the repository
git clone [your-repo-url]
cd dungeon_master_discord_bot_v3

# Create virtual environment
python -m venv llama_env_311
llama_env_311\Scripts\activate  # Windows
source llama_env_311/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Database setup
# 1. Create PostgreSQL database: 'dnd_bot_v3'
# 2. Run SQL initialization scripts from queries/ folder

# Configuration
cp src/config_template.py src/config.py
# Edit src/config.py with your API keys and database credentials

# Start the system
python start_web_system.py
```

Access the application:
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8080

## Project Structure

```
src/                           # Core backend logic
  dynamic_dm.py                # AI Dungeon Master brain
  game_actions.py              # AI function calling for game mechanics
  character_manager.py         # Character sheet management
  spell_integration.py         # 319 D&D 5e SRD spells
  campaign_state_manager.py    # Story and NPC tracking

web/                           # React frontend
  src/components/              # UI components

dnd_src_material/              # Campaign content
  custom_campaigns/            # Generated campaign files

tests/                         # Test scripts
```

## How It Works

### AI Function Calling System
Instead of just narrating events, the AI directly executes game mechanics. When you take damage, the system calls `modify_hp(character_id, -10, "goblin sword")` to update your actual HP. This applies to spell slots, conditions, dice rolls, and all other mechanical actions.

### Campaign Generation Pipeline
1. **XAI**: Generates campaign outline and structure
2. **Gemini**: Expands outline into detailed narrative content
3. **Local LLM**: Adds final polish and mechanical details

Result: Fully playable campaigns with coherent plots, balanced encounters, and proper pacing.

### Character System
Full D&D 5e implementation including:
- All core classes and subclasses
- Spell slot progression and preparation mechanics
- Animal companion system (Beast Master Rangers)
- Ability scores, proficiencies, and skill checks
- Complete integration with AI narrative system

## Current Status

**Completed Systems**:
- Character management and creation
- Spell system (all 319 SRD spells)
- AI function calling for game mechanics
- Campaign generation pipeline
- Session persistence and summaries
- Web interface with real-time chat
- Dice rolling system with advantage/disadvantage

**In Progress**:
- Equipment and inventory integration
- Advanced combat positioning mechanics
- Multiplayer session support

## Known Limitations

- Single-player only (no multi-user sessions yet)
- Combat positioning is narrative-based (no battle map grid)
- Spell damage calculation requires manual confirmation in some cases
- Equipment system exists but not fully integrated with character stats
- Turn order tracking can occasionally need clarification

## Testing

Run validation scripts to test system components:

```bash
python tests/test_ai_function_calling.py    # AI mechanics validation
python tests/test_session_summaries.py      # Session storage tests
python tests/test_spells.py                 # Spell system validation
```

## Contributing

Contributions are welcome. When contributing:
- Follow existing code patterns and architecture
- Maintain compatibility with the AI function calling system
- Add tests for new features
- Update documentation as needed

## License

MIT License - Free to use and modify. Please provide attribution if you use this project as a base for your own work.

---

*Built to solve the eternal problem of D&D scheduling conflicts.*
