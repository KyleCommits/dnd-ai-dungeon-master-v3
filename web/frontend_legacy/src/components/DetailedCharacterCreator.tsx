// web/frontend/src/components/DetailedCharacterCreator.tsx
import React, { useState, useEffect } from 'react';
import './DetailedCharacterCreator.css';

interface DetailedCharacterCreatorProps {
  onSubmit: (characterData: any) => void;
  onCancel: () => void;
  campaignId: number;
}

interface RaceVariant {
  ability_increases: Array<{ ability: string; amount: number }>;
  traits: Array<{ name: string; description: string }>;
  speed: number;
  size: string;
  extra_language: boolean;
  extra_skill: boolean;
  proficiencies: string[];
}

interface CharacterClass {
  hit_die: number;
  primary_abilities: string[];
  saving_throws: string[];
  armor_proficiencies: string[];
  weapon_proficiencies: string[];
  skill_choices: number;
  skill_list: string[];
  starting_equipment: any;
  spellcasting?: any;
  subclasses: { [key: string]: any };
  subclass_level: number;
  chooses_subclass_at_creation: boolean;
}

interface AbilityScores {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

const DetailedCharacterCreator: React.FC<DetailedCharacterCreatorProps> = ({
  onSubmit,
  onCancel,
  campaignId
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step data
  const [characterName, setCharacterName] = useState('');
  const [selectedRace, setSelectedRace] = useState<string>('');
  const [selectedVariant, setSelectedVariant] = useState<string>('');
  const [selectedClass, setSelectedClass] = useState<string>('');
  const [selectedSubclass, setSelectedSubclass] = useState<string>('');
  const [selectedBackground, setSelectedBackground] = useState<string>('');
  const [abilityScoreMethod, setAbilityScoreMethod] = useState<string>('');
  const [baseAbilities, setBaseAbilities] = useState<AbilityScores>({
    strength: 8, dexterity: 8, constitution: 8,
    intelligence: 8, wisdom: 8, charisma: 8
  });
  const [standardArrayValues] = useState([15, 14, 13, 12, 10, 8]);
  const [pointBuyPoints, setPointBuyPoints] = useState(27);
  const [rolledStats, setRolledStats] = useState<Array<Array<number>>>([]);
  const [finalAbilities, setFinalAbilities] = useState<AbilityScores>({
    strength: 8, dexterity: 8, constitution: 8,
    intelligence: 8, wisdom: 8, charisma: 8
  });
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedFeats, setSelectedFeats] = useState<string[]>([]);
  const [customAbilityChoices, setCustomAbilityChoices] = useState<{ [key: string]: number }>({});

  // Add keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't handle Enter if user is typing in an input field
      if (event.target && (event.target as HTMLElement).tagName === 'INPUT') {
        return;
      }

      if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        // Add small delay to allow state updates to complete
        setTimeout(() => {
          if (currentStep < 6) {
            nextStep();
          } else {
            handleSubmit();
          }
        }, 100);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        onCancel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [currentStep]);

  // API data
  const [availableRaces, setAvailableRaces] = useState<{ [key: string]: any }>({});
  const [availableClasses, setAvailableClasses] = useState<{ [key: string]: CharacterClass }>({});
  const [availableBackgrounds, setAvailableBackgrounds] = useState<{ [key: string]: any }>({});
  const [availableFeats, setAvailableFeats] = useState<{ [key: string]: any }>({});
  const [raceValidation, setRaceValidation] = useState<any>(null);
  const [characterStats, setCharacterStats] = useState<any>(null);
  const [customChoicesNeeded, setCustomChoicesNeeded] = useState<{ [key: string]: any }>({});

