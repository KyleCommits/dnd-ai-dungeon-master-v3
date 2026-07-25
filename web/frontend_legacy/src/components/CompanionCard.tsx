import React, { useState } from 'react';
import './CompanionCard.css';

interface Companion {
  id: number;
  name: string;
  template_name: string;
  size: string;
  creature_type: string;
  challenge_rating: string;
  level: number;
  armor_class: number;
  current_hp: number;
  max_hp: number;
  hit_dice: string;
  abilities: {
    strength: number;
    dexterity: number;
    constitution: number;
    intelligence: number;
    wisdom: number;
    charisma: number;
  };
  speed: {
    land: number;
    fly: number;
    swim: number;
    climb: number;
    burrow: number;
  };
  skills: Record<string, number>;
  darkvision: number;
  blindsight: number;
  passive_perception: number;
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
  is_unconscious: boolean;
  is_dead: boolean;
  relationship_level: number;
  personality_traits: string;
  backstory: string;
  notes: string;
  environment: string;
  description: string;
  experience_points: number;
  level_bonuses: {
    hp_bonus: number;
    ac_bonus: number;
    attack_bonus: number;
    damage_bonus: number;
    abilities: string[];
  };
}

interface CompanionCardProps {
  companion: Companion;
  onHeal: (companionId: number, amount: number) => void;
  onDamage: (companionId: number, amount: number) => void;
  onLevelUp: (companionId: number, rangerLevel: number) => void;
  onDismiss: (companionId: number) => void;
}

export default function CompanionCard({ companion, onHeal, onDamage, onLevelUp, onDismiss }: CompanionCardProps) {
  const [healAmount, setHealAmount] = useState('');
  const [damageAmount, setDamageAmount] = useState('');
  const [rangerLevel, setRangerLevel] = useState('');
  const [showActions, setShowActions] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const getAbilityModifier = (score: number) => {
    return Math.floor((score - 10) / 2);
  };

  const formatModifier = (modifier: number) => {
    return modifier >= 0 ? `+${modifier}` : `${modifier}`;
  };

  const getSpeedDisplay = (speed: Companion['speed']) => {
    const speeds = [];
    if (speed.land > 0) speeds.push(`${speed.land} ft.`);
    if (speed.fly > 0) speeds.push(`fly ${speed.fly} ft.`);
    if (speed.swim > 0) speeds.push(`swim ${speed.swim} ft.`);
    if (speed.climb > 0) speeds.push(`climb ${speed.climb} ft.`);
    if (speed.burrow > 0) speeds.push(`burrow ${speed.burrow} ft.`);
    return speeds.join(', ');
  };

  const getHealthPercentage = () => {
    return Math.max(0, (companion.current_hp / companion.max_hp) * 100);
  };

  const getHealthColor = () => {
    const percentage = getHealthPercentage();
    if (percentage > 75) return '#4caf50';
    if (percentage > 50) return '#ff9800';
    if (percentage > 25) return '#f44336';
    return '#9e9e9e';
  };

  const handleHeal = () => {
    const amount = parseInt(healAmount);
    if (amount > 0) {
      onHeal(companion.id, amount);
      setHealAmount('');
    }
  };

  const handleDamage = () => {
    const amount = parseInt(damageAmount);
    if (amount > 0) {
      onDamage(companion.id, amount);
      setDamageAmount('');
    }
  };

  const handleLevelUp = () => {
    const level = parseInt(rangerLevel);
    if (level > 0) {
      onLevelUp(companion.id, level);
      setRangerLevel('');
    }
  };

  const getRelationshipText = (level: number) => {
    const relationships = ['Unknown', 'Wary', 'Neutral', 'Friendly', 'Bonded', 'Devoted'];
    return relationships[Math.min(level, relationships.length - 1)];
  };

  return (
    <div className={`character-card companion-card ${companion.is_dead ? 'dead' : companion.is_unconscious ? 'unconscious' : ''}`}>
      <div className="character-main">
        <div className="character-header">
          <h4>{companion.name}</h4>
          <span className="character-class">{companion.template_name}</span>
          <span className="character-level">Level {companion.level}</span>
        </div>
        <div className="character-stats">
          <div className="stat-group">
            <span>HP: {companion.current_hp}/{companion.max_hp}</span>
            <span>AC: {companion.armor_class}</span>
            <span>Speed: {getSpeedDisplay(companion.speed)}</span>
          </div>
        </div>
        {(companion.is_dead || companion.is_unconscious) && (
          <div className="status-alert">
            {companion.is_dead ? 'DEAD' : 'UNCONSCIOUS'}
          </div>
        )}
      </div>
      <div className="character-actions">
        <button
          className="btn btn-secondary"
          onClick={() => setShowActions(!showActions)}
        >
          {showActions ? 'Hide Actions' : 'Actions'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? 'Hide Details' : 'Details'}
        </button>
      </div>

      {showActions && !companion.is_dead && (
        <div className="action-panel">
          <div className="action-group">
            <label>Heal:</label>
            <input
              type="number"
              value={healAmount}
              onChange={(e) => setHealAmount(e.target.value)}
              placeholder="Amount"
              min="1"
            />
            <button onClick={handleHeal} disabled={!healAmount}>Heal</button>
          </div>

          <div className="action-group">
            <label>Damage:</label>
            <input
              type="number"
              value={damageAmount}
              onChange={(e) => setDamageAmount(e.target.value)}
              placeholder="Amount"
              min="1"
            />
            <button onClick={handleDamage} disabled={!damageAmount}>Damage</button>
          </div>

          <div className="action-group">
            <label>Level Up (Ranger Level):</label>
            <input
              type="number"
              value={rangerLevel}
              onChange={(e) => setRangerLevel(e.target.value)}
              placeholder="Ranger Level"
              min="3"
              max="20"
            />
            <button onClick={handleLevelUp} disabled={!rangerLevel}>Level Up</button>
          </div>

          <div className="action-group">
            <button
              className="dismiss-btn"
              onClick={() => onDismiss(companion.id)}
            >
              Dismiss Companion
            </button>
          </div>
        </div>
      )}

      {showDetails && (
        <div className="details-panel">
          {/* Details content remains the same */}
        </div>
      )}
    </div>
  );
}