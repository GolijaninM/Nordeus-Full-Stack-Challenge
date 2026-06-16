import { useMemo, useState } from 'react';
import './BattleScreen.css';
import combatField from '../../assets/combat-field.png';
import LogicalCropImage from '../../components/LogicalCropImage';
import golfBall from '../../assets/secret items/Golf-ball.png';
import footballBall from '../../assets/secret items/Football-ball.png';
import topElevenImage from '../../assets/characters/top-eleven.png';
import golfRivalImage from '../../assets/characters/golf-rival.png';
import monstersSheet from '../../assets/characters/monsters.png';
import roguesSheet from '../../assets/characters/rogues.png';
import { getMoveIcon } from '../../utils/moveIcons';

const createCharacterState = ({ name, current_hp, hp, max_hp, attack, defense, magic, id, enrage_threshold, enrage_buff_stat, enrage_buff_value, enrage_unlock_moves }) => ({
  id,
  name,
  hp: hp ?? current_hp ?? max_hp,
  max_hp,
  base_attack: attack ?? 0,
  base_defense: defense ?? 0,
  base_magic: magic ?? 0,
  attack: attack ?? 0,
  defense: defense ?? 0,
  magic: magic ?? 0,
  cooldowns: {},
  active_effects: [],
  last_move: null,
  enraged: false,
  enrage_threshold,
  enrage_buff_stat,
  enrage_buff_value,
  enrage_unlock_moves: enrage_unlock_moves ?? []
});

const createInitialBattleState = (hero, monster) => ({
  turn: 1,
  hero: createCharacterState({
    name: hero.name ?? 'Hero',
    current_hp: hero.current_hp,
    max_hp: hero.max_hp,
    attack: hero.attack,
    defense: hero.defense,
    magic: hero.magic
  }),
  monster: createCharacterState({
    id: monster.id,
    name: monster.name,
    hp: monster.max_hp,
    max_hp: monster.max_hp,
    attack: monster.attack,
    defense: monster.defense,
    magic: monster.magic,
    enrage_threshold: monster.enrage_threshold,
    enrage_buff_stat: monster.enrage_buff_stat,
    enrage_buff_value: monster.enrage_buff_value,
    enrage_unlock_moves: monster.enrage_unlock_moves
  })
});

const getEffectLabel = (effect) => {
  if (effect.kind === 'dot') {
    return `${effect.effect_id ?? 'dot'} ${effect.damage}/turn (${effect.remaining})`;
  }

  const sign = effect.amount > 0 ? '+' : '';
  return `${effect.stat} ${sign}${effect.amount} (${effect.remaining})`;
};

const buildFollowUpLog = (data, monsterName) => {
  const parts = [];

  data.events?.forEach(event => {
    if (event.type === 'dot') {
      const target = event.target === 'hero' ? 'You' : monsterName;
      parts.push(`${target} suffered ${event.damage} damage from ${event.source_move}.`);
    }
    if (event.type === 'enrage') {
      parts.push(`${monsterName} entered Enrage and gained +${event.amount} ${event.stat}!`);
    }
  });

  if (data.monster_move) {
    parts.push(`${monsterName} used ${data.monster_move} and dealt ${data.monster_damage} damage.`);
    if (data.monster_combo_triggered) {
      parts.push('Combo triggered.');
    }
  }

  return parts.join(' ');
};

