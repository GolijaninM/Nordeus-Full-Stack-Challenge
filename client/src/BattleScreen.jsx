import React, { useState } from 'react';
import './BattleScreen.css';
import combatField from '../images/combat-field.jpg'; 
import LogicalCropImage from './LogicalCropImage';

const BattleScreen = ({ hero, monster, onBattleEnd }) => {

  const [heroHp, setHeroHp] = useState(hero.current_hp);
  const [heroMaxHp] = useState(hero.max_hp);
  const [heroAtk, setHeroAtk] = useState(hero.attack);
  const [heroDef, setHeroDef] = useState(hero.defense);
  const [heroMag, setHeroMag] = useState(hero.magic);

  const [heroBaseAtk] = useState(hero.attack);
  const [heroBaseDef] = useState(hero.defense);
  const [heroBaseMag] = useState(hero.magic);

  const [heroAtkDuration, setHeroAtkDuration] = useState(0);
  const [heroDefDuration, setHeroDefDuration] = useState(0);
  const [heroMagDuration, setHeroMagDuration] = useState(0);
  
  const [monsterHp, setMonsterHp] = useState(monster.max_hp);
  const [monsterMaxHp] = useState(monster.max_hp);
  const [monsterAtk, setMonsterAtk] = useState(monster.attack || 0);
  const [monsterDef, setMonsterDef] = useState(monster.defense || 0);
  const [monsterMag, setMonsterMag] = useState(monster.magic || 0);

  const [monsterBaseAtk] = useState(monster.attack || 0);
  const [monsterBaseDef] = useState(monster.defense || 0);
  const [monsterBaseMag] = useState(monster.magic || 0);

  const [monsterAtkDuration, setMonsterAtkDuration] = useState(0);
  const [monsterDefDuration, setMonsterDefDuration] = useState(0);
  const [monsterMagDuration, setMonsterMagDuration] = useState(0);
  
  const [combatLog, setCombatLog] = useState(`A wild ${monster.name} appears!`);
  const [hoveredMove, setHoveredMove] = useState(null);
  
  const [isProcessing, setIsProcessing] = useState(false);

  const getMoveIconSrc = (moveId) => `/images/moves/${moveId}.png`;

  const decrementStatDurations = () => {
    setHeroAtkDuration(prev => Math.max(0, prev - 1));
    setHeroDefDuration(prev => Math.max(0, prev - 1));
    setHeroMagDuration(prev => Math.max(0, prev - 1));
    setMonsterAtkDuration(prev => Math.max(0, prev - 1));
    setMonsterDefDuration(prev => Math.max(0, prev - 1));
    setMonsterMagDuration(prev => Math.max(0, prev - 1));
  };

  const handleMoveSelect = async (moveId) => {
    if (isProcessing) return;
    setIsProcessing(true);

    // Check if any stat durations have expired and reset to base if needed
    let currentHeroAtk = heroAtkDuration > 0 ? heroAtk : heroBaseAtk;
    let currentHeroDef = heroDefDuration > 0 ? heroDef : heroBaseDef;
    let currentHeroMag = heroMagDuration > 0 ? heroMag : heroBaseMag;
    
    let currentMonsterAtk = monsterAtkDuration > 0 ? monsterAtk : monsterBaseAtk;
    let currentMonsterDef = monsterDefDuration > 0 ? monsterDef : monsterBaseDef;
    let currentMonsterMag = monsterMagDuration > 0 ? monsterMag : monsterBaseMag;

    try {
      const url = new URL('http://localhost:5000/api/play-turn');
      url.searchParams.append('hero_hp', heroHp);
      url.searchParams.append('hero_max_hp', heroMaxHp);
      url.searchParams.append('hero_atk', currentHeroAtk);
      url.searchParams.append('hero_def', currentHeroDef);
      url.searchParams.append('hero_mag', currentHeroMag);
      url.searchParams.append('monster_id', monster.id);
      url.searchParams.append('monster_hp', monsterHp);
      url.searchParams.append('move_id', moveId);

      const response = await fetch(url);
      if (!response.ok) throw new Error("Network response was not ok");
      const data = await response.json();

      decrementStatDurations();

      // 3. Update all stats from response
      setHeroAtk(data.hero_state.attack);
      setHeroDef(data.hero_state.defense);
      setHeroMag(data.hero_state.magic);

      setMonsterHp(data.monster_state.hp);
      setMonsterAtk(data.monster_state.attack);
      setMonsterDef(data.monster_state.defense);
      setMonsterMag(data.monster_state.magic);


      // Update stat change durations based on stat changes in response
      if (data.hero_stat_changes && data.hero_stat_changes.length > 0) {
        data.hero_stat_changes.forEach(change => {
          if (change.stat === 'attack') setHeroAtkDuration(2);
          if (change.stat === 'defense') setHeroDefDuration(2);
          if (change.stat === 'magic') setHeroMagDuration(2);
        });
      }

      if (data.monster_stat_changes && data.monster_stat_changes.length > 0) {
        data.monster_stat_changes.forEach(change => {
          if (change.stat === 'attack') setMonsterAtkDuration(2);
          if (change.stat === 'defense') setMonsterDefDuration(2);
          if (change.stat === 'magic') setMonsterMagDuration(2);
        });
      }

      // Display the hero's action
      setCombatLog(`${hero.name} used ${data.hero_move} and dealt ${data.hero_damage} damage!`);
      console.log("Heros defense: " + currentHeroDef);
      console.log("Heros attack: " + currentHeroAtk);

      if (!data.match_over) {
        setTimeout(() => {
          // Display the monster's counterattack
          setHeroHp(data.hero_state.hp);
          setCombatLog(`${monster.name} used ${data.monster_move} and dealt ${data.monster_damage} damage!`);
          
          setIsProcessing(false);
        }, 1500);
      } else {
        setHeroHp(data.hero_state.hp);
        setTimeout(() => {
          if (data.winner === 'hero') {
            setCombatLog(`Victory! ${monster.name} was defeated!`);
            setTimeout(() => {
              onBattleEnd({ 
                won: true, 
                monster: monster, 
                xp: data.xp_earned, 
                newMove: data.learned_move 
              });
            }, 2000);
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

  const heroHpPercent = Math.max(0, (heroHp / heroMaxHp) * 100);
  const monsterHpPercent = Math.max(0, (monsterHp / monsterMaxHp) * 100);

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
            <p className="hp-text">{monsterHp} / {monsterMaxHp} HP</p>
          </div>
          <div className="character-sprite monster-sprite">
            {monster.id === "goblin_warrior" && (
                <LogicalCropImage src="/images/monsters.png" cropCoords={{ sx: 7*32, sy: 0, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === "goblin_mage" && (
                <LogicalCropImage src="/images/monsters.png" cropCoords={{ sx: 6*32, sy: 0, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === "giant_spider" && (
                <LogicalCropImage src="/images/monsters.png" cropCoords={{ sx: 8*32, sy: 6*32, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === "witch" && (
                <LogicalCropImage src="/images/monsters.png" cropCoords={{ sx: 4*32, sy: 5*32, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === "dragon" && (
                <LogicalCropImage src="/images/monsters.png" cropCoords={{ sx: 2*32, sy: 8*32, sWidth: 32, sHeight: 32 }} />
            )}
          </div>
        </div>

        {/* Hero with circular ability buttons */}
        <div className="hero-battle-zone">
          <div className="hud hero-hud">
            <h3>{hero.name}</h3>
            <div className="health-bar-bg">
              <div className="health-bar-fill hero-fill" style={{ width: `${heroHpPercent}%` }}></div>
            </div>
            <p className="hp-text">{heroHp} / {heroMaxHp} HP</p>
          </div>
          
          <div className="character-sprite hero-sprite">
            <LogicalCropImage src="/images/rogues.png" cropCoords={{ sx: 0, sy: 32, sWidth: 32, sHeight: 32 }} />
          </div>

          {/* Circular ability buttons around hero */}
          <div className="circular-moves">
            {hero.equipped_moves.slice(0, 4).map((move, index) => (
              <button 
                key={move.id} 
                className={`move-button circular ${move.type}`}
                style={{ '--position': index }}
                onClick={() => handleMoveSelect(move.id)}
                disabled={isProcessing}
                onMouseEnter={() => {
                  setHoveredMove(move);
                }}
                onMouseLeave={() => {
                  setHoveredMove(null);
                }}
                title={move.description || move.name}
                aria-label={`${move.name}: ${move.description || 'No description available'}`}
              >
                <img className="move-icon" src={getMoveIconSrc(move.id)} alt="" aria-hidden="true" />
              </button>
            ))}
          </div>

          {hoveredMove && (
            <div className="move-hover-card" aria-live="polite">
              <div className="move-hover-card-name">{hoveredMove.name}</div>
              <div className="move-hover-card-description">
                {hoveredMove.description || 'No description available.'}
              </div>
            </div>
          )}
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