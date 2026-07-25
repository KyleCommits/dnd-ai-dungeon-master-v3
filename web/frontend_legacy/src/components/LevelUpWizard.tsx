import React, { useState, useEffect } from 'react';
import './LevelUpWizard.css';

interface LevelUpWizardProps {
  character: any;
  onComplete: (updatedCharacter: any) => void;
  onCancel: () => void;
}

interface Feature {
  name: string;
  description: string;
  choices?: string[];
  choice?: string;
  requires_choice?: boolean;
  choice_type?: 'archetype' | 'tradition' | 'domain' | 'path' | 'college' | 'circle' | 'oath' | 'patron' | 'origin' | 'specialist';
}

interface LevelUpOptions {
  hp_gain_options: number[];
  features: Feature[];
  spells_learned?: any[];
  asi_or_feat?: boolean;
  subclass_choice?: any;
}

interface LevelUpSelections {
  hp_gain: number;
  selected_features: Feature[];
  ability_score_improvements: { [key: string]: number };
  selected_feat: string;
  selected_spells: any[];
  selected_subclass: string;
  subclass_choices: { [key: string]: string };
  asi_choice_type: 'abilities' | 'feat' | '';
}

const LevelUpWizard: React.FC<LevelUpWizardProps> = ({ character, onComplete, onCancel }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [levelUpOptions, setLevelUpOptions] = useState<LevelUpOptions | null>(null);
  const [selections, setSelections] = useState<LevelUpSelections>({
    hp_gain: 0,
    selected_features: [],
    ability_score_improvements: {},
    selected_feat: '',
    selected_spells: [],
    selected_subclass: '',
    subclass_choices: {},
    asi_choice_type: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const newLevel = character.level + 1;

  useEffect(() => {
    fetchLevelUpOptions();
  }, []);

  const fetchLevelUpOptions = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8080/api/characters/${character.id}/level-up-options`, {
        method: 'GET'
      });

      if (response.ok) {
        const options = await response.json();
        setLevelUpOptions(options);
        // Auto-select average HP gain
        if (options.hp_gain_options && options.hp_gain_options.length > 0) {
          const averageHp = Math.ceil(options.hp_gain_options.reduce((a: number, b: number) => a + b, 0) / options.hp_gain_options.length);
          setSelections(prev => ({ ...prev, hp_gain: averageHp }));
        }
      } else {
        setError('Failed to load level up options');
      }
    } catch (err) {
      setError('Error loading level up options');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const rollHpGain = () => {
    if (!levelUpOptions?.hp_gain_options) return;

    // Simulate rolling hit die + CON modifier
    const hitDie = levelUpOptions.hp_gain_options[0]; // Assuming first option is the rolled value
    const roll = Math.floor(Math.random() * hitDie) + 1;
    const conModifier = Math.floor(((character.abilities?.constitution || 10) - 10) / 2);
    const totalGain = Math.max(1, roll + conModifier); // Minimum 1 HP gain

    setSelections(prev => ({ ...prev, hp_gain: totalGain }));
  };

  const nextStep = () => {
    if (currentStep < getTotalSteps()) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const getTotalSteps = () => {
    let steps = 2; // HP and Summary
    if (levelUpOptions?.features && levelUpOptions.features.length > 0) steps++;
    if (levelUpOptions?.asi_or_feat) steps++;
    if (levelUpOptions?.spells_learned && levelUpOptions.spells_learned.length > 0) steps++;
    if (levelUpOptions?.subclass_choice) steps++;
    return steps;
  };

  const handleLevelUp = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8080/api/characters/${character.id}/level-up`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hp_gain: selections.hp_gain,
          selected_features: selections.selected_features,
          ability_score_improvements: selections.ability_score_improvements,
          selected_feat: selections.selected_feat,
          selected_spells: selections.selected_spells,
          selected_subclass: selections.selected_subclass,
          subclass_choices: selections.subclass_choices
        })
      });

      if (response.ok) {
        const updatedCharacter = await response.json();
        onComplete(updatedCharacter);
      } else {
        const errorData = await response.json();
        setError(errorData.detail?.message || 'Failed to level up character');
      }
    } catch (err) {
      setError('Error leveling up character');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const renderHpStep = () => (
    <div className="level-up-step">
      <h3>Hit Points</h3>
      <div className="hp-section">
        <p>Choose how to increase your hit points for level {newLevel}:</p>

        <div className="hp-options">
          <div className="hp-option">
            <label>Roll Hit Die + CON Modifier</label>
            <div className="hp-roll-section">
              <button onClick={rollHpGain} className="roll-hp-button">
                🎲 Roll for HP
              </button>
              <div className="hp-calculation">
                d{levelUpOptions?.hp_gain_options[0] || 8} + {Math.floor(((character.abilities?.constitution || 10) - 10) / 2)} (CON)
              </div>
            </div>
          </div>

          <div className="hp-option">
            <label>Take Average</label>
            <div className="hp-average">
              {levelUpOptions?.hp_gain_options && levelUpOptions.hp_gain_options.length > 1
                ? levelUpOptions.hp_gain_options[1]
                : Math.ceil((levelUpOptions?.hp_gain_options[0] || 8) / 2) + 1
              } HP (Average)
              <button
                onClick={() => setSelections(prev => ({
                  ...prev,
                  hp_gain: levelUpOptions?.hp_gain_options[1] || Math.ceil((levelUpOptions?.hp_gain_options[0] || 8) / 2) + 1
                }))}
                className="select-average-button"
              >
                Select Average
              </button>
            </div>
          </div>

          <div className="hp-option">
            <label>Manual Entry</label>
            <input
              type="number"
              min="1"
              max="20"
              value={selections.hp_gain}
              onChange={(e) => setSelections(prev => ({ ...prev, hp_gain: parseInt(e.target.value) || 1 }))}
              className="hp-manual-input"
            />
          </div>
        </div>

        <div className="hp-result">
          <strong>HP Gain: {selections.hp_gain}</strong>
          <div className="hp-totals">
            Current: {character.max_hp} → New: {character.max_hp + selections.hp_gain}
          </div>
        </div>
      </div>
    </div>
  );

  const renderFeaturesStep = () => (
    <div className="level-up-step">
      <h3>Class Features</h3>
      <div className="features-section">
        <p>You gain the following features at level {newLevel}:</p>

        <div className="features-list">
          {levelUpOptions?.features.map((feature, index) => (
            <div key={index} className="feature-item">
              <h4>{feature.name}</h4>
              <p>{feature.description}</p>

              {/* Handle subclass choices */}
              {feature.requires_choice && feature.choices && (
                <div className="feature-choices">
                  <label>Choose your {feature.choice_type}:</label>
                  <select
                    value={selections.subclass_choices[feature.choice_type || 'default'] || ''}
                    onChange={(e) => {
                      const choiceType = feature.choice_type || 'default';
                      setSelections(prev => ({
                        ...prev,
                        subclass_choices: {
                          ...prev.subclass_choices,
                          [choiceType]: e.target.value
                        }
                      }));
                    }}
                    className="subclass-select"
                  >
                    <option value="">Select {feature.choice_type}...</option>
                    {feature.choices.map((choice: string, idx: number) => (
                      <option key={idx} value={choice}>{choice}</option>
                    ))}
                  </select>

                  {/* Show selected choice confirmation */}
                  {selections.subclass_choices[feature.choice_type || 'default'] && (
                    <div className="choice-confirmation">
                      ✓ Selected: <strong>{selections.subclass_choices[feature.choice_type || 'default']}</strong>
                    </div>
                  )}
                </div>
              )}

              {/* Handle other feature choices (non-subclass) */}
              {!feature.requires_choice && feature.choices && (
                <div className="feature-choices">
                  <label>Choose:</label>
                  <select
                    onChange={(e) => {
                      const newFeatures = [...selections.selected_features];
                      const updatedFeature: Feature = { ...feature, choice: e.target.value };
                      newFeatures[index] = updatedFeature;
                      setSelections(prev => ({ ...prev, selected_features: newFeatures }));
                    }}
                  >
                    <option value="">Select option...</option>
                    {feature.choices.map((choice: string, idx: number) => (
                      <option key={idx} value={choice}>{choice}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderASIStep = () => (
    <div className="level-up-step">
      <h3>Ability Score Improvement</h3>
      <div className="asi-section">
        <p>Choose to increase ability scores or take a feat:</p>

        <div className="asi-options">
          <div className="asi-option">
            <label>
              <input
                type="radio"
                name="asiChoice"
                value="abilities"
                checked={selections.asi_choice_type === 'abilities'}
                onChange={() => setSelections(prev => ({
                  ...prev,
                  selected_feat: '',
                  asi_choice_type: 'abilities'
                }))}
              />
              Increase Ability Scores (2 points total)
            </label>

            <div className="ability-improvements">
              {['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].map(ability => (
                <div key={ability} className="ability-improvement">
                  <span>{ability.toUpperCase()}: {character.abilities?.[ability] || 10}</span>
                  <div className="ability-controls">
                    <button
                      onClick={() => {
                        const current = selections.ability_score_improvements[ability] || 0;
                        if (current > 0) {
                          setSelections(prev => ({
                            ...prev,
                            ability_score_improvements: {
                              ...prev.ability_score_improvements,
                              [ability]: current - 1
                            }
                          }));
                        }
                      }}
                      disabled={!selections.ability_score_improvements[ability] || selections.asi_choice_type === 'feat'}
                    >
                      -
                    </button>
                    <span>{selections.ability_score_improvements[ability] || 0}</span>
                    <button
                      onClick={() => {
                        const totalUsed = Object.values(selections.ability_score_improvements).reduce((sum: number, val: any) => sum + (val || 0), 0);
                        const currentAbility = character.abilities?.[ability] || 10;
                        const currentIncrease = selections.ability_score_improvements[ability] || 0;

                        if (totalUsed < 2 && currentAbility + currentIncrease < 20) {
                          setSelections(prev => ({
                            ...prev,
                            ability_score_improvements: {
                              ...prev.ability_score_improvements,
                              [ability]: currentIncrease + 1
                            }
                          }));
                        }
                      }}
                      disabled={
                        Object.values(selections.ability_score_improvements).reduce((sum: number, val: any) => sum + (val || 0), 0) >= 2 ||
                        (character.abilities?.[ability] || 10) + (selections.ability_score_improvements[ability] || 0) >= 20 ||
                        selections.asi_choice_type === 'feat'
                      }
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="asi-option">
            <label>
              <input
                type="radio"
                name="asiChoice"
                value="feat"
                checked={selections.asi_choice_type === 'feat'}
                onChange={() => setSelections(prev => ({
                  ...prev,
                  ability_score_improvements: {},
                  asi_choice_type: 'feat'
                }))}
              />
              Take a Feat
            </label>

            <select
              value={selections.selected_feat}
              onChange={(e) => setSelections(prev => ({
                ...prev,
                selected_feat: e.target.value,
                asi_choice_type: e.target.value ? 'feat' : ''
              }))}
              disabled={false}
            >
              <option value="">Select a feat...</option>
              <option value="Actor">Actor</option>
              <option value="Alert">Alert</option>
              <option value="Artificer Initiate">Artificer Initiate</option>
              <option value="Athlete">Athlete</option>
              <option value="Bountiful Luck">Bountiful Luck</option>
              <option value="Charger">Charger</option>
              <option value="Chef">Chef</option>
              <option value="Crossbow Expert">Crossbow Expert</option>
              <option value="Crusher">Crusher</option>
              <option value="Defensive Duelist">Defensive Duelist</option>
              <option value="Dragon Fear">Dragon Fear</option>
              <option value="Dragon Hide">Dragon Hide</option>
              <option value="Dual Wielder">Dual Wielder</option>
              <option value="Dungeon Delver">Dungeon Delver</option>
              <option value="Durable">Durable</option>
              <option value="Dwarven Fortitude">Dwarven Fortitude</option>
              <option value="Eldritch Adept">Eldritch Adept</option>
              <option value="Elemental Adept">Elemental Adept</option>
              <option value="Elven Accuracy">Elven Accuracy</option>
              <option value="Fade Away">Fade Away</option>
              <option value="Fey Teleportation">Fey Teleportation</option>
              <option value="Fey Touched">Fey Touched</option>
              <option value="Fighting Initiate">Fighting Initiate</option>
              <option value="Flames of Phlegethos">Flames of Phlegethos</option>
              <option value="Grappler">Grappler</option>
              <option value="Great Weapon Master">Great Weapon Master</option>
              <option value="Gunner">Gunner</option>
              <option value="Healer">Healer</option>
              <option value="Heavily Armored">Heavily Armored</option>
              <option value="Heavy Armor Master">Heavy Armor Master</option>
              <option value="Infernal Constitution">Infernal Constitution</option>
              <option value="Inspiring Leader">Inspiring Leader</option>
              <option value="Keen Mind">Keen Mind</option>
              <option value="Lightly Armored">Lightly Armored</option>
              <option value="Linguist">Linguist</option>
              <option value="Lucky">Lucky</option>
              <option value="Mage Slayer">Mage Slayer</option>
              <option value="Magic Initiate">Magic Initiate</option>
              <option value="Martial Adept">Martial Adept</option>
              <option value="Medium Armor Master">Medium Armor Master</option>
              <option value="Metamagic Adept">Metamagic Adept</option>
              <option value="Mobile">Mobile</option>
              <option value="Moderately Armored">Moderately Armored</option>
              <option value="Mounted Combatant">Mounted Combatant</option>
              <option value="Observant">Observant</option>
              <option value="Orcish Fury">Orcish Fury</option>
              <option value="Piercer">Piercer</option>
              <option value="Poisoner">Poisoner</option>
              <option value="Polearm Master">Polearm Master</option>
              <option value="Prodigy">Prodigy</option>
              <option value="Resilient">Resilient</option>
              <option value="Ritual Caster">Ritual Caster</option>
              <option value="Savage Attacker">Savage Attacker</option>
              <option value="Second Chance">Second Chance</option>
              <option value="Sentinel">Sentinel</option>
              <option value="Shadow Touched">Shadow Touched</option>
              <option value="Sharpshooter">Sharpshooter</option>
              <option value="Shield Master">Shield Master</option>
              <option value="Shield Training">Shield Training</option>
              <option value="Skill Expert">Skill Expert</option>
              <option value="Skilled">Skilled</option>
              <option value="Skulker">Skulker</option>
              <option value="Slasher">Slasher</option>
              <option value="Spell Sniper">Spell Sniper</option>
              <option value="Squat Nimbleness">Squat Nimbleness</option>
              <option value="Tavern Brawler">Tavern Brawler</option>
              <option value="Telekinetic">Telekinetic</option>
              <option value="Telepathic">Telepathic</option>
              <option value="Tough">Tough</option>
              <option value="War Caster">War Caster</option>
              <option value="Weapon Master">Weapon Master</option>
              <option value="Wood Elf Magic">Wood Elf Magic</option>
            </select>
          </div>
        </div>

        <div className="asi-summary">
          {selections.asi_choice_type === 'feat' ? (
            selections.selected_feat ? `Selected Feat: ${selections.selected_feat}` : 'Please select a feat from the dropdown'
          ) : (
            `Points used: ${Object.values(selections.ability_score_improvements).reduce((sum: number, val: any) => sum + (val || 0), 0)} / 2`
          )}
        </div>
      </div>
    </div>
  );

  const renderSummaryStep = () => (
    <div className="level-up-step">
      <h3>Level Up Summary</h3>
      <div className="summary-section">
        <div className="character-progress">
          <h4>{character.name}</h4>
          <p>Level {character.level} → {newLevel}</p>
          <p>HP: {character.max_hp} → {character.max_hp + selections.hp_gain}</p>
        </div>

        <div className="summary-details">
          <div className="summary-item">
            <strong>Hit Points:</strong> +{selections.hp_gain}
          </div>

          {Object.keys(selections.ability_score_improvements).length > 0 && (
            <div className="summary-item">
              <strong>Ability Improvements:</strong>
              {Object.entries(selections.ability_score_improvements).map(([ability, increase]: [string, any]) => (
                increase > 0 && <span key={ability}> {ability.toUpperCase()} +{increase}</span>
              ))}
            </div>
          )}

          {selections.selected_feat && (
            <div className="summary-item">
              <strong>Feat:</strong> {selections.selected_feat}
            </div>
          )}

          {Object.keys(selections.subclass_choices).length > 0 && (
            <div className="summary-item">
              <strong>Subclass Choices:</strong>
              {Object.entries(selections.subclass_choices).map(([choiceType, choice]) => (
                <div key={choiceType}>
                  {choiceType.charAt(0).toUpperCase() + choiceType.slice(1)}: <span>{choice}</span>
                </div>
              ))}
            </div>
          )}

          {levelUpOptions?.features && levelUpOptions.features.length > 0 && (
            <div className="summary-item">
              <strong>New Features:</strong>
              <ul>
                {levelUpOptions.features.map((feature, index) => {
                  // For subclass choices, show the actual selection
                  if (feature.requires_choice && feature.choice_type && selections.subclass_choices[feature.choice_type]) {
                    return (
                      <li key={index}>
                        {selections.subclass_choices[feature.choice_type]}
                      </li>
                    );
                  }
                  // For regular features, show the name
                  return <li key={index}>{feature.name}</li>;
                })}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (isLoading && !levelUpOptions) {
    return (
      <div className="level-up-wizard loading">
        <div className="loading-spinner"></div>
        <p>Loading level up options...</p>
      </div>
    );
  }

  return (
    <div className="level-up-wizard">
      <div className="wizard-header">
        <h2>Level Up: {character.name}</h2>
        <div className="level-progress">
          Level {character.level} → {newLevel}
        </div>
        <div className="step-indicator">
          Step {currentStep} of {getTotalSteps()}
        </div>
      </div>

      <div className="wizard-content">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {currentStep === 1 && renderHpStep()}
        {currentStep === 2 && levelUpOptions?.features && renderFeaturesStep()}
        {currentStep === (levelUpOptions?.features ? 3 : 2) && levelUpOptions?.asi_or_feat && renderASIStep()}
        {currentStep === getTotalSteps() && renderSummaryStep()}
      </div>

      <div className="wizard-actions">
        <button
          onClick={onCancel}
          className="cancel-button"
          disabled={isLoading}
        >
          Cancel
        </button>

        {currentStep > 1 && (
          <button
            onClick={prevStep}
            className="prev-button"
            disabled={isLoading}
          >
            Previous
          </button>
        )}

        {currentStep < getTotalSteps() ? (
          <button
            onClick={nextStep}
            className="next-button"
            disabled={isLoading}
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleLevelUp}
            className="complete-button"
            disabled={isLoading}
          >
            {isLoading ? 'Leveling Up...' : 'Complete Level Up'}
          </button>
        )}
      </div>
    </div>
  );
};

export default LevelUpWizard;