const BattleScreen = ({ hero, monster, onBattleEnd, onUnlockSkin }) => {
  const [battleState, setBattleState] = useState(() => createInitialBattleState(hero, monster));
  const [combatLog, setCombatLog] = useState(`A wild ${monster.name} appears!`);
  const [hoveredMove, setHoveredMove] = useState(null);
  const [heroHit, setHeroHit] = useState(false);
  const [monsterHit, setMonsterHit] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const heroBattleState = battleState.hero;
  const monsterBattleState = battleState.monster;

  const heroHpPercent = Math.max(0, (heroBattleState.hp / heroBattleState.max_hp) * 100);
  const monsterHpPercent = Math.max(0, (monsterBattleState.hp / monsterBattleState.max_hp) * 100);

  const moveCooldowns = useMemo(() => heroBattleState.cooldowns ?? {}, [heroBattleState.cooldowns]);
  const getMoveIconSrc = (moveId) => getMoveIcon(moveId);

  const triggerHitAnimation = (setHitState) => {
    setHitState(true);
    setTimeout(() => setHitState(false), 320);
  };

  const handleMoveSelect = async (moveId) => {
    if (isProcessing || moveCooldowns[moveId] > 0) return;
    setIsProcessing(true);

    try {
      const response = await fetch('http://localhost:5000/api/play-turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          move_id: moveId,
          battle_state: battleState
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Network response was not ok');

      setBattleState(data.battle_state);

      if (data.hero_damage > 0 || data.monster_dot_damage > 0) {
        triggerHitAnimation(setMonsterHit);
      }
      if (data.monster_damage > 0 || data.hero_dot_damage > 0) {
        triggerHitAnimation(setHeroHit);
      }

      const heroLog = [
        `You used ${data.hero_move} and dealt ${data.hero_damage} damage.`,
        data.hero_combo_triggered ? 'Combo triggered.' : ''
      ].filter(Boolean).join(' ');
      setCombatLog(heroLog);

      if (!data.match_over) {
        setTimeout(() => {
          setCombatLog(buildFollowUpLog(data, monster.name));
          setIsProcessing(false);
        }, 1500);
      } else {
        setTimeout(() => {
          if (data.winner === 'hero') {
            setCombatLog(`Victory! ${monster.name} was defeated!`);
            setTimeout(() => {
              onBattleEnd({
                won: true,
                monster,
                xp: data.xp_earned,
                newMove: data.learned_move
              });
            }, 2000);
          } else {
            setCombatLog('Defeat! You have fallen...');
            setTimeout(() => onBattleEnd({ won: false, monster }), 2000);
          }
        }, 1500);
      }
    } catch (error) {
      console.error('Failed to process turn:', error);
      setCombatLog(error.message);
      setIsProcessing(false);
    }
  };

  const renderEffects = (state) => {
    const effects = state.active_effects ?? [];
    if (effects.length === 0 && !state.enraged) return null;

    return (
      <div className="status-effects">
        {state.enraged && <span className="status-chip enrage">Enraged</span>}
        {effects.map((effect, index) => (
          <span key={`${effect.source_move_id}-${effect.kind}-${index}`} className={`status-chip ${effect.kind}`}>
            {getEffectLabel(effect)}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div
      className="battle-container"
      style={{ backgroundImage: `url(${combatField})` }}
    >
      <div className="battle-arena">

        <div className="monster-container">
          <div className="hud monster-hud">
            <h3>{monster.name}</h3>
            <div className="stat-line">ATK {monsterBattleState.attack} DEF {monsterBattleState.defense} MAG {monsterBattleState.magic}</div>
            <div className="health-bar-bg">
              <div className="health-bar-fill monster-fill" style={{ width: `${monsterHpPercent}%` }}></div>
            </div>
            <p className="hp-text">{monsterBattleState.hp} / {monsterBattleState.max_hp} HP</p>
            {renderEffects(monsterBattleState)}
          </div>
          <div className={`character-sprite monster-sprite ${monsterHit ? 'is-hit' : ''}`}>
            {monster.id === 'goblin_warrior' && (
              <LogicalCropImage src={monstersSheet} cropCoords={{ sx: 7 * 32, sy: 0, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === 'goblin_mage' && (
              <LogicalCropImage src={monstersSheet} cropCoords={{ sx: 6 * 32, sy: 0, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === 'giant_spider' && (
              <LogicalCropImage src={monstersSheet} cropCoords={{ sx: 8 * 32, sy: 6 * 32, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === 'witch' && (
              <LogicalCropImage src={monstersSheet} cropCoords={{ sx: 4 * 32, sy: 5 * 32, sWidth: 32, sHeight: 32 }} />
            )}
            {monster.id === 'dragon' && (
              <LogicalCropImage src={monstersSheet} cropCoords={{ sx: 2 * 32, sy: 8 * 32, sWidth: 32, sHeight: 32 }} />
            )}
          </div>
        </div>

        <div className="hero-battle-zone">
          <div className="hud hero-hud">
            <h3>You</h3>
            <div className="stat-line">ATK {heroBattleState.attack} DEF {heroBattleState.defense} MAG {heroBattleState.magic}</div>
            <div className="health-bar-bg">
              <div className="health-bar-fill hero-fill" style={{ width: `${heroHpPercent}%` }}></div>
            </div>
            <p className="hp-text">{heroBattleState.hp} / {heroBattleState.max_hp} HP</p>
            {renderEffects(heroBattleState)}
          </div>

          <div className={`character-sprite hero-sprite ${heroHit ? 'is-hit' : ''}`}>
            {hero.available_skins && hero.current_skin && hero.available_skins[hero.current_skin] && hero.available_skins[hero.current_skin].image === 'easter-egg' ? (
              <img
                src={hero.current_skin === 'knight_secret_left' ? golfRivalImage : topElevenImage}
                alt={hero.available_skins[hero.current_skin].name}
                style={{ maxWidth: '40px', maxHeight: '40px', objectFit: 'contain', imageRendering: 'pixelated' }}
              />
            ) : hero.available_skins && hero.current_skin && hero.available_skins[hero.current_skin] ? (
              <LogicalCropImage
                src={roguesSheet}
                cropCoords={{
                  sx: hero.available_skins[hero.current_skin].coords[0],
                  sy: hero.available_skins[hero.current_skin].coords[1],
                  sWidth: 32,
                  sHeight: 32
                }}
              />
            ) : (
              <LogicalCropImage src={roguesSheet} cropCoords={{ sx: 0, sy: 96, sWidth: 32, sHeight: 32 }} />
            )}
          </div>

          {monster && monster.order === 3 && hero && hero.available_skins && !hero.available_skins['knight_secret_left']?.unlocked && (
            <img
              src={golfBall}
              alt="golf ball"
              className="secret-ball golf-ball"
              onClick={() => {
                if (typeof onUnlockSkin === 'function') {
                  onUnlockSkin('knight_secret_left');
                }
                setCombatLog('You found a hidden golf ball! A secret skin was unlocked.');
              }}
            />
          )}

          {monster && monster.order === 5 && hero && hero.available_skins && !hero.available_skins['knight_secret_right']?.unlocked && (
            <img
              src={footballBall}
              alt="football ball"
              className="secret-ball football-ball"
              onClick={() => {
                if (typeof onUnlockSkin === 'function') {
                  onUnlockSkin('knight_secret_right');
                }
                setCombatLog('You found a hidden football! A secret skin was unlocked.');
              }}
            />
          )}

          <div className="circular-moves">
            {hero.equipped_moves.slice(0, 4).map((move, index) => {
              const cooldownRemaining = moveCooldowns[move.id] ?? 0;
              return (
                <button
                  key={move.id}
                  className={`move-button circular ${move.type} ${cooldownRemaining > 0 ? 'on-cooldown' : ''}`}
                  style={{ '--position': index }}
                  onClick={() => handleMoveSelect(move.id)}
                  disabled={isProcessing || cooldownRemaining > 0}
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
                  {cooldownRemaining > 0 && <span className="cooldown-badge">{cooldownRemaining}</span>}
                </button>
              );
            })}
          </div>

          {hoveredMove && (
            <div className="move-hover-card" aria-live="polite">
              <div className="move-hover-card-name">{hoveredMove.name}</div>
              <div className="move-hover-card-description">
                {hoveredMove.description || 'No description available.'}
              </div>
              {hoveredMove.cooldown > 0 && (
                <div className="move-hover-card-meta">Cooldown: {hoveredMove.cooldown}</div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="battle-controls">
        <div className="combat-log">
          <p>{combatLog}</p>
        </div>
      </div>
    </div>
  );
};

export default BattleScreen;
