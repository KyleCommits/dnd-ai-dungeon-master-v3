// web/src/components/CharacterCreationSummary.tsx
import React from 'react';

interface AbilityScores {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

interface AbilityModifiers {
  [key: string]: number;
}

interface RaceSelection {
  race: string;
  variant: string;
  speed: number;
  size: string;
  languages: string[];
  ability_increases: Array<{ability: string; amount: number}>;
  traits: Array<{name: string; description: string}>;
}

interface ClassSelection {
  class_name: string;
  subclass?: string;
  hit_die: number;
  primary_abilities: string[];
  saving_throws: string[];
  skill_choices: number;
  subclass_level: number;
  chooses_subclass_now: boolean;
  spellcasting?: any;
}

interface AbilitySelection {
  method: string;
  base_scores: AbilityScores;
  final_scores: AbilityScores;
  modifiers: AbilityModifiers;
  racial_bonuses: AbilityScores;
}

interface BackgroundSelection {
  background: string;
  skill_choices: string[];
  languages: string[];
  tools: string[];
}

interface FinalSelection {
  feats: string[];
  additional_asi: {[key: string]: number};
  equipment: {[key: string]: string};
}

interface DerivedStats {
  hit_points: {average: number; maximum: number};
  armor_class: number;
  proficiency_bonus: number;
  speed: number;
}

interface CharacterCreationSummaryData {
  current_step: number;
  completed_steps: number[];
  selections: {
    name?: string;
    campaign_id?: number;
    race?: RaceSelection;
    class?: ClassSelection;
    abilities?: AbilitySelection;
    background?: BackgroundSelection;
    final?: FinalSelection;
  };
  derived_stats?: DerivedStats;
}

interface CharacterCreationSummaryProps {
  summary: CharacterCreationSummaryData;
  currentStep: number;
}

const CharacterCreationSummary: React.FC<CharacterCreationSummaryProps> = ({
  summary,
  currentStep
}) => {
  const formatModifier = (modifier: number): string => {
    return modifier >= 0 ? `+${modifier}` : `${modifier}`;
  };

  const getStepTitle = (step: number): string => {
    const titles = {
      1: "Basic Info",
      2: "Race & Variant",
      3: "Class",
      4: "Ability Scores",
      5: "Background & Skills",
      6: "Feats & Final"
    };
    return titles[step as keyof typeof titles] || `Step ${step}`;
  };

  const getStepStatus = (step: number): string => {
    if (summary.completed_steps.includes(step)) return "completed";
    if (step === currentStep) return "current";
    return "pending";
  };

  return (
    <div className="character-creation-summary">
      <div className="summary-header">
        <h3>Character Creation Progress</h3>
        <div className="progress-steps">
          {[1, 2, 3, 4, 5, 6].map(step => (
            <div
              key={step}
              className={`step-indicator ${getStepStatus(step)}`}
              title={getStepTitle(step)}
            >
              {step}
            </div>
          ))}
        </div>
      </div>

      <div className="summary-content">
        {/* Basic Info */}
        {summary.selections.name && (
          <div className="selection-section">
            <h4>Character Name</h4>
            <p className="selection-value">{summary.selections.name}</p>
          </div>
        )}

        {/* Race Selection */}
        {summary.selections.race && (
          <div className="selection-section">
            <h4>Race & Variant</h4>
            <div className="race-info">
              <p className="selection-value">
                {summary.selections.race.variant} ({summary.selections.race.race})
              </p>
              <div className="race-details">
                <span className="detail">Size: {summary.selections.race.size}</span>
                <span className="detail">Speed: {summary.selections.race.speed} ft</span>
                <span className="detail">Languages: {summary.selections.race.languages.join(', ')}</span>
              </div>
              {summary.selections.race.ability_increases.length > 0 && (
                <div className="ability-increases">
                  <strong>Ability Score Increases:</strong>
                  {summary.selections.race.ability_increases.map((inc, idx) => (
                    <span key={idx} className="ability-bonus">
                      {inc.ability.charAt(0).toUpperCase() + inc.ability.slice(1)} +{inc.amount}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Class Selection */}
        {summary.selections.class && (
          <div className="selection-section">
            <h4>Class{summary.selections.class.subclass ? ' & Subclass' : ''}</h4>
            <div className="class-info">
              <p className="selection-value">
                {summary.selections.class.class_name}
                {summary.selections.class.subclass && ` (${summary.selections.class.subclass})`}
              </p>
              <div className="class-details">
                <span className="detail">Hit Die: d{summary.selections.class.hit_die}</span>
                <span className="detail">
                  Primary: {summary.selections.class.primary_abilities.join(', ')}
                </span>
                <span className="detail">
                  Saves: {summary.selections.class.saving_throws.join(', ')}
                </span>
              </div>
              {!summary.selections.class.chooses_subclass_now && (
                <p className="subclass-note">
                  Subclass chosen at level {summary.selections.class.subclass_level}
                </p>
              )}
              {summary.selections.class.spellcasting && (
                <p className="spellcasting-note">
                  Spellcasting class ({summary.selections.class.spellcasting.type || 'full'} caster)
                </p>
              )}
            </div>
          </div>
        )}

        {/* Ability Scores */}
        {summary.selections.abilities && (
          <div className="selection-section">
            <h4>Ability Scores</h4>
            <div className="abilities-info">
              <p className="method-info">Method: {summary.selections.abilities.method}</p>
              <div className="ability-grid">
                {Object.entries(summary.selections.abilities.final_scores).map(([ability, score]) => {
                  const modifier = summary.selections.abilities.modifiers[ability];
                  const racialBonus = summary.selections.abilities.racial_bonuses[ability];
                  const baseScore = summary.selections.abilities.base_scores[ability as keyof AbilityScores];

                  return (
                    <div key={ability} className="ability-score">
                      <div className="ability-name">
                        {ability.charAt(0).toUpperCase() + ability.slice(1).slice(0, 3)}
                      </div>
                      <div className="ability-value">
                        {score} ({formatModifier(modifier)})
                      </div>
                      {racialBonus > 0 && (
                        <div className="ability-breakdown">
                          {baseScore} + {racialBonus}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Background Selection */}
        {summary.selections.background && (
          <div className="selection-section">
            <h4>Background</h4>
            <div className="background-info">
              <p className="selection-value">{summary.selections.background.background}</p>
              {summary.selections.background.skill_choices.length > 0 && (
                <div className="skills-info">
                  <strong>Skills:</strong> {summary.selections.background.skill_choices.join(', ')}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Final Selections */}
        {summary.selections.final && (
          <div className="selection-section">
            <h4>Final Choices</h4>
            <div className="final-info">
              {summary.selections.final.feats.length > 0 && (
                <div className="feats-info">
                  <strong>Feats:</strong> {summary.selections.final.feats.join(', ')}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Derived Stats */}
        {summary.derived_stats && (
          <div className="selection-section derived-stats">
            <h4>Character Stats</h4>
            <div className="stats-grid">
              <div className="stat">
                <span className="stat-label">Hit Points:</span>
                <span className="stat-value">{summary.derived_stats.hit_points.average}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Armor Class:</span>
                <span className="stat-value">{summary.derived_stats.armor_class}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Speed:</span>
                <span className="stat-value">{summary.derived_stats.speed} ft</span>
              </div>
              <div className="stat">
                <span className="stat-label">Prof. Bonus:</span>
                <span className="stat-value">+{summary.derived_stats.proficiency_bonus}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CharacterCreationSummary;