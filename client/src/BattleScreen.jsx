import React, { useState } from 'react';
import './BattleScreen.css';
import combatField from '../images/combat-field.jpg'; 
import LogicalCropImage from './LogicalCropImage';

const BattleScreen = ({ hero, monster, onBattleEnd }) => {
  // Track the active HP locally during the fight
  const [heroHp, setHeroHp] = useState(hero.current_hp);
  const [monsterHp, setMonsterHp] = useState(monster.max_hp);
  
  // Track what happened to display on screen
  const [combatLog, setCombatLog] = useState(`A wild ${monster.name} appears!`);
  
  // Prevent spam-clicking while waiting for the server
  const [isProcessing, setIsProcessing] = useState(false);

  const handleMoveSelect = async (moveId) => {
    if (isProcessing) return;
    setIsProcessing(true);

    try {
      // 1. Construct the URL with query parameters for the Flask server
      const url = new URL('http://localhost:5000/api/play-turn');
      url.searchParams.append('hero_hp', heroHp);
      url.searchParams.append('hero_atk', hero.attack);
      url.searchParams.append('hero_def', hero.defense);
      url.searchParams.append('hero_mag', hero.magic);
      url.searchParams.append('monster_id', monster.id);
      url.searchParams.append('monster_hp', monsterHp);
      url.searchParams.append('move_id', moveId);

      // 2. Fetch the turn result
      const response = await fetch(url);
      if (!response.ok) throw new Error("Network response was not ok");
      const data = await response.json();

      // 3. Process the visual updates step-by-step
      
      // Update Monster HP and log the Hero's attack
      setMonsterHp(data.monster_hp_remaining);
      setCombatLog(`${hero.name} used ${data.hero_move} and dealt ${data.hero_damage} damage!`);

      // If the monster didn't die, wait 1.5 seconds and show its counter-attack
      if (!data.match_over) {
        setTimeout(() => {
          setHeroHp(data.hero_hp_remaining);
          setCombatLog(`${monster.name} used ${data.monster_move} and dealt ${data.monster_damage} damage!`);
          setIsProcessing(false);
        }, 1500);
      } else {
        // Match is over!
        setTimeout(() => {
          if (data.winner === 'hero') {
            setCombatLog(`Victory! ${monster.name} was defeated!`);
            // Wait a moment so the player can read the victory text before leaving
            setTimeout(() => onBattleEnd({ won: true, monster: monster }), 2000);
          } else {
            setCombatLog(`Defeat! ${hero.name} has fallen...`);
            setTimeout(() => onBattleEnd({ won: false, monster: monster }), 2000);
          }
        }, 1500);
      }

    } catch (error) {
      console.error("Failed to process turn:", error);
      setIsProcessing(false);
    }
  };

  // Calculate health bar percentages safely (avoiding negative widths)
  const heroHpPercent = Math.max(0, (heroHp / hero.max_hp) * 100);
  const monsterHpPercent = Math.max(0, (monsterHp / monster.max_hp) * 100);

  return (
    <div 
      className="battle-container" 
      style={{ backgroundImage: `url(${combatField})` }}
    >
      <div className="battle-arena">
        
        {/* Monster and Health Bar */}
        <div className="monster-container">
          <div className="hud monster-hud">
            <h3>{monster.name}</h3>
            <div className="health-bar-bg">
              <div className="health-bar-fill monster-fill" style={{ width: `${monsterHpPercent}%` }}></div>
            </div>
            <p className="hp-text">{monsterHp} / {monster.max_hp} HP</p>
          </div>
          <div className="character-sprite monster-sprite">
            <LogicalCropImage src="/images/monsters.png" cropCoords={{ sx: 0, sy: 0, sWidth: 32, sHeight: 32 }} />
          </div>
        </div>

        {/* Hero with circular ability buttons */}
        <div className="hero-battle-zone">
          <div className="hud hero-hud">
            <h3>{hero.name}</h3>
            <div className="health-bar-bg">
              <div className="health-bar-fill hero-fill" style={{ width: `${heroHpPercent}%` }}></div>
            </div>
            <p className="hp-text">{heroHp} / {hero.max_hp} HP</p>
          </div>
          
          <div className="character-sprite hero-sprite">
            <LogicalCropImage src="/images/rogues.png" cropCoords={{ sx: 0, sy: 32, sWidth: 32, sHeight: 32 }} />
          </div>

          {/* Circular ability buttons around hero */}
          <div className="circular-moves">
            {hero.equipped_moves.map((move, index) => (
              <button 
                key={move.id} 
                className={`move-button circular ${move.type}`}
                style={{ '--position': index }}
                onClick={() => handleMoveSelect(move.id)}
                disabled={isProcessing}
                title={move.name}
              >
                <span className="move-name">{move.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Combat Log */}
      <div className="battle-controls">
        <div className="combat-log">
          <p>{combatLog}</p>
        </div>
      </div>
    </div>
  );
};

export default BattleScreen;