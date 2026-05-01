import React, { useEffect, useState } from 'react';
import MainMenu from './MainMenu';
import MapOverview from './MapOverview';
import BattleScreen from './BattleScreen';
import BattleResultScreen from './BattleResultScreen';

const HERO_PROGRESS_STORAGE_KEY = 'nordeus.heroProgression';
const STAT_UPGRADE_COST = 20;
const STAT_UPGRADE_AMOUNT = 5;

const readStoredHeroProgression = () => {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const rawProgression = window.localStorage.getItem(HERO_PROGRESS_STORAGE_KEY);
    return rawProgression ? JSON.parse(rawProgression) : null;
  } catch (error) {
    console.error('Failed to read stored hero progression:', error);
    return null;
  }
};

const mergeHeroState = (baseHero, storedHero) => {
  if (!storedHero) {
    return baseHero;
  }

  const mergedHero = {
    ...baseHero,
    ...storedHero,
    current_xp: storedHero.current_xp ?? baseHero.current_xp ?? 0,
    attack: storedHero.attack ?? baseHero.attack,
    defense: storedHero.defense ?? baseHero.defense,
    magic: storedHero.magic ?? baseHero.magic,
    max_hp: storedHero.max_hp ?? baseHero.max_hp,
    coins: storedHero.coins ?? baseHero.coins ?? 0,
    current_skin: storedHero.current_skin ?? baseHero.current_skin ?? 'knight_default',
    available_skins: baseHero.available_skins,
    equipped_moves: baseHero.equipped_moves
  };

  return {
    ...mergedHero,
    current_hp: mergedHero.max_hp
  };
};

