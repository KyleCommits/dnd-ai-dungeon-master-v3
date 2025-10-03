// web/frontend/src/components/SpellManager.tsx
import React, { useState, useEffect } from 'react';

interface Spell {
  name: string;
  level: number;
  school: string;
  casting_time: string;
  range: string;
  components: string[];
  duration: string;
  description: string[];
  is_prepared?: boolean;
  is_known?: boolean;
  times_cast_today?: number;
  ritual: boolean;
  concentration: boolean;
  damage?: {
    type: string;
    at_slot_level: { [key: string]: string };
  };
}

interface CharacterSpellData {
  character_id: number;
  character_name: string;
  class_name: string;
  level: number;
  is_spellcaster: boolean;
  caster_type: string;
  spellcasting_ability: string;
  spellcasting_modifier: number;
  spell_save_dc: number;
  spell_attack_bonus: number;
  spell_slots: number[];
  spells_by_level: { [key: string]: Spell[] };
  total_spells: number;
}

interface SpellManagerProps {
  characterId: number;
  onSpellCast?: (result: any) => void;
}

const SpellManager: React.FC<SpellManagerProps> = ({ characterId, onSpellCast }) => {
  const [spellData, setSpellData] = useState<CharacterSpellData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpell, setSelectedSpell] = useState<Spell | null>(null);
  const [castingLevel, setCastingLevel] = useState<number>(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterLevel, setFilterLevel] = useState<number | null>(null);

  useEffect(() => {
    loadCharacterSpells();
  }, [characterId]);

  const loadCharacterSpells = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/characters/${characterId}/spells`);
      if (!response.ok) throw new Error('Failed to load spells');

      const data = await response.json();
      setSpellData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const castSpell = async (spell: Spell, slotLevel: number) => {
    try {
      const response = await fetch(`/api/characters/${characterId}/spells/cast`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          spell_name: spell.name,
          slot_level: slotLevel,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to cast spell');
      }

      const result = await response.json();

      // Notify parent component
      if (onSpellCast) {
        onSpellCast(result);
      }

      // Reload spell data to update usage counts
      await loadCharacterSpells();
    } catch (err) {
      console.error('Failed to cast spell:', err);
    }
  };

  const getFilteredSpells = () => {
    if (!spellData) return {};

    const filtered: { [key: string]: Spell[] } = {};

    Object.entries(spellData.spells_by_level).forEach(([level, spells]) => {
      const levelNum = parseInt(level);

      if (filterLevel !== null && levelNum !== filterLevel) return;

      const filteredSpells = spells.filter(spell =>
        spell.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        spell.school.toLowerCase().includes(searchTerm.toLowerCase())
      );

      if (filteredSpells.length > 0) {
        filtered[level] = filteredSpells;
      }
    });

    return filtered;
  };

  const prepareSpell = async (spellName: string, prepare: boolean) => {
    try {
      const response = await fetch(`/api/characters/${characterId}/spells/prepare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spell_name: spellName,
          prepare: prepare
        })
      });

      if (response.ok) {
        await loadCharacterSpells(); // Refresh data
      } else {
        const error = await response.json();
        console.error(`Failed to ${prepare ? 'prepare' : 'unprepare'} ${spellName}:`, error.detail);
      }
    } catch (error) {
      console.error(`Error ${prepare ? 'preparing' : 'unpreparing'} ${spellName}:`, error);
    }
  };

  const takeRest = async (restType: 'short' | 'long') => {
    try {
      const response = await fetch(`/api/characters/${characterId}/rest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rest_type: restType })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Rest completed:', result.message, result.recovery);
        await loadCharacterSpells(); // Refresh data
      } else {
        const error = await response.json();
        console.error(`Failed to rest:`, error.detail);
      }
    } catch (error) {
      console.error(`Error taking ${restType} rest:`, error);
    }
  };

  const SpellCard: React.FC<{ spell: Spell }> = ({ spell }) => {
    const canCast = spell.is_prepared || spell.level === 0; // Cantrips don't need preparation
    const minCastLevel = spell.level === 0 ? 1 : spell.level;
    const canPrepare = spell.level > 0 && spellData?.caster_type !== 'warlock' && !['Sorcerer', 'Warlock', 'Bard'].includes(spellData?.class_name || '');

    return (
      <div className="spell-card" style={{
        border: '2px solid #8B4513',
        borderRadius: '8px',
        padding: '12px',
        margin: '8px 0',
        backgroundColor: canCast ? '#2F4F2F' : '#4A4A4A',
        color: '#F5DEB3'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#DAA520' }}>
            {spell.name}
            {spell.ritual && <span style={{ fontSize: '0.8em', color: '#87CEEB' }}> (Ritual)</span>}
            {spell.concentration && <span style={{ fontSize: '0.8em', color: '#FF6347' }}> (Concentration)</span>}
          </h4>
          <div style={{ fontSize: '0.9em', color: '#D2B48C' }}>
            Level {spell.level} {spell.school}
          </div>
        </div>

        <div style={{ fontSize: '0.85em', color: '#D2B48C', marginBottom: '8px' }}>
          <strong>Casting Time:</strong> {spell.casting_time} |
          <strong> Range:</strong> {spell.range} |
          <strong> Components:</strong> {spell.components.join(', ')} |
          <strong> Duration:</strong> {spell.duration}
        </div>

        <div style={{ fontSize: '0.9em', marginBottom: '12px' }}>
          {Array.isArray(spell.description)
            ? spell.description.join(' ')
            : spell.description}
        </div>

        {spell.damage && (
          <div style={{ fontSize: '0.85em', color: '#FF6347', marginBottom: '8px' }}>
            <strong>Damage:</strong> {spell.damage.type}
            {spell.damage.at_slot_level && Object.entries(spell.damage.at_slot_level).map(([level, damage]) => (
              <span key={level}> | Level {level}: {damage}</span>
            ))}
          </div>
        )}

        {(spell.times_cast_today || 0) > 0 && (
          <div style={{ fontSize: '0.8em', color: '#FFD700', marginBottom: '8px' }}>
            Cast {spell.times_cast_today || 0} time(s) today
          </div>
        )}

        {canCast && spellData && spellData.spell_slots.some(slots => slots > 0) && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '8px' }}>
            <label style={{ fontSize: '0.85em' }}>Cast at level:</label>
            <select
              value={castingLevel}
              onChange={(e) => setCastingLevel(parseInt(e.target.value))}
              style={{
                padding: '4px',
                borderRadius: '4px',
                border: '1px solid #8B4513',
                backgroundColor: '#3E2723',
                color: '#F5DEB3'
              }}
            >
              {spellData.spell_slots.map((slots, index) => {
                const level = index + 1;
                if (level >= minCastLevel && slots > 0) {
                  return (
                    <option key={level} value={level}>
                      Level {level} ({slots} slots)
                    </option>
                  );
                }
                return null;
              })}
            </select>
            <button
              onClick={() => castSpell(spell, castingLevel)}
              style={{
                padding: '6px 12px',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: '#8B4513',
                color: '#F5DEB3',
                cursor: 'pointer',
                fontSize: '0.85em'
              }}
            >
              Cast
            </button>
          </div>
        )}

        {canPrepare && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '8px' }}>
            <button
              onClick={() => prepareSpell(spell.name, !spell.is_prepared)}
              style={{
                padding: '4px 8px',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: spell.is_prepared ? '#FF6347' : '#2F4F2F',
                color: '#F5DEB3',
                cursor: 'pointer',
                fontSize: '0.8em'
              }}
            >
              {spell.is_prepared ? 'Unprepare' : 'Prepare'}
            </button>
            {spell.is_prepared && <span style={{ fontSize: '0.8em', color: '#90EE90' }}>✓ Prepared</span>}
          </div>
        )}

        {!canCast && spell.level > 0 && !canPrepare && (
          <div style={{ fontSize: '0.8em', color: '#FF6347', fontStyle: 'italic' }}>
            Not prepared
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return <div style={{ color: '#F5DEB3', padding: '20px' }}>Loading spells...</div>;
  }

  if (error) {
    return <div style={{ color: '#FF6347', padding: '20px' }}>Error: {error}</div>;
  }

  if (!spellData || !spellData.is_spellcaster) {
    return (
      <div style={{ color: '#F5DEB3', padding: '20px' }}>
        This character is not a spellcaster.
      </div>
    );
  }

  const filteredSpells = getFilteredSpells();

  return (
    <div style={{
      backgroundColor: '#1E1E1E',
      color: '#F5DEB3',
      padding: '20px',
      borderRadius: '8px',
      minHeight: '600px'
    }}>
      <h2 style={{ color: '#DAA520', marginBottom: '20px' }}>
        {spellData.character_name}'s Spells
      </h2>

      {/* Character Info */}
      <div style={{
        backgroundColor: '#2F4F2F',
        padding: '16px',
        borderRadius: '8px',
        marginBottom: '20px',
        border: '2px solid #8B4513'
      }}>
        <h3 style={{ color: '#DAA520', margin: '0 0 12px 0' }}>Spellcasting Info</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '0.9em' }}>
          <div><strong>Class:</strong> {spellData.class_name}</div>
          <div><strong>Level:</strong> {spellData.level}</div>
          <div><strong>Caster Type:</strong> {spellData.caster_type}</div>
          <div><strong>Ability:</strong> {spellData.spellcasting_ability}</div>
          <div><strong>Modifier:</strong> +{spellData.spellcasting_modifier}</div>
          <div><strong>Spell Save DC:</strong> {spellData.spell_save_dc}</div>
          <div><strong>Spell Attack:</strong> +{spellData.spell_attack_bonus}</div>
        </div>

        {/* Spell Slots */}
        <div style={{ marginTop: '12px' }}>
          <strong>Spell Slots:</strong>
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
            {spellData.spell_slots.map((slots, index) => {
              const level = index + 1;
              if (slots > 0) {
                return (
                  <div key={level} style={{
                    padding: '4px 8px',
                    backgroundColor: '#8B4513',
                    borderRadius: '4px',
                    fontSize: '0.85em'
                  }}>
                    Level {level}: {slots}
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      </div>

      {/* Rest Actions */}
      <div style={{
        backgroundColor: '#2F4F2F',
        padding: '16px',
        borderRadius: '8px',
        marginBottom: '20px',
        border: '2px solid #8B4513',
        display: 'flex',
        gap: '12px',
        alignItems: 'center'
      }}>
        <h3 style={{ color: '#DAA520', margin: '0', flex: 1 }}>Rest & Recovery</h3>
        <button
          onClick={() => takeRest('short')}
          style={{
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: '#4682B4',
            color: '#F5DEB3',
            cursor: 'pointer',
            fontSize: '0.9em'
          }}
        >
          Short Rest
        </button>
        <button
          onClick={() => takeRest('long')}
          style={{
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: '#8B4513',
            color: '#F5DEB3',
            cursor: 'pointer',
            fontSize: '0.9em'
          }}
        >
          Long Rest
        </button>
      </div>

      {/* Search and Filter */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px',
        alignItems: 'center'
      }}>
        <input
          type="text"
          placeholder="Search spells..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #8B4513',
            backgroundColor: '#3E2723',
            color: '#F5DEB3',
            flex: 1
          }}
        />
        <select
          value={filterLevel || ''}
          onChange={(e) => setFilterLevel(e.target.value ? parseInt(e.target.value) : null)}
          style={{
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #8B4513',
            backgroundColor: '#3E2723',
            color: '#F5DEB3'
          }}
        >
          <option value="">All Levels</option>
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(level => (
            <option key={level} value={level}>
              {level === 0 ? 'Cantrips' : `Level ${level}`}
            </option>
          ))}
        </select>
      </div>

      {/* Spells by Level */}
      {Object.entries(filteredSpells).map(([level, spells]) => (
        <div key={level} style={{ marginBottom: '24px' }}>
          <h3 style={{ color: '#DAA520', borderBottom: '2px solid #8B4513', paddingBottom: '8px' }}>
            {level === '0' ? 'Cantrips' : `Level ${level} Spells`} ({spells.length})
          </h3>
          {spells.map(spell => (
            <SpellCard key={spell.name} spell={spell} />
          ))}
        </div>
      ))}

      {Object.keys(filteredSpells).length === 0 && (
        <div style={{ textAlign: 'center', color: '#D2B48C', fontSize: '1.1em', marginTop: '40px' }}>
          No spells found matching your criteria.
        </div>
      )}
    </div>
  );
};

export default SpellManager;