  // Load initial data
  useEffect(() => {
    const loadCharacterCreationData = async () => {
      setIsLoading(true);
      try {
        const [racesRes, classesRes, backgroundsRes, featsRes] = await Promise.all([
          fetch('http://localhost:8080/api/character-creation/races'),
          fetch('http://localhost:8080/api/character-creation/classes'),
          fetch('http://localhost:8080/api/character-creation/backgrounds'),
          fetch('http://localhost:8080/api/character-creation/feats')
        ]);

        const [races, classes, backgrounds, feats] = await Promise.all([
          racesRes.json(),
          classesRes.json(),
          backgroundsRes.json(),
          featsRes.json()
        ]);

        setAvailableRaces(races.races);
        setAvailableClasses(classes.classes);
        setAvailableBackgrounds(backgrounds.backgrounds);
        setAvailableFeats(feats.feats);
      } catch (err) {
        setError('Failed to load character creation data');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadCharacterCreationData();
  }, []);

  // Calculate final abilities when race/base abilities change
  useEffect(() => {
    if (selectedRace && selectedVariant && baseAbilities) {
      calculateFinalAbilities();
    }
  }, [selectedRace, selectedVariant, baseAbilities, customAbilityChoices]);

  // Handle ability score method changes
  useEffect(() => {
    if (abilityScoreMethod === 'standard_array') {
      applyStandardArray();
    } else if (abilityScoreMethod === 'point_buy') {
      resetToPointBuyDefaults();
    }
  }, [abilityScoreMethod]);

  // Validate race choice and get custom options
  useEffect(() => {
    const validateRaceChoice = async () => {
      if (selectedRace && selectedVariant) {
        try {
          const response = await fetch('http://localhost:8080/api/character-creation/validate-race-choice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              race: selectedRace,
              variant: selectedVariant,
              custom_ability_choices: customAbilityChoices
            })
          });

          if (response.ok) {
            const validation = await response.json();
            setRaceValidation(validation);
            setCustomChoicesNeeded(validation.custom_choices_needed || {});
          }
        } catch (error) {
          console.error('Race validation error:', error);
        }
      } else {
        setRaceValidation(null);
        setCustomChoicesNeeded({});
      }
    };

    validateRaceChoice();
  }, [selectedRace, selectedVariant, customAbilityChoices]);

  const calculateFinalAbilities = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/character-creation/calculate-final-abilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_scores: baseAbilities,
          race_choice: {
            race: selectedRace,
            variant: selectedVariant,
            custom_ability_choices: customAbilityChoices
          }
        })
      });

      if (response.ok) {
        const result = await response.json();
        setFinalAbilities(result.final_abilities);
      }
    } catch (err) {
      console.error('Error calculating final abilities:', err);
    }
  };


  const nextStep = async () => {
    // Basic validation
    if (currentStep === 1 && !characterName.trim()) {
      setError('Please enter a character name');
      return;
    }

    if (currentStep === 2 && (!selectedRace || !selectedVariant)) {
      setError('Please select a race and variant');
      return;
    }

    // Validate Human Variant requirements
    if (currentStep === 2 && selectedVariant === 'Variant Human') {
      const selectedAbilityCount = Object.values(customAbilityChoices).filter(v => v === 1).length;
      if (selectedAbilityCount < 2) {
        setError('Variant Human must choose 2 different ability score increases');
        return;
      }
      if (selectedFeats.length === 0) {
        setError('Variant Human must choose a feat');
        return;
      }
    }

    // Validate Custom Lineage requirements
    if (currentStep === 2 && selectedVariant === 'Custom Lineage') {
      const selectedAbilityCount = Object.values(customAbilityChoices).reduce((sum, val) => sum + val, 0);
      if (selectedAbilityCount === 0) {
        setError('Custom Lineage must choose ability score increases');
        return;
      }
      if (selectedFeats.length === 0) {
        setError('Custom Lineage must choose a feat');
        return;
      }
    }

    if (currentStep === 3 && !selectedClass) {
      setError('Please select a class');
      return;
    }

    if (currentStep === 4 && !abilityScoreMethod) {
      setError('Please select an ability score method');
      return;
    }

    if (currentStep === 5 && !selectedBackground) {
      setError('Please select a background');
      return;
    }

    setError(null);
    setCurrentStep(prev => prev + 1);
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(1, prev - 1));
    setError(null);
  };

  // Standard Array helper functions
  const applyStandardArray = () => {
    setBaseAbilities({
      strength: 15,
      dexterity: 14,
      constitution: 13,
      intelligence: 12,
      wisdom: 10,
      charisma: 8
    });
  };

  const handleStandardArrayAssignment = (ability: string, newValue: number) => {
    setBaseAbilities(prev => {
      // Find if another ability already has this value
      const currentAbilityWithValue = Object.entries(prev).find(
        ([abilityName, abilityValue]) => abilityName !== ability && abilityValue === newValue
      );

      if (currentAbilityWithValue) {
        // Swap the values
        const [otherAbility] = currentAbilityWithValue;
        const currentValue = prev[ability as keyof AbilityScores];

        return {
          ...prev,
          [ability]: newValue,
          [otherAbility]: currentValue
        };
      } else {
        // No conflict, just assign the value
        return {
          ...prev,
          [ability]: newValue
        };
      }
    });
  };

  // Point Buy helper functions
  const resetToPointBuyDefaults = () => {
    setBaseAbilities({
      strength: 8,
      dexterity: 8,
      constitution: 8,
      intelligence: 8,
      wisdom: 8,
      charisma: 8
    });
    setPointBuyPoints(27);
  };

  const calculatePointBuyCost = (score: number): number => {
    if (score <= 8) return 0;
    if (score <= 13) return score - 8;
    if (score === 14) return 7;
    if (score === 15) return 9;
    return 0;
  };

  const calculateTotalPointsUsed = (): number => {
    return Object.values(baseAbilities).reduce((total, score) => total + calculatePointBuyCost(score), 0);
  };

  const getPointsRemaining = (): number => {
    return 27 - calculateTotalPointsUsed();
  };

  const getNextPointCost = (currentScore: number): number => {
    if (currentScore < 13) return 1;
    if (currentScore === 13) return 2;
    if (currentScore === 14) return 2;
    return 0;
  };

  const adjustPointBuyScore = (ability: string, change: number) => {
    const currentScore = baseAbilities[ability as keyof AbilityScores];
    const newScore = currentScore + change;

    if (newScore < 8 || newScore > 15) return;

    const currentCost = calculatePointBuyCost(currentScore);
    const newCost = calculatePointBuyCost(newScore);
    const costDifference = newCost - currentCost;

    // Check if we have enough points remaining
    if (getPointsRemaining() - costDifference < 0) return;

    setBaseAbilities(prev => ({
      ...prev,
      [ability]: newScore
    }));
  };

  // Rolling helper functions
  const rollAbilityScores = () => {
    const newRolls: Array<Array<number>> = [];

    for (let i = 0; i < 6; i++) {
      // Roll 4d6, sort descending, take top 3
      const rolls = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1);
      rolls.sort((a, b) => b - a);
      newRolls.push(rolls);
    }

    setRolledStats(newRolls);

    // Auto-assign the first rolled set to abilities
    const totals = newRolls.map(roll => roll[0] + roll[1] + roll[2]);
    setBaseAbilities({
      strength: totals[0] || 8,
      dexterity: totals[1] || 8,
      constitution: totals[2] || 8,
      intelligence: totals[3] || 8,
      wisdom: totals[4] || 8,
      charisma: totals[5] || 8
    });
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      const characterData = {
        step1: { name: characterName, campaign_id: campaignId },
        step2: {
          race: selectedRace,
          variant: selectedVariant,
          custom_ability_choices: customAbilityChoices
        },
        step3: {
          class_name: selectedClass,
          subclass: selectedSubclass
        },
        step4: {
          method: abilityScoreMethod,
          base_scores: baseAbilities
        },
        step5: {
          background: selectedBackground,
          skill_choices: selectedSkills
        },
        step6: {
          feats: selectedFeats
        }
      };

      const response = await fetch('http://localhost:8080/api/character-creation/finalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(characterData)
      });

      if (response.ok) {
        const result = await response.json();
        onSubmit(result);
      } else {
        const error = await response.json();
        setError(error.detail?.message || 'Failed to create character');
      }
    } catch (err) {
      setError('Failed to create character');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const renderProgressBar = () => {
    const steps = ['Name', 'Race', 'Class', 'Abilities', 'Skills', 'Review'];
    return (
      <div className="progress-bar">
        {steps.map((step, index) => (
          <div
            key={index}
            className={`progress-step ${index + 1 <= currentStep ? 'completed' : ''} ${index + 1 === currentStep ? 'current' : ''}`}
          >
            <div className="step-number">{index + 1}</div>
            <div className="step-label">{step}</div>
          </div>
        ))}
      </div>
    );
  };

  const renderNameStep = () => (
    <div className="creation-step">
      <h3>Character Name</h3>
      <div className="form-group">
        <label>Enter your character's name:</label>
        <input
          type="text"
          value={characterName}
          onChange={(e) => setCharacterName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && characterName.trim()) {
              e.preventDefault();
              nextStep();
            }
          }}
          placeholder="e.g., Aragorn, Legolas, Gimli"
          maxLength={50}
        />
      </div>
    </div>
  );

  const renderRaceStep = () => (
    <div className="creation-step">
      <h3>Race & Variant</h3>

      <div className="form-group">
        <label>Race:</label>
        <select
          value={selectedRace}
          onChange={(e) => {
            setSelectedRace(e.target.value);
            setSelectedVariant('');
          }}
        >
          <option value="">Select Race</option>
          {Object.keys(availableRaces).map(race => (
            <option key={race} value={race}>{race}</option>
          ))}
        </select>
      </div>

      {selectedRace && (
        <div className="form-group">
          <label>Variant:</label>
          <select
            value={selectedVariant}
            onChange={(e) => setSelectedVariant(e.target.value)}
          >
            <option value="">Select Variant</option>
            {Object.keys(availableRaces[selectedRace]?.variants || {}).map(variant => (
              <option key={variant} value={variant}>{variant}</option>
            ))}
          </select>
        </div>
      )}

      {selectedRace && selectedVariant && (
        <div className="race-info">
          <h4>Racial Traits</h4>
          <div className="traits-list">
            {availableRaces[selectedRace]?.traits?.map((trait: any, index: number) => (
              <div key={index} className="trait-item">
                <strong>{trait.name}:</strong> {trait.description}
              </div>
            ))}
            {availableRaces[selectedRace]?.variants[selectedVariant]?.traits?.map((trait: any, index: number) => (
              <div key={`variant-${index}`} className="trait-item">
                <strong>{trait.name}:</strong> {trait.description}
              </div>
            ))}
          </div>

          <h4>Ability Score Increases</h4>
          <div className="ability-increases">
            {availableRaces[selectedRace]?.variants[selectedVariant]?.ability_increases?.map((increase: any, index: number) => (
              <span key={index} className="ability-increase">
                {increase.ability.toUpperCase()} +{increase.amount}
              </span>
            ))}
          </div>

          {/* Custom Ability Choice for Variant Human */}
          {customChoicesNeeded.ability_increases && (
            <div className="custom-ability-choice">
              <h4>Choose Ability Increases</h4>
              <p>{customChoicesNeeded.ability_increases.description}</p>
              {['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].map(ability => (
                <label key={ability} className="ability-choice">
                  <input
                    type="checkbox"
                    checked={customAbilityChoices[ability] === 1}
                    onChange={(e) => {
                      const newChoices = { ...customAbilityChoices };
                      if (e.target.checked) {
                        // Limit to 2 choices for Variant Human
                        const currentChoices = Object.values(newChoices).filter(v => v === 1).length;
                        if (currentChoices < (customChoicesNeeded.ability_increases.count || 2)) {
                          newChoices[ability] = 1;
                        }
                      } else {
                        delete newChoices[ability];
                      }
                      setCustomAbilityChoices(newChoices);
                    }}
                  />
                  {ability.charAt(0).toUpperCase() + ability.slice(1)}
                </label>
              ))}
            </div>
          )}

          {/* Feat Choice for Variant Human and Custom Lineage */}
          {customChoicesNeeded.feat_choice && (
            <div className="feat-choice">
              <h4>Choose a Feat</h4>
              <p>{customChoicesNeeded.feat_choice.description}</p>
              <select
                value={selectedFeats[0] || ''}
                onChange={(e) => setSelectedFeats(e.target.value ? [e.target.value] : [])}
              >
                <option value="">Select a Feat</option>
                {Object.keys(availableFeats).map(feat => (
                  <option key={feat} value={feat}>{feat}</option>
                ))}
              </select>
              {selectedFeats[0] && availableFeats[selectedFeats[0]] && (
                <div className="feat-description">
                  <strong>Benefits:</strong>
                  <ul>
                    {availableFeats[selectedFeats[0]].benefits?.map((benefit: string, index: number) => (
                      <li key={index}>{benefit}</li>
                    )) || <li>No benefits available</li>}
                  </ul>
                  {availableFeats[selectedFeats[0]].prerequisites?.length > 0 && (
                    <div>
                      <strong>Prerequisites:</strong> {availableFeats[selectedFeats[0]].prerequisites.join(', ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderClassStep = () => (
    <div className="creation-step">
      <h3>Class & Subclass</h3>

      <div className="form-group">
        <label>Class:</label>
        <select
          value={selectedClass}
          onChange={(e) => {
            setSelectedClass(e.target.value);
            setSelectedSubclass('');
          }}
        >
          <option value="">Select Class</option>
          {Object.keys(availableClasses).map(cls => (
            <option key={cls} value={cls}>{cls}</option>
          ))}
        </select>
      </div>

      {selectedClass && (
        <>
          <div className="class-info">
            <div className="class-details">
              <p><strong>Hit Die:</strong> d{availableClasses[selectedClass]?.hit_die}</p>
              <p><strong>Primary Abilities:</strong> {availableClasses[selectedClass]?.primary_abilities?.join(', ')}</p>
              <p><strong>Saving Throws:</strong> {availableClasses[selectedClass]?.saving_throws?.join(', ')}</p>
              <p><strong>Skill Choices:</strong> {availableClasses[selectedClass]?.skill_choices} from {availableClasses[selectedClass]?.skill_list?.length} skills</p>
            </div>
          </div>

          {/* Only show subclass selection for classes that choose at level 1 */}
          {availableClasses[selectedClass]?.chooses_subclass_at_creation && (
            <div className="form-group">
              <label>Subclass:</label>
              <select
                value={selectedSubclass}
                onChange={(e) => setSelectedSubclass(e.target.value)}
              >
                <option value="">Select Subclass</option>
                {Object.keys(availableClasses[selectedClass]?.subclasses || {}).map(subclass => (
                  <option key={subclass} value={subclass}>{subclass}</option>
                ))}
              </select>
              <small className="help-text">
                {selectedClass} chooses their subclass at 1st level.
              </small>
            </div>
          )}

          {/* Show info for classes that choose subclass later */}
          {!availableClasses[selectedClass]?.chooses_subclass_at_creation &&
           Object.keys(availableClasses[selectedClass]?.subclasses || {}).length > 0 && (
            <div className="subclass-info">
              <p className="info-text">
                <strong>Subclass Selection:</strong> {selectedClass} chooses their subclass at level {availableClasses[selectedClass]?.subclass_level || 3}.
              </p>
              <details className="subclass-preview">
                <summary>Preview Available Subclasses</summary>
                <ul className="subclass-list">
                  {Object.keys(availableClasses[selectedClass]?.subclasses || {}).map(subclass => (
                    <li key={subclass}>{subclass}</li>
                  ))}
                </ul>
              </details>
            </div>
          )}
        </>
      )}
    </div>
  );

  const renderAbilityStep = () => (
    <div className="creation-step">
      <h3>Ability Scores</h3>

      <div className="form-group">
        <label>Method:</label>
        <select
          value={abilityScoreMethod}
          onChange={(e) => {
            const method = e.target.value;
            setAbilityScoreMethod(method);
            if (method === 'standard_array') {
              applyStandardArray();
            } else if (method === 'point_buy') {
              resetToPointBuyDefaults();
            }
          }}
        >
          <option value="">Select Method</option>
          <option value="standard_array">Standard Array (15, 14, 13, 12, 10, 8)</option>
          <option value="point_buy">Point Buy (27 points)</option>
          <option value="roll">Roll 4d6 drop lowest</option>
          <option value="manual">Manual Entry</option>
        </select>
      </div>

      {abilityScoreMethod === 'standard_array' && (
        <div className="ability-scores-section">
          <div className="base-abilities">
            <h4>Standard Array Assignment</h4>
            <p>Assign these values to your abilities: {standardArrayValues.join(', ')}</p>
            <div className="abilities-grid">
              {Object.entries(baseAbilities).map(([ability, score]) => (
                <div key={ability} className="ability-input">
                  <label>{ability.toUpperCase()}</label>
                  <select
                    value={score}
                    onChange={(e) => handleStandardArrayAssignment(ability, parseInt(e.target.value))}
                  >
                    <option value="8">8</option>
                    {standardArrayValues.map(value => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {abilityScoreMethod === 'point_buy' && (
        <div className="ability-scores-section">
          <div className="base-abilities">
            <h4>Point Buy System</h4>
            <p>Points remaining: <strong>{getPointsRemaining()}</strong> / 27</p>
            <div className="abilities-grid">
              {Object.entries(baseAbilities).map(([ability, score]) => {
                const cost = calculatePointBuyCost(score);
                const canIncrease = score < 15 && getPointsRemaining() >= getNextPointCost(score);
                const canDecrease = score > 8;
                return (
                  <div key={ability} className="ability-input">
                    <label>{ability.toUpperCase()}</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <button
                        type="button"
                        onClick={() => adjustPointBuyScore(ability, -1)}
                        disabled={!canDecrease}
                        style={{ padding: '4px 8px' }}
                      >
                        -
                      </button>
                      <input
                        type="number"
                        value={score}
                        readOnly
                        style={{ width: '50px', textAlign: 'center' }}
                      />
                      <button
                        type="button"
                        onClick={() => adjustPointBuyScore(ability, 1)}
                        disabled={!canIncrease}
                        style={{ padding: '4px 8px' }}
                      >
                        +
                      </button>
                    </div>
                    <small>Total Cost: {cost}</small>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {abilityScoreMethod === 'roll' && (
        <div className="ability-scores-section">
          <div className="base-abilities">
            <h4>Roll for Ability Scores</h4>
            <div style={{ marginBottom: '20px' }}>
              <button
                type="button"
                onClick={rollAbilityScores}
                style={{
                  padding: '10px 20px',
                  marginRight: '10px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                {rolledStats.length === 0 ? 'Roll Ability Scores' : 'Re-roll All'}
              </button>
              {rolledStats.length > 0 && (
                <p>Click "Re-roll All" to roll again, or assign the rolled values below:</p>
              )}
            </div>

            {rolledStats.length > 0 && (
              <div>
                <h5>Rolled Results:</h5>
                <div style={{ display: 'flex', gap: '10px', marginBottom: '15px', flexWrap: 'wrap' }}>
                  {rolledStats.map((roll, index) => (
                    <div key={index} style={{
                      padding: '8px',
                      background: '#333',
                      borderRadius: '4px',
                      border: '1px solid #555'
                    }}>
                      <strong>{roll[0] + roll[1] + roll[2]}</strong>
                      <br />
                      <small style={{ color: '#aaa' }}>
                        [{roll.join(', ')}]
                        <span style={{ textDecoration: 'line-through', color: '#666' }}>
                          ({roll[3]})
                        </span>
                      </small>
                    </div>
                  ))}
                </div>

                <div className="abilities-grid">
                  {Object.entries(baseAbilities).map(([ability, score]) => (
                    <div key={ability} className="ability-input">
                      <label>{ability.toUpperCase()}</label>
                      <select
                        value={score}
                        onChange={(e) => setBaseAbilities(prev => ({
                          ...prev,
                          [ability]: parseInt(e.target.value)
                        }))}
                      >
                        <option value="8">8 (default)</option>
                        {rolledStats.map((roll, index) => {
                          const total = roll[0] + roll[1] + roll[2];
                          return (
                            <option key={index} value={total}>
                              {total}
                            </option>
                          );
                        })}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {abilityScoreMethod === 'manual' && (
        <div className="ability-scores-section">
          <div className="base-abilities">
            <h4>Manual Entry</h4>
            <div className="abilities-grid">
              {Object.entries(baseAbilities).map(([ability, score]) => (
                <div key={ability} className="ability-input">
                  <label>{ability.toUpperCase()}</label>
                  <input
                    type="number"
                    min="3"
                    max="18"
                    value={score}
                    onChange={(e) => setBaseAbilities(prev => ({
                      ...prev,
                      [ability]: parseInt(e.target.value) || 8
                    }))}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {abilityScoreMethod && (
        <div className="ability-scores-section">
          <div className="final-abilities">
            <h4>Final Ability Scores (with racial bonuses)</h4>
            <div className="abilities-grid">
              {Object.entries(finalAbilities).map(([ability, score]) => {
                const modifier = Math.floor((score - 10) / 2);
                const change = score - baseAbilities[ability as keyof AbilityScores];
                return (
                  <div key={ability} className="ability-display">
                    <label>{ability.toUpperCase()}</label>
                    <div className="ability-value">
                      {score} ({modifier >= 0 ? '+' : ''}{modifier})
                      {change > 0 && <span className="racial-bonus"> (+{change})</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderSkillsStep = () => (
    <div className="creation-step">
      <h3>Background & Skills</h3>

      <div className="form-group">
        <label>Background:</label>
        <select
          value={selectedBackground}
          onChange={(e) => setSelectedBackground(e.target.value)}
        >
          <option value="">Select Background</option>
          {Object.keys(availableBackgrounds).map(bg => (
            <option key={bg} value={bg}>{bg}</option>
          ))}
        </select>
      </div>

      {selectedBackground && (
        <div className="background-info">
          <h4>Background Benefits</h4>
          <p><strong>Skills:</strong> {availableBackgrounds[selectedBackground]?.skills?.join(', ')}</p>
          <p><strong>Languages:</strong> {availableBackgrounds[selectedBackground]?.languages || 0}</p>
          <p><strong>Feature:</strong> {availableBackgrounds[selectedBackground]?.feature}</p>
        </div>
      )}

      {selectedClass && (
        <div className="skill-selection">
          <h4>Class Skill Choices</h4>
          <p>Choose {availableClasses[selectedClass]?.skill_choices} skills from: {availableClasses[selectedClass]?.skill_list?.join(', ')}</p>
          <div className="skills-grid">
            {availableClasses[selectedClass]?.skill_list?.map(skill => (
              <label key={skill} className="skill-checkbox">
                <input
                  type="checkbox"
                  checked={selectedSkills.includes(skill)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      if (selectedSkills.length < (availableClasses[selectedClass]?.skill_choices || 0)) {
                        setSelectedSkills(prev => [...prev, skill]);
                      }
                    } else {
                      setSelectedSkills(prev => prev.filter(s => s !== skill));
                    }
                  }}
                  disabled={!selectedSkills.includes(skill) && selectedSkills.length >= (availableClasses[selectedClass]?.skill_choices || 0)}
                />
                {skill}
              </label>
            ))}
          </div>
          <p>{selectedSkills.length}/{availableClasses[selectedClass]?.skill_choices} selected</p>
        </div>
      )}
    </div>
  );

  const renderReviewStep = () => (
    <div className="creation-step">
      <h3>Character Review</h3>

      <div className="character-summary">
        <div className="summary-section">
          <h4>{characterName}</h4>
          <p>{selectedRace} ({selectedVariant}) {selectedClass}</p>
          {selectedSubclass && <p>Subclass: {selectedSubclass}</p>}
          <p>Background: {selectedBackground}</p>
        </div>

        <div className="summary-section">
          <h4>Ability Scores</h4>
          <div className="abilities-summary">
            {Object.entries(finalAbilities).map(([ability, score]) => {
              const modifier = Math.floor((score - 10) / 2);
              return (
                <div key={ability} className="ability-summary">
                  <span className="ability-name">{ability.toUpperCase()}</span>
                  <span className="ability-score">{score} ({modifier >= 0 ? '+' : ''}{modifier})</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="summary-section">
          <h4>Skills</h4>
          <p>{selectedSkills.join(', ')}</p>
        </div>

        {selectedFeats.length > 0 && (
          <div className="summary-section">
            <h4>Feats</h4>
            <p>{selectedFeats.join(', ')}</p>
          </div>
        )}
      </div>
    </div>
  );

  if (isLoading && currentStep === 1) {
    return (
      <div className="character-creator-loading">
        <div className="loading-spinner"></div>
        <p>Loading character creation options...</p>
      </div>
    );
  }

  const renderProgressSummary = () => (
    <div className="progress-summary">
      <h3>Character Progress</h3>

      {/* Character Name */}
      {characterName && (
        <div className="summary-section">
          <h4>Character Name</h4>
          <p className="summary-value">{characterName}</p>
        </div>
      )}

      {/* Race & Variant */}
      {selectedRace && selectedVariant && (
        <div className="summary-section">
          <h4>Race & Variant</h4>
          <p className="summary-value">{selectedVariant} ({selectedRace})</p>

          {availableRaces[selectedRace]?.variants[selectedVariant]?.ability_increases && (
            <div className="ability-bonuses">
              <strong>Ability Bonuses:</strong>
              {availableRaces[selectedRace].variants[selectedVariant].ability_increases.map((inc: any, idx: number) => (
                <span key={idx} className="bonus-tag">
                  {inc.ability.toUpperCase()} +{inc.amount}
                </span>
              ))}
            </div>
          )}

          <div className="race-details">
            <span className="detail">Speed: {availableRaces[selectedRace]?.base_speed || 30} ft</span>
            <span className="detail">Size: {availableRaces[selectedRace]?.size || 'Medium'}</span>
          </div>
        </div>
      )}

      {/* Class */}
      {selectedClass && (
        <div className="summary-section">
          <h4>Class{selectedSubclass ? ' & Subclass' : ''}</h4>
          <p className="summary-value">
            {selectedClass}
            {selectedSubclass && ` (${selectedSubclass})`}
          </p>

          <div className="class-details">
            <span className="detail">Hit Die: d{availableClasses[selectedClass]?.hit_die}</span>
            <span className="detail">
              Primary: {availableClasses[selectedClass]?.primary_abilities?.join(', ')}
            </span>
          </div>

          {!availableClasses[selectedClass]?.chooses_subclass_at_creation && (
            <p className="subclass-note">
              Subclass at level {availableClasses[selectedClass]?.subclass_level || 3}
            </p>
          )}
        </div>
      )}

      {/* Ability Scores */}
      {abilityScoreMethod && (
        <div className="summary-section">
          <h4>Ability Scores</h4>
          <p className="method-info">Method: {abilityScoreMethod.replace('_', ' ')}</p>

          <div className="ability-summary-grid">
            {Object.entries(finalAbilities).map(([ability, score]) => {
              const modifier = Math.floor((score - 10) / 2);
              const racialBonus = score - baseAbilities[ability as keyof AbilityScores];

              return (
                <div key={ability} className="ability-summary-item">
                  <div className="ability-name">{ability.substring(0, 3).toUpperCase()}</div>
                  <div className="ability-score">
                    {score} ({modifier >= 0 ? '+' : ''}{modifier})
                  </div>
                  {racialBonus > 0 && (
                    <div className="racial-bonus">+{racialBonus}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Background */}
      {selectedBackground && (
        <div className="summary-section">
          <h4>Background</h4>
          <p className="summary-value">{selectedBackground}</p>

          {availableBackgrounds[selectedBackground]?.skills && (
            <div className="background-skills">
              <strong>Background Skills:</strong> {availableBackgrounds[selectedBackground].skills.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Selected Skills */}
      {selectedSkills.length > 0 && (
        <div className="summary-section">
          <h4>Class Skills</h4>
          <p className="summary-value">{selectedSkills.join(', ')}</p>
          <p className="skill-count">{selectedSkills.length}/{availableClasses[selectedClass]?.skill_choices} selected</p>
        </div>
      )}

      {/* Feats */}
      {selectedFeats.length > 0 && (
        <div className="summary-section">
          <h4>Feats</h4>
          <p className="summary-value">{selectedFeats.join(', ')}</p>
        </div>
      )}

      {/* Derived Stats */}
      {selectedClass && finalAbilities.constitution && (
        <div className="summary-section derived-stats">
          <h4>Character Stats</h4>
          <div className="stats-grid">
            <div className="stat">
              <span className="stat-label">Hit Points:</span>
              <span className="stat-value">
                {(availableClasses[selectedClass]?.hit_die || 8) + Math.floor((finalAbilities.constitution - 10) / 2)}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Armor Class:</span>
              <span className="stat-value">
                {10 + Math.floor((finalAbilities.dexterity - 10) / 2)}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Speed:</span>
              <span className="stat-value">{availableRaces[selectedRace]?.base_speed || 30} ft</span>
            </div>
            <div className="stat">
              <span className="stat-label">Prof. Bonus:</span>
              <span className="stat-value">+2</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="detailed-character-creator">
      <div className="creator-header">
        <h2>Create New Character</h2>
        {renderProgressBar()}
      </div>

      <div className="creator-layout">
        <div className="creator-content">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {currentStep === 1 && renderNameStep()}
          {currentStep === 2 && renderRaceStep()}
          {currentStep === 3 && renderClassStep()}
          {currentStep === 4 && renderAbilityStep()}
          {currentStep === 5 && renderSkillsStep()}
          {currentStep === 6 && renderReviewStep()}
        </div>

        <div className="creator-sidebar">
          {renderProgressSummary()}
        </div>
      </div>

      <div className="creator-actions">
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

        {currentStep < 6 ? (
          <button
            onClick={nextStep}
            className="next-button"
            disabled={isLoading}
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            className="submit-button"
            disabled={isLoading}
          >
            {isLoading ? 'Creating...' : 'Create Character'}
          </button>
        )}
      </div>
    </div>
  );
};

export default DetailedCharacterCreator;