function App() {
  const [currentScreen, setCurrentScreen] = useState('menu');
  const [heroState, setHeroState] = useState(null);
  const [encounters, setEncounters] = useState([]);
  const [activeMonster, setActiveMonster] = useState(null); // Track the current fight
  const [battleResultData, setBattleResultData] = useState(null); // Track battle results
  const [allLearnedMoves, setAllLearnedMoves] = useState([]); // Track all abilities learned
  const [allLearnedMovesDetails, setAllLearnedMovesDetails] = useState({}); // Store full details of all learned moves

  const handleStartGame = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/start-run');
      const data = await response.json();
      setHeroState(data.hero);
      setEncounters(data.run_encounters);
      // Initialize all learned moves with default moves
      const moveIds = data.hero.equipped_moves.map(m => m.id);
      setAllLearnedMoves(moveIds);
      
      // Store full details of all learned moves
      const moveDetails = {};
      data.hero.equipped_moves.forEach(move => {
        moveDetails[move.id] = move;
      });
      setAllLearnedMovesDetails(moveDetails);
      
      setCurrentScreen('map');
    } catch (error) {
      console.error("Failed to fetch game data:", error);
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined' || !heroState) {
      return;
    }

    try {
      window.localStorage.setItem(HERO_PROGRESS_STORAGE_KEY, JSON.stringify(heroState));
    } catch (error) {
      console.error('Failed to store hero progression:', error);
    }
  }, [heroState]);

  const handleEnterBattle = (monsterData) => {
    setActiveMonster(monsterData);
    setCurrentScreen('battle');
  };

  const handleBattleEnd = (resultData) => {
    // Calculate coins reward based on monster health: max = health/3
    let coinsReward = 0;
    if (resultData.won) {
      const maxCoins = Math.floor(resultData.monster.max_hp / 2);
      coinsReward = Math.floor(Math.random() * maxCoins) + 1;
    }
    
    // Save the outcome and switch to the result screen
    setBattleResultData({
      ...resultData,
      coinsEarned: coinsReward
    });
    setCurrentScreen('result');
  };

  const handleCloseResult = () => {
    if (battleResultData.won) {
      const newMove = battleResultData.newMove;
      if (newMove && newMove.id) {
        const newMoveId = newMove.id;

        // Add learned move to all learned moves if not already there
        setAllLearnedMoves(prevMoves => {
          if (!prevMoves.includes(newMoveId)) {
            return [...prevMoves, newMoveId];
          }
          return prevMoves;
        });

        // Store full details of the new learned move
        setAllLearnedMovesDetails(prevDetails => ({
          ...prevDetails,
          [newMoveId]: newMove
        }));
      }

      // Use coinsEarned from battleResultData (calculated in handleBattleEnd)
      const coinsReward = battleResultData.coinsEarned ?? 0;

      // Update hero state - add XP and coins
      setHeroState(prevHero => {
        return {
          ...prevHero,
          current_xp: prevHero.current_xp + battleResultData.xp,
          coins: (prevHero.coins ?? 0) + coinsReward
        };
      });

      setEncounters(prevMap => {
        const newMap = [...prevMap];
        const monsterIndex = newMap.findIndex(m => m.id === battleResultData.monster.id);

        if (monsterIndex >= 0 && monsterIndex < newMap.length) {
          // Mark current as completed
          newMap[monsterIndex].status = 'completed';

          // Unlock the next one if it exists and is locked
          if (monsterIndex + 1 < newMap.length && newMap[monsterIndex + 1].status === 'locked') {
            newMap[monsterIndex + 1].status = 'next';
          }
        }

        return newMap;
      });
    }
    
    // Return to map whether we won or lost
    setCurrentScreen('map');
  };

  const handleSelectAbilities = (selectedMoveIds) => {
    setHeroState(prevHero => {
      // Build equipped moves from selected IDs using stored move details
      const equippedMoves = selectedMoveIds
        .map(moveId => allLearnedMovesDetails[moveId])
        .filter(m => m !== undefined);
      
      return {
        ...prevHero,
        equipped_moves: equippedMoves
      };
    });
  };

  const handleUpgradeStat = (statKey) => {
    setHeroState(prevHero => {
      if (!prevHero || prevHero.current_xp < STAT_UPGRADE_COST) {
        return prevHero;
      }

      const nextHero = {
        ...prevHero,
        current_xp: prevHero.current_xp - STAT_UPGRADE_COST,
        [statKey]: (prevHero[statKey] ?? 0) + STAT_UPGRADE_AMOUNT
      };

      if (statKey === 'max_hp') {
        nextHero.current_hp = Math.min(
          (prevHero.current_hp ?? prevHero.max_hp ?? 0) + STAT_UPGRADE_AMOUNT,
          nextHero.max_hp
        );
      }

      return nextHero;
    });
  };

  const handleBuySkin = (skinId) => {
    setHeroState(prevHero => {
      if (!prevHero) return prevHero;
      
      const skin = prevHero.available_skins?.[skinId];
      if (!skin || (prevHero.coins ?? 0) < skin.cost) {
        return prevHero; // Not enough coins
      }

      // Deduct coins and unlock skin
      const updatedSkins = { ...prevHero.available_skins };
      updatedSkins[skinId] = { ...skin, unlocked: true };

      return {
        ...prevHero,
        coins: prevHero.coins - skin.cost,
        available_skins: updatedSkins,
        current_skin: skinId // Auto-equip the purchased skin
      };
    });
  };

  const handleEquipSkin = (skinId) => {
    setHeroState(prevHero => {
      if (!prevHero) return prevHero;
      
      const skin = prevHero.available_skins?.[skinId];
      if (!skin || !skin.unlocked) {
        return prevHero; // Skin not available
      }

      return {
        ...prevHero,
        current_skin: skinId
      };
    });
  };

  return (
    <div>
      {currentScreen === 'menu' && (
        <MainMenu onStartRun={handleStartGame} />
      )}
      
      {currentScreen === 'map' && (
        <MapOverview 
          encounters={encounters}
          heroState={heroState}
          allLearnedMoves={allLearnedMoves}
          allLearnedMovesDetails={allLearnedMovesDetails}
          onEnterBattle={handleEnterBattle}
          onSelectAbilities={handleSelectAbilities}
          onUpgradeStat={handleUpgradeStat}
          onBuySkin={handleBuySkin}
          onEquipSkin={handleEquipSkin}
        />
      )}

      {currentScreen === 'battle' && activeMonster && (
        <BattleScreen
          hero={heroState}
          monster={activeMonster}
          onBattleEnd={handleBattleEnd}
        />
      )}

      {currentScreen === 'result' && battleResultData && (
        <BattleResultScreen 
          resultData={battleResultData} 
          onContinue={handleCloseResult} 
        />
      )}

    </div>
  );
}

export default App;