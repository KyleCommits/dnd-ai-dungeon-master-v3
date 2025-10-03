import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import CampaignGenerator from './components/CampaignGenerator';
import DetailedCharacterCreator from './components/DetailedCharacterCreator';
import CharacterEditor from './components/CharacterEditor';
import LevelUpWizard from './components/LevelUpWizard';
import CompanionSelection from './components/CompanionSelection';
import CompanionCard from './components/CompanionCard';
import SpellManager from './components/SpellManager';

interface Message {
  type: 'user_message' | 'dm_response' | 'system' | 'typing' | 'error';
  user_id: string;
  message: string;
  timestamp: string;
  campaign_state?: {
    location: string;
    act: number;
    session: number;
  };
  typing?: boolean;
}

interface CharacterCreatorFormProps {
  onSubmit: (characterData: any) => void;
  onCancel: () => void;
}

// Quick Spell Panel Component for the right sidebar
interface QuickSpellPanelProps {
  characterId: number;
  onSpellCast?: (result: any) => void;
}

interface QuickSpell {
  name: string;
  level: number;
  school: string;
  is_prepared?: boolean;
  is_known?: boolean;
}

interface QuickSpellData {
  is_spellcaster: boolean;
  spell_slots: number[];
  prepared_spells: QuickSpell[];
  cantrips: QuickSpell[];
}

