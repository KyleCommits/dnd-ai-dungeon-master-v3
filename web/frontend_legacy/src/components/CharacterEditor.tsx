import React, { useState, useEffect } from 'react';
import './CharacterEditor.css';

interface CharacterEditorProps {
  character: any;
  onSave: (updatedCharacter: any) => void;
  onCancel: () => void;
}

const CharacterEditor: React.FC<CharacterEditorProps> = ({ character, onSave, onCancel }) => {
  const [editData, setEditData] = useState({
    name: character.name || '',
    race: character.race || '',
    class_name: character.class_name || '',
    background: character.background || '',
    level: character.level || 1,
    current_hp: character.current_hp || character.max_hp || 0,
    max_hp: character.max_hp || 0,
    armor_class: character.armor_class || 10,
    speed: character.speed || 30,
    abilities: {
      strength: character.abilities?.strength || 10,
      dexterity: character.abilities?.dexterity || 10,
      constitution: character.abilities?.constitution || 10,
      intelligence: character.abilities?.intelligence || 10,
      wisdom: character.abilities?.wisdom || 10,
      charisma: character.abilities?.charisma || 10
    }
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateModifier = (score: number) => Math.floor((score - 10) / 2);

  const handleAbilityChange = (ability: string, value: number) => {
    if (value < 1 || value > 30) return; // Reasonable bounds

    setEditData(prev => ({
      ...prev,
      abilities: {
        ...prev.abilities,
        [ability]: value
      }
    }));
  };

  const handleSave = async () => {
    if (!editData.name.trim()) {
      setError('Character name is required');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8080/api/characters/${character.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editData)
      });

      if (response.ok) {
        const updatedCharacter = await response.json();
        onSave(updatedCharacter);
      } else {
        const errorData = await response.json();
        setError(errorData.detail?.message || 'Failed to update character');
      }
    } catch (err) {
      setError('Error updating character');
      console.error('Save error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const healCharacter = async (amount: number) => {
    try {
      const response = await fetch(`http://localhost:8080/api/characters/${character.id}/heal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ heal_amount: amount })
      });

      if (response.ok) {
        const result = await response.json();
        setEditData(prev => ({
          ...prev,
          current_hp: result.new_hp
        }));
      }
    } catch (err) {
      console.error('Heal error:', err);
    }
  };

  return (
    <div className="character-editor">
      <div className="editor-header">
        <h3>Edit Character: {character.name}</h3>
      </div>

      <div className="editor-content">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Basic Information */}
        <div className="editor-section">
          <h4>Basic Information</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Name:</label>
              <input
                type="text"
                value={editData.name}
                onChange={(e) => setEditData(prev => ({ ...prev, name: e.target.value }))}
                maxLength={50}
              />
            </div>
            <div className="form-group">
              <label>Race:</label>
              <input
                type="text"
                value={editData.race}
                onChange={(e) => setEditData(prev => ({ ...prev, race: e.target.value }))}
                maxLength={30}
              />
            </div>
            <div className="form-group">
              <label>Class:</label>
              <input
                type="text"
                value={editData.class_name}
                onChange={(e) => setEditData(prev => ({ ...prev, class_name: e.target.value }))}
                maxLength={30}
              />
            </div>
            <div className="form-group">
              <label>Background:</label>
              <input
                type="text"
                value={editData.background}
                onChange={(e) => setEditData(prev => ({ ...prev, background: e.target.value }))}
                maxLength={30}
              />
            </div>
            <div className="form-group">
              <label>Level:</label>
              <input
                type="number"
                min="1"
                max="20"
                value={editData.level}
                onChange={(e) => setEditData(prev => ({ ...prev, level: parseInt(e.target.value) || 1 }))}
              />
            </div>
          </div>
        </div>

        {/* Combat Stats */}
        <div className="editor-section">
          <h4>Combat Stats</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Current HP:</label>
              <div className="hp-controls">
                <input
                  type="number"
                  min="0"
                  max={editData.max_hp}
                  value={editData.current_hp}
                  onChange={(e) => setEditData(prev => ({
                    ...prev,
                    current_hp: Math.min(parseInt(e.target.value) || 0, prev.max_hp)
                  }))}
                />
                <div className="heal-buttons">
                  <button type="button" onClick={() => healCharacter(1)} className="heal-button">+1</button>
                  <button type="button" onClick={() => healCharacter(5)} className="heal-button">+5</button>
                  <button type="button" onClick={() => healCharacter(editData.max_hp - editData.current_hp)} className="heal-button">Full</button>
                </div>
              </div>
            </div>
            <div className="form-group">
              <label>Max HP:</label>
              <input
                type="number"
                min="1"
                max="999"
                value={editData.max_hp}
                onChange={(e) => setEditData(prev => ({ ...prev, max_hp: parseInt(e.target.value) || 1 }))}
              />
            </div>
            <div className="form-group">
              <label>Armor Class:</label>
              <input
                type="number"
                min="1"
                max="30"
                value={editData.armor_class}
                onChange={(e) => setEditData(prev => ({ ...prev, armor_class: parseInt(e.target.value) || 10 }))}
              />
            </div>
            <div className="form-group">
              <label>Speed:</label>
              <input
                type="number"
                min="0"
                max="120"
                value={editData.speed}
                onChange={(e) => setEditData(prev => ({ ...prev, speed: parseInt(e.target.value) || 30 }))}
              />
            </div>
          </div>
        </div>

        {/* Ability Scores */}
        <div className="editor-section">
          <h4>Ability Scores</h4>
          <div className="abilities-grid">
            {Object.entries(editData.abilities).map(([ability, score]) => (
              <div key={ability} className="ability-group">
                <label>{ability.toUpperCase()}:</label>
                <div className="ability-controls">
                  <button
                    type="button"
                    onClick={() => handleAbilityChange(ability, score - 1)}
                    disabled={score <= 1}
                    className="ability-button"
                  >
                    -
                  </button>
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={score}
                    onChange={(e) => handleAbilityChange(ability, parseInt(e.target.value) || 10)}
                    className="ability-input"
                  />
                  <button
                    type="button"
                    onClick={() => handleAbilityChange(ability, score + 1)}
                    disabled={score >= 30}
                    className="ability-button"
                  >
                    +
                  </button>
                </div>
                <span className="modifier">
                  ({calculateModifier(score) >= 0 ? '+' : ''}{calculateModifier(score)})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* HP Status */}
        <div className="editor-section">
          <h4>Character Status</h4>
          <div className="status-display">
            <div className="hp-bar">
              <div className="hp-bar-label">HP: {editData.current_hp} / {editData.max_hp}</div>
              <div className="hp-bar-container">
                <div
                  className="hp-bar-fill"
                  style={{
                    width: `${(editData.current_hp / editData.max_hp) * 100}%`,
                    backgroundColor: editData.current_hp <= editData.max_hp * 0.25 ? '#f44336' :
                                   editData.current_hp <= editData.max_hp * 0.5 ? '#ff9800' : '#4caf50'
                  }}
                />
              </div>
            </div>
            {editData.current_hp === 0 && (
              <div className="status-warning">⚠️ Character is unconscious</div>
            )}
          </div>
        </div>
      </div>

      <div className="editor-actions">
        <button
          onClick={onCancel}
          className="cancel-button"
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="save-button"
          disabled={isLoading}
        >
          {isLoading ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
};

export default CharacterEditor;