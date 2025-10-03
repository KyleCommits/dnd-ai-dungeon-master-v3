import React, { useState, useEffect } from 'react';
import './CompanionSelection.css';

interface CompanionTemplate {
  id: number;
  name: string;
  size: string;
  challenge_rating: string;
  armor_class: number;
  hit_points: number;
  abilities: {
    str: number;
    dex: number;
    con: number;
    int: number;
    wis: number;
    cha: number;
  };
  speed: {
    land: number;
    fly: number;
    swim: number;
    climb: number;
    burrow: number;
  };
  skills: Record<string, number>;
  special_abilities: Array<{
    name: string;
    description: string;
  }>;
  attacks: Array<{
    name: string;
    attack_bonus: number;
    damage: string;
    damage_type: string;
    range: string;
    special?: string;
  }>;
  environment: string;
  description: string;
}

interface CompanionSelectionProps {
  characterId: number;
  campaignId: number;
  onCompanionCreated: () => void;
  onClose: () => void;
}

export default function CompanionSelection({ characterId, campaignId, onCompanionCreated, onClose }: CompanionSelectionProps) {
  const [templates, setTemplates] = useState<CompanionTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<CompanionTemplate | null>(null);
  const [companionName, setCompanionName] = useState('');
  const [personalityTraits, setPersonalityTraits] = useState('');
  const [backstory, setBackstory] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState(1); // 1: Select Template, 2: Customize Details

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/companions/templates?companion_type=beast_master');
      if (response.ok) {
        const data = await response.json();
        setTemplates(Array.isArray(data.templates) ? data.templates : []);
      } else {
        console.error('Failed to fetch templates:', response.status);
        setTemplates([]);
        setError('Failed to load companion templates');
      }
    } catch (err) {
      console.error('Error fetching templates:', err);
      setTemplates([]);
      setError('Failed to load companion templates');
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSelect = (template: CompanionTemplate) => {
    setSelectedTemplate(template);
    setCompanionName(template.name);
    setStep(2);
  };

  const handleCreateCompanion = async () => {
    if (!selectedTemplate || !companionName.trim()) {
      setError('Please provide a name for your companion');
      return;
    }

    setCreating(true);
    setError('');

    try {
      const response = await fetch('/api/companions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character_id: characterId,
          template_id: selectedTemplate.id,
          campaign_id: campaignId,
          name: companionName,
          personality_traits: personalityTraits,
          backstory: backstory,
          notes: notes,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create companion');
      }

      onCompanionCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create companion');
    } finally {
      setCreating(false);
    }
  };

  const getAbilityModifier = (score: number) => {
    return Math.floor((score - 10) / 2);
  };

  const formatModifier = (modifier: number) => {
    return modifier >= 0 ? `+${modifier}` : `${modifier}`;
  };

  const getSpeedDisplay = (speed: CompanionTemplate['speed']) => {
    const speeds = [];
    if (speed.land > 0) speeds.push(`${speed.land} ft.`);
    if (speed.fly > 0) speeds.push(`fly ${speed.fly} ft.`);
    if (speed.swim > 0) speeds.push(`swim ${speed.swim} ft.`);
    if (speed.climb > 0) speeds.push(`climb ${speed.climb} ft.`);
    if (speed.burrow > 0) speeds.push(`burrow ${speed.burrow} ft.`);
    return speeds.join(', ');
  };

  if (loading) {
    return (
      <div className="companion-selection-overlay">
        <div className="companion-selection-modal">
          <div className="loading">Loading companion templates...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="companion-selection-overlay">
      <div className="companion-selection-modal">
        <div className="modal-header">
          <h2>Select Animal Companion</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {step === 1 && (
          <div className="template-selection">
            <h3>Choose a Beast</h3>
            <div className="templates-grid">
              {Array.isArray(templates) && templates.length > 0 ? templates.map((template) => (
                <div
                  key={template.id}
                  className="template-card"
                  onClick={() => handleTemplateSelect(template)}
                >
                  <div className="template-header">
                    <h4>{template.name}</h4>
                    <span className="cr">CR {template.challenge_rating}</span>
                  </div>
                  <div className="template-stats">
                    <div className="stat-row">
                      <span>AC {template.armor_class}</span>
                      <span>{template.hit_points} HP</span>
                      <span>{template.size}</span>
                    </div>
                    <div className="speed">Speed: {getSpeedDisplay(template.speed)}</div>
                  </div>
                  <div className="abilities-row">
                    {Object.entries(template.abilities).map(([ability, score]) => (
                      <div key={ability} className="ability">
                        <span className="ability-name">{ability.toUpperCase()}</span>
                        <span className="ability-score">{score} ({formatModifier(getAbilityModifier(score))})</span>
                      </div>
                    ))}
                  </div>
                  <div className="template-description">
                    {template.description}
                  </div>
                  <div className="environment">
                    Environment: {template.environment}
                  </div>
                </div>
              )) : (
                <div className="no-templates">
                  {loading ? 'Loading companion templates...' : 'No companion templates available.'}
                </div>
              )}
            </div>
          </div>
        )}

        {step === 2 && selectedTemplate && (
          <div className="companion-customization">
            <div className="customization-header">
              <button className="back-btn" onClick={() => setStep(1)}>← Back</button>
              <h3>Customize Your {selectedTemplate.name}</h3>
            </div>

            <div className="customization-form">
              <div className="form-group">
                <label>Companion Name *</label>
                <input
                  type="text"
                  value={companionName}
                  onChange={(e) => setCompanionName(e.target.value)}
                  placeholder="Enter a name for your companion"
                  className="companion-name-input"
                />
              </div>

              <div className="form-group">
                <label>Personality Traits</label>
                <textarea
                  value={personalityTraits}
                  onChange={(e) => setPersonalityTraits(e.target.value)}
                  placeholder="Describe your companion's personality..."
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Backstory</label>
                <textarea
                  value={backstory}
                  onChange={(e) => setBackstory(e.target.value)}
                  placeholder="How did you meet this companion?"
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any additional notes..."
                  rows={2}
                />
              </div>

              <div className="selected-template-summary">
                <h4>Selected: {selectedTemplate.name}</h4>
                <div className="template-details">
                  <div className="basic-stats">
                    <span>CR {selectedTemplate.challenge_rating}</span>
                    <span>AC {selectedTemplate.armor_class}</span>
                    <span>{selectedTemplate.hit_points} HP</span>
                    <span>{selectedTemplate.size}</span>
                  </div>

                  {selectedTemplate.special_abilities.length > 0 && (
                    <div className="special-abilities">
                      <h5>Special Abilities:</h5>
                      {selectedTemplate.special_abilities.map((ability, index) => (
                        <div key={index} className="ability-item">
                          <strong>{ability.name}:</strong> {ability.description}
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedTemplate.attacks.length > 0 && (
                    <div className="attacks">
                      <h5>Attacks:</h5>
                      {selectedTemplate.attacks.map((attack, index) => (
                        <div key={index} className="attack-item">
                          <strong>{attack.name}:</strong> {formatModifier(attack.attack_bonus)} to hit,
                          {attack.damage} {attack.damage_type} damage, range {attack.range}
                          {attack.special && <span className="attack-special"> • {attack.special}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="form-actions">
                <button
                  className="create-companion-btn"
                  onClick={handleCreateCompanion}
                  disabled={creating || !companionName.trim()}
                >
                  {creating ? 'Creating...' : 'Create Companion'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}