const QuickSpellPanel: React.FC<QuickSpellPanelProps> = ({ characterId, onSpellCast }) => {
  const [spellData, setSpellData] = useState<QuickSpellData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadQuickSpells();
  }, [characterId]);

  const loadQuickSpells = async () => {
    try {
      setLoading(true);
      console.log(`QuickSpellPanel - Loading spells for character ${characterId}`);
      const response = await fetch(`http://localhost:8080/api/characters/${characterId}/spells/quick`);
      console.log(`QuickSpellPanel - Response status:`, response.status);
      if (response.ok) {
        const data = await response.json();
        console.log(`QuickSpellPanel - API data received:`, data);
        setSpellData(data);
      } else {
        console.error(`QuickSpellPanel - API error:`, response.status, response.statusText);
        const errorText = await response.text();
        console.error(`QuickSpellPanel - Error response:`, errorText);
      }
    } catch (error) {
      console.error('Error loading quick spells:', error);
    } finally {
      setLoading(false);
    }
  };

  const quickCastSpell = async (spellName: string, slotLevel: number = 1) => {
    try {
      const response = await fetch(`http://localhost:8080/api/characters/${characterId}/spells/cast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spell_name: spellName,
          slot_level: slotLevel
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('QuickSpellPanel - API response received:', result);
        if (onSpellCast) {
          console.log('QuickSpellPanel - About to call onSpellCast callback');
          onSpellCast(result);
          console.log('QuickSpellPanel - onSpellCast callback called');
        } else {
          console.log('QuickSpellPanel - No onSpellCast callback provided');
        }
        await loadQuickSpells(); // Refresh spell slots
      } else {
        const error = await response.json();
        console.error(`Failed to cast ${spellName}:`, error.detail);
      }
    } catch (error) {
      console.error('Error casting spell:', error);
    }
  };

  console.log('QuickSpellPanel - loading:', loading, 'spellData:', spellData);

  if (loading) return <div className="spell-section"><h4>Loading Spells...</h4></div>;
  if (!spellData) {
    console.log('QuickSpellPanel - No spell data, returning null');
    return <div className="spell-section"><h4>No spell data</h4></div>;
  }
  if (!spellData.is_spellcaster) {
    console.log('QuickSpellPanel - Not a spellcaster, returning null');
    return <div className="spell-section"><h4>Not a spellcaster</h4></div>;
  }

  const hasSpellSlots = spellData.spell_slots.some(slots => slots > 0);
  const hasCantrips = spellData.cantrips.length > 0;
  const hasPreparedSpells = spellData.prepared_spells.length > 0;

  return (
    <div className="spell-section">
      <h4>Quick Spells</h4>

      {/* Spell Slots Display */}
      {hasSpellSlots && (
        <div className="spell-slots-display">
          <div className="spell-slots-grid">
            {spellData.spell_slots.map((slots, index) => {
              const level = index + 1;
              if (slots > 0) {
                return (
                  <div key={level} className="spell-slot-indicator">
                    L{level}: {slots}
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      )}

      {/* Cantrips */}
      {hasCantrips && (
        <div className="cantrips-section">
          <h5>Cantrips</h5>
          <div className="quick-spell-grid">
            {spellData.cantrips.slice(0, 6).map(spell => (
              <button
                key={spell.name}
                onClick={() => quickCastSpell(spell.name, 1)}
                className="quick-spell-button cantrip"
                title={`${spell.name} (${spell.school})`}
              >
                {spell.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Prepared Spells */}
      {hasPreparedSpells && hasSpellSlots && (
        <div className="prepared-spells-section">
          <h5>Prepared Spells</h5>
          <div className="quick-spell-grid">
            {spellData.prepared_spells.slice(0, 4).map(spell => (
              <button
                key={spell.name}
                onClick={() => quickCastSpell(spell.name, spell.level)}
                className={`quick-spell-button level-${spell.level}`}
                title={`${spell.name} - Level ${spell.level} ${spell.school}`}
                disabled={spell.level > 0 && !spellData.spell_slots.slice(spell.level - 1).some(slots => slots > 0)}
              >
                {spell.name} ({spell.level})
              </button>
            ))}
          </div>
        </div>
      )}

      {!hasCantrips && !hasPreparedSpells && (
        <p className="no-spells">No prepared spells</p>
      )}
    </div>
  );
};

const CharacterCreatorForm: React.FC<CharacterCreatorFormProps> = ({ onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
    race: 'human',
    class_name: 'fighter',
    background: 'folk_hero',
    level: 1,
    abilities: {
      strength: 15,
      dexterity: 14,
      constitution: 13,
      intelligence: 12,
      wisdom: 10,
      charisma: 8
    },
    skills: {
      athletics: false,
      acrobatics: false,
      sleight_of_hand: false,
      stealth: false,
      arcana: false,
      history: false,
      investigation: false,
      nature: false,
      religion: false,
      animal_handling: false,
      insight: false,
      medicine: false,
      perception: false,
      survival: false,
      deception: false,
      intimidation: false,
      performance: false,
      persuasion: false
    },
    saving_throws: {
      strength: false,
      dexterity: false,
      constitution: false,
      intelligence: false,
      wisdom: false,
      charisma: false
    },
    max_hp: 10,
    armor_class: 10,
    speed: 30
  });

  const races = ['human', 'elf', 'dwarf', 'halfling', 'dragonborn', 'gnome', 'half-elf', 'half-orc', 'tiefling'];
  const classes = ['barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk', 'paladin', 'ranger', 'rogue', 'sorcerer', 'warlock', 'wizard'];
  const backgrounds = ['acolyte', 'criminal', 'folk_hero', 'noble', 'sage', 'soldier', 'charlatan', 'entertainer', 'guild_artisan', 'hermit', 'outlander', 'sailor'];

  // D&D 5e race speed mapping
  const raceSpeed = {
    'human': 30, 'elf': 30, 'half-elf': 30, 'tiefling': 30, 'dragonborn': 30, 'half-orc': 30,
    'dwarf': 25, 'halfling': 25, 'gnome': 25
  };

  // Calculate AC based on base + dex modifier (unarmored)
  const calculateBaseAC = (dexterity: number) => 10 + Math.floor((dexterity - 10) / 2);

  const handleAbilityChange = (ability: string, value: number) => {
    setFormData(prev => ({
      ...prev,
      abilities: { ...prev.abilities, [ability]: value }
    }));
  };


  const calculateModifier = (score: number) => Math.floor((score - 10) / 2);

  // Auto-calculate speed based on race
  React.useEffect(() => {
    const speed = raceSpeed[formData.race as keyof typeof raceSpeed] || 30;
    setFormData(prev => ({ ...prev, speed }));
  }, [formData.race]);

  // Auto-calculate AC based on dexterity
  React.useEffect(() => {
    const armor_class = calculateBaseAC(formData.abilities.dexterity);
    setFormData(prev => ({ ...prev, armor_class }));
  }, [formData.abilities.dexterity]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="character-creator">
      <h3>Create New Character</h3>
      <form onSubmit={handleSubmit} className="character-form">
        <div className="form-section">
          <h4>Basic Information</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Name:</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                required
              />
            </div>
            <div className="form-group">
              <label>Race:</label>
              <select
                value={formData.race}
                onChange={(e) => setFormData(prev => ({ ...prev, race: e.target.value }))}
              >
                {races.map(race => (
                  <option key={race} value={race}>{race.charAt(0).toUpperCase() + race.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Class:</label>
              <select
                value={formData.class_name}
                onChange={(e) => setFormData(prev => ({ ...prev, class_name: e.target.value }))}
              >
                {classes.map(cls => (
                  <option key={cls} value={cls}>{cls.charAt(0).toUpperCase() + cls.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Background:</label>
              <select
                value={formData.background}
                onChange={(e) => setFormData(prev => ({ ...prev, background: e.target.value }))}
              >
                {backgrounds.map(bg => (
                  <option key={bg} value={bg}>{bg.replace('_', ' ').charAt(0).toUpperCase() + bg.replace('_', ' ').slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Level:</label>
              <input
                type="number"
                min="1"
                max="20"
                value={formData.level}
                onChange={(e) => setFormData(prev => ({ ...prev, level: parseInt(e.target.value) }))}
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h4>Ability Scores</h4>
          <div className="abilities-grid">
            {Object.entries(formData.abilities).map(([ability, score]) => (
              <div key={ability} className="ability-group">
                <label>{ability.toUpperCase()}:</label>
                <input
                  type="number"
                  min="3"
                  max="20"
                  value={score}
                  onChange={(e) => handleAbilityChange(ability, parseInt(e.target.value))}
                />
                <span className="modifier">({calculateModifier(score) >= 0 ? '+' : ''}{calculateModifier(score)})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="form-section">
          <h4>Combat Stats</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Max HP:</label>
              <input
                type="number"
                min="1"
                value={formData.max_hp}
                onChange={(e) => setFormData(prev => ({ ...prev, max_hp: parseInt(e.target.value) }))}
              />
            </div>
            <div className="form-group">
              <label>Armor Class (calculated):</label>
              <div className="calculated-stat">
                {formData.armor_class} (10 + DEX mod: {calculateModifier(formData.abilities.dexterity)})
              </div>
            </div>
            <div className="form-group">
              <label>Speed (racial):</label>
              <div className="calculated-stat">
                {formData.speed} ft ({formData.race})
              </div>
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="cancel-button">Cancel</button>
          <button type="submit" className="submit-button">Create Character</button>
        </div>
      </form>
    </div>
  );
};

interface CampaignInfo {
  name?: string;
  act: number;
  location: string;
  session: number;
  active_npcs: number;
  plot_threads: number;
}

interface SystemStatus {
  dynamic_dm_loaded: boolean;
  campaign_loaded?: string;
  campaign_info?: CampaignInfo;
  campaign_id?: number;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [availableCampaigns, setAvailableCampaigns] = useState<string[]>([]);
  const [userId] = useState('player1');
  const [activeTab, setActiveTab] = useState<'chat' | 'generator' | 'characters' | 'spells'>('chat');
  const [diceAdvantage, setDiceAdvantage] = useState<'normal' | 'advantage' | 'disadvantage'>('normal');
  const [customModifier, setCustomModifier] = useState<number>(0);

  // Character management state
  const [characters, setCharacters] = useState<any[]>([]);
  const [activeCharacter, setActiveCharacter] = useState<any>(null);
  const [showCharacterCreator, setShowCharacterCreator] = useState(false);
  const [showCharacterEditor, setShowCharacterEditor] = useState(false);
  const [showLevelUpWizard, setShowLevelUpWizard] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<any>(null);

  // Companion management state
  const [companions, setCompanions] = useState<any[]>([]);
  const [showCompanionSelection, setShowCompanionSelection] = useState(false);

  const websocketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchStatus = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/status');
      const status = await response.json();
      setSystemStatus(status);
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  const fetchCampaigns = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/campaigns');
      const data = await response.json();
      setAvailableCampaigns(data.campaigns);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    }
  };

  const loadCampaign = async (campaignName: string) => {
    try {
      const response = await fetch(`http://localhost:8080/api/load_campaign/${campaignName}`, {
        method: 'POST'
      });
      if (response.ok) await fetchStatus();
      else console.error('Failed to load campaign:', response.status, response.statusText);
    } catch (error) {
      console.error('Error loading campaign:', error);
    }
  };

  const clearCampaign = async () => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm('Clear the current campaign? You can reload it later.')) return;
    try {
      const response = await fetch('http://localhost:8080/api/clear_campaign', {
        method: 'POST'
      });
      if (response.ok) {
        await fetchStatus();
        setMessages([]);
      } else {
        console.error('Failed to clear campaign:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error clearing campaign:', error);
    }
  };

  const deleteCampaign = async (campaignName: string) => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm(`Permanently delete campaign "${campaignName}"? This cannot be undone!`)) return;
    try {
      const response = await fetch(`http://localhost:8080/api/campaigns/${campaignName}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        await fetchStatus();
        await fetchCampaigns();
        setMessages([]);
      } else {
        console.error('Failed to delete campaign:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error deleting campaign:', error);
    } 
  };

  const endSession = async () => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm('Are you sure you want to end the current session? This will generate a summary and prepare for the next session.')) return;

    setMessages(prev => [...prev, {
      type: 'system',
      user_id: 'SYSTEM',
      message: 'Summarizing session, please wait... This may take a moment.',
      timestamp: new Date().toISOString()
    }]);

    try {
      const response = await fetch(`http://localhost:8080/api/sessions/end/${userId}`, {
        method: 'POST'
      });
      if (response.ok) {
        const result = await response.json();
        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'SYSTEM',
          message: `Session Ended. Summary:\n${result.summary}`,
          timestamp: new Date().toISOString()
        }]);
        setMessages([]);
        await clearCampaign();
      } else {
        console.error('Failed to end session:', response.status, response.statusText);
        setMessages(prev => [...prev, {
          type: 'error',
          user_id: 'ERROR',
          message: 'Failed to generate session summary. Please try again.',
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error ending session:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        user_id: 'ERROR',
        message: 'An error occurred while ending the session.',
        timestamp: new Date().toISOString()
      }]);
    }
  };

  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = `ws://localhost:8080/ws/${userId}`;
      websocketRef.current = new WebSocket(wsUrl);
      websocketRef.current.onopen = () => setIsConnected(true);
      websocketRef.current.onmessage = (event) => {
        const message: Message = JSON.parse(event.data);
        if (message.type === 'typing') {
          setIsTyping(message.typing || false);
        } else {
          setMessages(prev => [...prev, message]);
        }
      };
      websocketRef.current.onclose = () => {
        setIsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };
      websocketRef.current.onerror = (error) => console.error('WebSocket error:', error);
    };

    connectWebSocket();
    fetchStatus();
    fetchCampaigns();

    return () => {
      websocketRef.current?.close();
    };
  }, [userId]);

  // Character management functions
  const fetchCharacters = React.useCallback(async () => {
    if (!systemStatus?.campaign_loaded || !systemStatus?.campaign_id) return;
    try {
      const response = await fetch(`http://localhost:8080/api/characters?user_id=${userId}&campaign_id=${systemStatus.campaign_id}`);
      if (response.ok) {
        const data = await response.json();
        setCharacters(data.characters || []);
        setActiveCharacter(data.active_character || null);
      }
    } catch (error) {
      console.error('Error fetching characters:', error);
    }
  }, [systemStatus?.campaign_loaded, systemStatus?.campaign_id, userId]);

  // Fetch characters when campaign is loaded
  useEffect(() => {
    if (systemStatus?.campaign_loaded) {
      fetchCharacters();
    }
  }, [systemStatus?.campaign_loaded, fetchCharacters]);

  // Companion management functions
  const fetchCompanions = React.useCallback(async () => {
    if (!activeCharacter) {
      setCompanions([]);
      return;
    }

    try {
      const response = await fetch(`http://localhost:8080/api/companions/character/${activeCharacter.id}`);
      if (response.ok) {
        const data = await response.json();
        setCompanions(Array.isArray(data.companions) ? data.companions : []);
      } else {
        console.error('Failed to fetch companions:', response.status);
        setCompanions([]);
      }
    } catch (error) {
      console.error('Error fetching companions:', error);
      setCompanions([]);
    }
  }, [activeCharacter]);

  const handleCompanionCreated = async () => {
    await fetchCompanions();
    setShowCompanionSelection(false);
  };

  const handleCompanionHeal = async (companionId: number, amount: number) => {
    try {
      const response = await fetch(`http://localhost:8080/api/companions/${companionId}/heal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ healing_amount: amount })
      });

      if (response.ok) {
        await fetchCompanions();
      }
    } catch (error) {
      console.error('Error healing companion:', error);
    }
  };

  const handleCompanionDamage = async (companionId: number, amount: number) => {
    try {
      const response = await fetch(`http://localhost:8080/api/companions/${companionId}/damage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ damage_amount: amount })
      });

      if (response.ok) {
        await fetchCompanions();
      }
    } catch (error) {
      console.error('Error damaging companion:', error);
    }
  };

  const handleCompanionLevelUp = async (companionId: number, rangerLevel: number) => {
    try {
      const response = await fetch(`http://localhost:8080/api/companions/${companionId}/level-up?ranger_level=${rangerLevel}`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchCompanions();
      }
    } catch (error) {
      console.error('Error leveling up companion:', error);
    }
  };

  const handleCompanionDismiss = async (companionId: number) => {
    if (!window.confirm('Are you sure you want to dismiss this companion?')) return;

    try {
      const response = await fetch(`http://localhost:8080/api/companions/${companionId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await fetchCompanions();
      }
    } catch (error) {
      console.error('Error dismissing companion:', error);
    }
  };

  // Handle rest for active character
  const handleRest = async (restType: 'short' | 'long') => {
    if (!activeCharacter) return;

    try {
      const response = await fetch(`http://localhost:8080/api/characters/${activeCharacter.id}/rest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rest_type: restType })
      });

      if (response.ok) {
        const result = await response.json();

        // Add rest result to chat messages
        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'REST',
          message: `🛌 **${activeCharacter.name}** takes a ${restType} rest:\n${result.recovery.join('\n')}`,
          timestamp: new Date().toISOString()
        }]);

        // Refresh character data
        await fetchCharacters();
      } else {
        const error = await response.json();
        setMessages(prev => [...prev, {
          type: 'error',
          user_id: 'ERROR',
          message: `Failed to rest: ${error.detail}`,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error taking rest:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        user_id: 'ERROR',
        message: `Error taking ${restType} rest`,
        timestamp: new Date().toISOString()
      }]);
    }
  };

  // Fetch companions when active character changes
  useEffect(() => {
    if (activeCharacter) {
      fetchCompanions();
    } else {
      setCompanions([]);
    }
  }, [activeCharacter, fetchCompanions]);

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !websocketRef.current || !isConnected) return;
    const messageData = { type: 'chat', message: inputMessage.trim() };
    websocketRef.current.send(JSON.stringify(messageData));
    setInputMessage('');
  };

  const handleGenerationComplete = () => {
    console.log('Campaign generation complete! Refreshing campaign list and switching tab.');
    fetchCampaigns();
    setActiveTab('chat');
  };

  const formatCampaignName = (rawName: string = '') => {
    return rawName
      .replace(/_/g, ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  };

  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return 'Unknown Time';
    try {
      const date = new Date(timestamp);
      return isNaN(date.getTime()) ? 'Invalid Time' : date.toLocaleTimeString();
    } catch (error) {
      return 'Error Time';
    }
  };

  const createCharacter = async (characterData: any) => {
    try {
      const response = await fetch('http://localhost:8080/api/characters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...characterData,
          campaign_id: systemStatus?.campaign_id || 1,
          user_id: userId
        })
      });
      if (response.ok) {
        await fetchCharacters();
        setShowCharacterCreator(false);
      }
    } catch (error) {
      console.error('Error creating character:', error);
    }
  };

  const setActiveCharacterById = async (characterId: number) => {
    try {
      console.log('Setting active character:', characterId, 'Current active:', activeCharacter?.id);
      const response = await fetch(`http://localhost:8080/api/characters/${characterId}/set-active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, campaign_id: systemStatus?.campaign_id || 1 })
      });
      if (response.ok) {
        await fetchCharacters();
      }
    } catch (error) {
      console.error('Error setting active character:', error);
    }
  };

  const openCharacterEditor = (character: any) => {
    setEditingCharacter(character);
    setShowCharacterEditor(true);
  };

  const openLevelUpWizard = (character: any) => {
    setEditingCharacter(character);
    setShowLevelUpWizard(true);
  };

  const handleCharacterEditorSave = async (updatedCharacter: any) => {
    await fetchCharacters();
    setShowCharacterEditor(false);
    setEditingCharacter(null);
  };

  const handleLevelUpComplete = async (updatedCharacter: any) => {
    await fetchCharacters();
    setShowLevelUpWizard(false);
    setEditingCharacter(null);
  };

  const startNewSession = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/sessions/start_new', {
        method: 'POST'
      });
      if (response.ok) {
        const result = await response.json();
        setMessages([{
          type: 'system',
          user_id: 'SYSTEM',
          message: result.message + ' - You can now begin fresh with a recap!',
          timestamp: new Date().toISOString()
        }]);
      } else {
        console.error('Failed to start new session:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error starting new session:', error);
    }
  };

  const renderMarkdown = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|~~[^~]+~~)/);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      } else if (part.startsWith('*') && part.endsWith('*')) {
        return <em key={index}>{part.slice(1, -1)}</em>;
      } else if (part.startsWith('~~') && part.endsWith('~~')) {
        return <del key={index}>{part.slice(2, -2)}</del>;
      }
      return part;
    });
  };

  // Dice rolling functions
  const rollBasicDice = async (sides: number, count: number = 1, modifier: number = 0) => {
    try {
      const totalModifier = modifier + customModifier;
      const response = await fetch('http://localhost:8080/api/dice/roll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dice_count: count,
          dice_sides: sides,
          modifier: totalModifier,
          advantage: sides === 20 ? diceAdvantage : 'normal' // Only apply advantage to d20s
        })
      });

      if (response.ok) {
        const result = await response.json();
        let rollDetails = result.rolls.join(', ');

        // Show both dice for advantage/disadvantage
        if (result.dropped && result.dropped.length > 0) {
          const advantageType = result.advantage === 'advantage' ? 'ADV' : 'DIS';
          rollDetails = `${result.rolls[0]}, ~~${result.dropped[0]}~~ (${advantageType})`;
        }

        const rollMessage = `🎲 **${result.description}**: ${result.total} (${rollDetails}${result.modifier !== 0 ? ` ${result.modifier > 0 ? '+' : ''}${result.modifier}` : ''})`;

        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'DICE',
          message: rollMessage,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error rolling dice:', error);
    }
  };

  const rollSkillCheck = async (skill: string) => {
    try {
      const endpoint = activeCharacter
        ? `http://localhost:8080/api/characters/${activeCharacter.id}/roll-skill`
        : 'http://localhost:8080/api/dice/skill';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill: skill, advantage: diceAdvantage })
      });

      if (response.ok) {
        const result = await response.json();
        let rollDetails = `d20: ${result.rolls[0]}`;

        // Show both dice for advantage/disadvantage
        if (result.dropped && result.dropped.length > 0) {
          const advantageType = result.advantage === 'advantage' ? 'ADV' : 'DIS';
          rollDetails = `d20: ${result.rolls[0]}, ~~${result.dropped[0]}~~ (${advantageType})`;
        }

        const rollMessage = `🎲 **${result.description}**: ${result.total} (${rollDetails}${result.modifier !== 0 ? ` ${result.modifier > 0 ? '+' : ''}${result.modifier}` : ''})`;

        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'DICE',
          message: rollMessage,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error rolling skill:', error);
    }
  };

  const rollAbilityCheck = async (ability: string) => {
    try {
      console.log('Rolling ability check for ability:', ability, 'Active character:', activeCharacter);
      const endpoint = activeCharacter
        ? `http://localhost:8080/api/characters/${activeCharacter.id}/roll-ability`
        : 'http://localhost:8080/api/dice/ability';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ability: ability, advantage: diceAdvantage })
      });

      if (response.ok) {
        const result = await response.json();
        let rollDetails = `d20: ${result.rolls[0]}`;

        // Show both dice for advantage/disadvantage
        if (result.dropped && result.dropped.length > 0) {
          const advantageType = result.advantage === 'advantage' ? 'ADV' : 'DIS';
          rollDetails = `d20: ${result.rolls[0]}, ~~${result.dropped[0]}~~ (${advantageType})`;
        }

        const rollMessage = `🎲 **${result.description}**: ${result.total} (${rollDetails}${result.modifier !== 0 ? ` ${result.modifier > 0 ? '+' : ''}${result.modifier}` : ''})`;

        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'DICE',
          message: rollMessage,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error rolling ability:', error);
    }
  };

  const rollInitiative = async () => {
    try {
      const endpoint = activeCharacter
        ? `http://localhost:8080/api/characters/${activeCharacter.id}/roll-ability`
        : 'http://localhost:8080/api/dice/ability';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ability: 'dex', advantage: diceAdvantage })
      });

      if (response.ok) {
        const result = await response.json();
        let rollDetails = `d20: ${result.rolls[0]}`;

        // Show both dice for advantage/disadvantage
        if (result.dropped && result.dropped.length > 0) {
          const advantageType = result.advantage === 'advantage' ? 'ADV' : 'DIS';
          rollDetails = `d20: ${result.rolls[0]}, ~~${result.dropped[0]}~~ (${advantageType})`;
        }

        const rollMessage = `🎲 **Initiative**: ${result.total} (${rollDetails}${result.modifier !== 0 ? ` ${result.modifier > 0 ? '+' : ''}${result.modifier}` : ''})`;

        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'DICE',
          message: rollMessage,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error rolling initiative:', error);
    }
  };

  const rollSavingThrow = async (ability: string) => {
    try {
      const endpoint = activeCharacter
        ? `http://localhost:8080/api/characters/${activeCharacter.id}/roll-save`
        : 'http://localhost:8080/api/dice/ability';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ability: ability, advantage: diceAdvantage })
      });

      if (response.ok) {
        const result = await response.json();
        let rollDetails = `d20: ${result.rolls[0]}`;

        // Show both dice for advantage/disadvantage
        if (result.dropped && result.dropped.length > 0) {
          const advantageType = result.advantage === 'advantage' ? 'ADV' : 'DIS';
          rollDetails = `d20: ${result.rolls[0]}, ~~${result.dropped[0]}~~ (${advantageType})`;
        }

        const rollMessage = `🎲 **${ability.toUpperCase()} Save**: ${result.total} (${rollDetails}${result.modifier !== 0 ? ` ${result.modifier > 0 ? '+' : ''}${result.modifier}` : ''})`;

        setMessages(prev => [...prev, {
          type: 'system',
          user_id: 'DICE',
          message: rollMessage,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Error rolling saving throw:', error);
    }
  };

  const renderMessage = (message: Message, index: number) => {
    const isUser = message.type === 'user_message';
    const isDM = message.type === 'dm_response';
    const isSystem = message.type === 'system';

    return (
      <div key={index} className={`message ${isUser ? 'user' : isDM ? 'dm' : isSystem ? 'system' : 'error'}`}>
        <div className="message-header">
          <span className="sender">{isUser ? message.user_id : isDM ? 'DM' : isSystem ? 'SYSTEM' : 'ERROR'}</span>
          <span className="timestamp">{formatTimestamp(message.timestamp)}</span>
        </div>
        <div className="message-content">{(isDM || isSystem) ? renderMarkdown(message.message) : message.message}</div>
        {isDM && message.campaign_state && (
          <div className="campaign-state">
            {message.campaign_state.location} (Act {message.campaign_state.act}, Session {message.campaign_state.session})
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>D&D AI Dungeon Master</h1>
        <div className="tab-navigation">
          <button className={`tab-button ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            Campaign Chat
          </button>
          <button className={`tab-button ${activeTab === 'generator' ? 'active' : ''}`} onClick={() => setActiveTab('generator')}>
            Campaign Generator
          </button>
          <button className={`tab-button ${activeTab === 'characters' ? 'active' : ''}`} onClick={() => setActiveTab('characters')}>
            Characters
          </button>
          <button className={`tab-button ${activeTab === 'spells' ? 'active' : ''}`} onClick={() => setActiveTab('spells')}>
            Spells
          </button>
        </div>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
      </header>

      <div className="main-content-wrapper">
        {activeTab === 'chat' && (
          <div className="main-content">
            <div className="left-panel wood-panel">
              <div className="campaign-info">
                {systemStatus?.campaign_loaded ? (
                  <div>
                    <h3>Campaign: {formatCampaignName(systemStatus.campaign_info?.name)}</h3>
                    <p>Act {systemStatus.campaign_info?.act} - {systemStatus.campaign_info?.location}</p>
                    {activeCharacter && (
                      <div className="active-character-card">
                        <div className="character-card-header">
                          <h4>Active Character</h4>
                        </div>
                        <div className="character-card-content">
                            <div className="character-identity">
                            <div className="character-name">{activeCharacter.name}</div>
                            <div className="character-details">
                                {activeCharacter.race} {activeCharacter.class_name} • Level {activeCharacter.level}
                            </div>
                            </div>
                            <div className="character-vitals">
                            <div className="vital-stat">
                                <span className="vital-label">HP</span>
                                <span className="vital-value">{activeCharacter.current_hp}/{activeCharacter.max_hp}</span>
                            </div>
                            <div className="vital-stat">
                                <span className="vital-label">AC</span>
                                <span className="vital-value">{activeCharacter.armor_class}</span>
                            </div>
                            </div>
                        </div>
                      </div>
                    )}
                    <div className="campaign-controls">
                      <button onClick={startNewSession} className="btn btn-primary">Start New Session</button>
                      <button onClick={() => endSession()} className="btn btn-purple">End Session</button>
                      <button onClick={clearCampaign} className="btn btn-warning">Clear</button>
                      <button onClick={() => deleteCampaign(systemStatus.campaign_info?.name || '')} className="btn btn-danger">Delete</button>
                    </div>

                    {/* Rest Controls for Active Character */}
                    {activeCharacter && (
                      <div className="rest-controls">
                        <h4>Rest & Recovery</h4>
                        <div className="rest-buttons">
                          <button
                            onClick={() => handleRest('short')}
                            className="btn btn-secondary"
                            title="Recover some abilities, spend hit dice"
                          >
                            Short Rest
                          </button>
                          <button
                            onClick={() => handleRest('long')}
                            className="btn btn-primary"
                            title="Recover all HP and spell slots"
                          >
                            Long Rest
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <h3>No Campaign Loaded</h3>
                    {availableCampaigns.length > 0 ? (
                      <select onChange={(e) => e.target.value && loadCampaign(e.target.value)} defaultValue="">
                        <option value="">Select Campaign</option>
                        {availableCampaigns.map(campaign => (
                          <option key={campaign} value={campaign}>
                            {formatCampaignName(campaign)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p>No campaigns found. Go to the Campaign Generator to create one!</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="chat-container">
              <div className="messages">
                {messages.map((message, index) => renderMessage(message, index))}
                {isTyping && (
                  <div className="message dm typing-indicator">
                    <div className="message-header"><span className="sender">DM</span></div>
                    <div className="message-content"><span className="typing-dots">DM is typing...</span></div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <form className="message-input-form" onSubmit={sendMessage}>
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Type your action or message..."
                  disabled={!isConnected || !systemStatus?.campaign_loaded}
                  className="message-input"
                />
                <button type="submit" disabled={!isConnected || !inputMessage.trim() || !systemStatus?.campaign_loaded} className="send-button">
                  Send
                </button>
              </form>
            </div>

            <div className="right-panel wood-panel">
              {/* Dice Rolling Panel */}
              <div className="dice-panel">
                <h3>Dice Rolls</h3>
                {activeCharacter && (
                  <div className="active-character-indicator">
                    Rolling for: <strong>{activeCharacter.name}</strong>
                  </div>
                )}

                {/* Quick Spell Casting - Only show for spellcasters */}
                {activeCharacter && (
                  <>
                    {console.log('Debug - activeCharacter:', activeCharacter)}
                    <div>Debug: About to render QuickSpellPanel for character {activeCharacter.id}</div>
                    <QuickSpellPanel
                      characterId={activeCharacter.id}
                    onSpellCast={(result) => {
                      console.log('QuickSpellPanel - Spell cast result received:', result);

                      try {
                        // Add spell cast result to chat messages
                        let message = `✨ **${result.spell_name}** cast`;

                        // Add slot level if upcast
                        if (result.slot_level_used && result.slot_level_used > 1) {
                          message += ` (Level ${result.slot_level_used})`;
                        }

                        console.log('Message after slot level:', message);

                        // Add damage info if available
                        if (result.spell_effects?.damage) {
                          const damage = result.spell_effects.damage;
                          console.log('Processing damage:', damage);
                          if (damage.dice && damage.dice.trim()) {
                            message += ` - **Damage:** ${damage.dice} ${damage.type}`;
                          } else if (damage.type) {
                            message += ` - **${damage.type} damage**`;
                          }
                        }

                        console.log('Message after damage:', message);

                        // Add saving throw info if available
                        if (result.spell_effects?.saving_throw) {
                          const save = result.spell_effects.saving_throw;
                          console.log('Processing save:', save);
                          message += ` - **${save.ability.toUpperCase()} Save**`;
                          if (save.dc) {
                            message += ` DC ${save.dc}`;
                          }
                        }

                        console.log('Message after save:', message);

                        // Always show cast successfully message if no effects added
                        if (!message.includes(' - ')) {
                          message += ' - Cast successfully!';
                        }

                        console.log('Final message:', message);
                        console.log('Current messages length before:', messages.length);

                        setMessages(prev => {
                          const newMessages = [...prev, {
                            type: 'system' as const,
                            user_id: 'SPELL',
                            message: message,
                            timestamp: new Date().toISOString()
                          }];
                          console.log('New messages length:', newMessages.length);
                          return newMessages;
                        });

                        console.log('Message should be added now');
                      } catch (error) {
                        console.error('Error in onSpellCast:', error);
                      }
                    }}
                  />
                  </>
                )}

                {/* Dice Modifiers */}
                <div className="dice-modifiers">
                  <div className="modifier-section">
                    <label>Advantage:</label>
                    <select
                      value={diceAdvantage}
                      onChange={(e) => setDiceAdvantage(e.target.value as 'normal' | 'advantage' | 'disadvantage')}
                      className="advantage-select"
                    >
                      <option value="normal">Normal</option>
                      <option value="advantage">Advantage</option>
                      <option value="disadvantage">Disadvantage</option>
                    </select>
                  </div>

                  <div className="modifier-section">
                    <label>Modifier:</label>
                    <input
                      type="number"
                      value={customModifier}
                      onChange={(e) => setCustomModifier(parseInt(e.target.value) || 0)}
                      className="modifier-input"
                      placeholder="±0"
                      min="-10"
                      max="10"
                    />
                  </div>

                  <button
                    onClick={() => {setDiceAdvantage('normal'); setCustomModifier(0);}}
                    className="btn btn-neutral"
                  >
                    Reset
                  </button>
                </div>

                {/* Basic Dice */}
                <div className="dice-section">
                  <h4>Basic Dice</h4>
                  <div className="dice-grid">
                    <button onClick={() => rollBasicDice(4)} className="dice-button">d4</button>
                    <button onClick={() => rollBasicDice(6)} className="dice-button">d6</button>
                    <button onClick={() => rollBasicDice(8)} className="dice-button">d8</button>
                    <button onClick={() => rollBasicDice(10)} className="dice-button">d10</button>
                    <button onClick={() => rollBasicDice(12)} className="dice-button">d12</button>
                    <button onClick={() => rollBasicDice(20)} className="dice-button">d20</button>
                    <button onClick={() => rollBasicDice(100)} className="dice-button">d100</button>
                  </div>
                </div>

                {/* Ability Checks */}
                <div className="dice-section">
                  <h4>Ability Checks</h4>
                  <div className="dice-grid">
                    <button onClick={() => rollAbilityCheck('str')} className="ability-button">STR</button>
                    <button onClick={() => rollAbilityCheck('dex')} className="ability-button">DEX</button>
                    <button onClick={() => rollAbilityCheck('con')} className="ability-button">CON</button>
                    <button onClick={() => rollAbilityCheck('int')} className="ability-button">INT</button>
                    <button onClick={() => rollAbilityCheck('wis')} className="ability-button">WIS</button>
                    <button onClick={() => rollAbilityCheck('cha')} className="ability-button">CHA</button>
                  </div>
                </div>

                {/* Skill Checks */}
                <div className="dice-section">
                  <h4>Skills</h4>
                  <div className="skill-grid">
                    <button onClick={() => rollSkillCheck('acrobatics')} className="skill-button">Acrobatics</button>
                    <button onClick={() => rollSkillCheck('animal_handling')} className="skill-button">Animal Handling</button>
                    <button onClick={() => rollSkillCheck('arcana')} className="skill-button">Arcana</button>
                    <button onClick={() => rollSkillCheck('athletics')} className="skill-button">Athletics</button>
                    <button onClick={() => rollSkillCheck('deception')} className="skill-button">Deception</button>
                    <button onClick={() => rollSkillCheck('history')} className="skill-button">History</button>
                    <button onClick={() => rollSkillCheck('insight')} className="skill-button">Insight</button>
                    <button onClick={() => rollSkillCheck('intimidation')} className="skill-button">Intimidation</button>
                    <button onClick={() => rollSkillCheck('investigation')} className="skill-button">Investigation</button>
                    <button onClick={() => rollSkillCheck('medicine')} className="skill-button">Medicine</button>
                    <button onClick={() => rollSkillCheck('nature')} className="skill-button">Nature</button>
                    <button onClick={() => rollSkillCheck('perception')} className="skill-button">Perception</button>
                    <button onClick={() => rollSkillCheck('performance')} className="skill-button">Performance</button>
                    <button onClick={() => rollSkillCheck('persuasion')} className="skill-button">Persuasion</button>
                    <button onClick={() => rollSkillCheck('religion')} className="skill-button">Religion</button>
                    <button onClick={() => rollSkillCheck('sleight_of_hand')} className="skill-button">Sleight of Hand</button>
                    <button onClick={() => rollSkillCheck('stealth')} className="skill-button">Stealth</button>
                    <button onClick={() => rollSkillCheck('survival')} className="skill-button">Survival</button>
                  </div>
                </div>

                {/* Combat Rolls */}
                <div className="dice-section">
                  <h4>Combat</h4>
                  <div className="dice-grid">
                    <button onClick={rollInitiative} className="initiative-button">Initiative</button>
                  </div>
                </div>

                {/* Saving Throws */}
                <div className="dice-section">
                  <h4>Saving Throws</h4>
                  <div className="dice-grid">
                    <button onClick={() => rollSavingThrow('str')} className="save-button">STR Save</button>
                    <button onClick={() => rollSavingThrow('dex')} className="save-button">DEX Save</button>
                    <button onClick={() => rollSavingThrow('con')} className="save-button">CON Save</button>
                    <button onClick={() => rollSavingThrow('int')} className="save-button">INT Save</button>
                    <button onClick={() => rollSavingThrow('wis')} className="save-button">WIS Save</button>
                    <button onClick={() => rollSavingThrow('cha')} className="save-button">CHA Save</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'generator' && (
          <div className="page-container">
            <CampaignGenerator onGenerationComplete={handleGenerationComplete} />
          </div>
        )}

        {activeTab === 'characters' && (
          <div className="page-container character-management">
            <div className="page-header">
              <h2>Character Management</h2>
              {!systemStatus?.campaign_loaded ? (
                <p>Please load a campaign to manage characters.</p>
              ) : (
                <button
                  onClick={() => setShowCharacterCreator(true)}
                  className="btn btn-primary"
                >
                  Create New Character
                </button>
              )}
            </div>

            {systemStatus?.campaign_loaded && (
              <>
                {/* Character List */}
                <div className="character-list-section">
                  <h3>All Characters</h3>
                  {characters.length === 0 ? (
                    <p>No characters found. Create your first character!</p>
                  ) : (
                    <div className="character-list">
                      {characters.map(character => (
                        <div
                          key={character.id}
                          className={`character-card ${character.id === activeCharacter?.id ? 'active' : ''}`}
                          onClick={() => character.id !== activeCharacter?.id && setActiveCharacterById(character.id)}
                          style={{ cursor: character.id !== activeCharacter?.id ? 'pointer' : 'default' }}
                        >
                          <div
                            className="character-main"
                          >
                            <div className="character-header">
                              <h4>{character.name}</h4>
                              <span className="character-class">{character.race} {character.class_name}</span>
                              <span className="character-level">Level {character.level}</span>
                            </div>
                            <div className="character-stats">
                              <div className="stat-group">
                                <span>HP: {character.current_hp}/{character.max_hp}</span>
                                <span>AC: {character.armor_class}</span>
                                <span>Speed: {character.speed}ft</span>
                              </div>
                            </div>
                            {character.id === activeCharacter?.id && (
                              <div className="active-indicator">ACTIVE</div>
                            )}
                          </div>
                          <div className="character-actions">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                openCharacterEditor(character);
                              }}
                              className="btn btn-secondary"
                            >
                              Edit
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                openLevelUpWizard(character);
                              }}
                              className="btn btn-warning"
                              disabled={character.level >= 20}
                            >
                              Level Up
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Animal Companions Section */}
                {activeCharacter && (
                  <div className="companions-section">
                    <div className="companions-header">
                      <h3>Animal Companions</h3>
                      {(activeCharacter.class_name?.toLowerCase().includes('ranger')) && (
                        <button
                          onClick={() => setShowCompanionSelection(true)}
                          className="create-companion-button"
                          disabled={Array.isArray(companions) && companions.some(comp => !comp.is_dead)}
                        >
                          {Array.isArray(companions) && companions.some(comp => !comp.is_dead) ? 'Already Has Companion' : 'Get Animal Companion'}
                        </button>
                      )}
                    </div>

                    {!Array.isArray(companions) || companions.length === 0 ? (
                      <p className="no-companions">
                        {activeCharacter.class_name?.toLowerCase().includes('ranger')
                          ? `No animal companions yet. Rangers can acquire companions starting at level 3. (Current: Level ${activeCharacter.level} ${activeCharacter.class_name})`
                          : `This character class cannot have animal companions. (${activeCharacter.class_name})`}
                      </p>
                    ) : (
                      <div className="companions-list">
                        {Array.isArray(companions) && companions.map((companion) => (
                          <CompanionCard
                            key={companion.id}
                            companion={companion}
                            onHeal={handleCompanionHeal}
                            onDamage={handleCompanionDamage}
                            onLevelUp={handleCompanionLevelUp}
                            onDismiss={handleCompanionDismiss}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Character Creator Modal */}
                {showCharacterCreator && (
                  <div className="modal-overlay" onClick={() => setShowCharacterCreator(false)}>
                    <div className="modal-content wide-modal" onClick={(e) => e.stopPropagation()}>
                      <DetailedCharacterCreator
                        campaignId={systemStatus?.campaign_id || 1}
                        onSubmit={(result) => {
                          console.log('Character created:', result);
                          fetchCharacters();
                          setShowCharacterCreator(false);
                        }}
                        onCancel={() => setShowCharacterCreator(false)}
                      />
                    </div>
                  </div>
                )}

                {/* Character Editor Modal */}
                {showCharacterEditor && editingCharacter && (
                  <div className="modal-overlay" onClick={() => setShowCharacterEditor(false)}>
                    <div className="modal-content wide-modal" onClick={(e) => e.stopPropagation()}>
                      <CharacterEditor
                        character={editingCharacter}
                        onSave={handleCharacterEditorSave}
                        onCancel={() => {
                          setShowCharacterEditor(false);
                          setEditingCharacter(null);
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Level Up Wizard Modal */}
                {showLevelUpWizard && editingCharacter && (
                  <div className="modal-overlay" onClick={() => setShowLevelUpWizard(false)}>
                    <div className="modal-content wide-modal" onClick={(e) => e.stopPropagation()}>
                      <LevelUpWizard
                        character={editingCharacter}
                        onComplete={handleLevelUpComplete}
                        onCancel={() => {
                          setShowLevelUpWizard(false);
                          setEditingCharacter(null);
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Companion Selection Modal */}
                {showCompanionSelection && activeCharacter && (
                  <CompanionSelection
                    characterId={activeCharacter.id}
                    campaignId={systemStatus?.campaign_id || 1}
                    onCompanionCreated={handleCompanionCreated}
                    onClose={() => setShowCompanionSelection(false)}
                  />
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'spells' && (
          <div className="page-container">
            <div className="page-header">
              <h2>Spell Management</h2>
              {!systemStatus?.campaign_loaded ? (
                <p>Please load a campaign to manage spells.</p>
              ) : !activeCharacter ? (
                <p>Please select an active character to view their spells.</p>
              ) : (
                <p>Managing spells for {activeCharacter.name}</p>
              )}
            </div>
            {systemStatus?.campaign_loaded && activeCharacter && (
              <SpellManager
                characterId={activeCharacter.id}
                onSpellCast={(result) => {
                  // Handle spell cast result - could add to chat log or show notification
                  console.log('Spell cast result:', result);
                }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default App;