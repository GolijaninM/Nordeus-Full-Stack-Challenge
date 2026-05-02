import React, { useEffect, useState } from 'react';
import MainMenu from './screens/MainMenu/MainMenu';
import MapOverview from './screens/MapOverview/MapOverview';
import BattleScreen from './screens/BattleScreen/BattleScreen';
import BattleResultScreen from './screens/BattleScreen/BattleResultScreen';

const HERO_PROGRESS_STORAGE_KEY = 'nordeus.heroProgression';
const ENCOUNTERS_STORAGE_KEY = 'nordeus.encounters';
const LEARNED_MOVES_STORAGE_KEY = 'nordeus.learnedMoves';
const LEARNED_MOVES_DETAILS_STORAGE_KEY = 'nordeus.learnedMovesDetails';
const BASE_STAT_UPGRADE_COST = 20;
const STAT_UPGRADE_AMOUNT = 5;
const STAT_UPGRADE_COST_INCREMENT = 10;

const calculateUpgradeCost = (upgradeCount) => {
  return BASE_STAT_UPGRADE_COST + (upgradeCount * STAT_UPGRADE_COST_INCREMENT);
};

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

const readStoredEncounters = () => {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const rawEncounters = window.localStorage.getItem(ENCOUNTERS_STORAGE_KEY);
    return rawEncounters ? JSON.parse(rawEncounters) : null;
  } catch (error) {
    console.error('Failed to read stored encounters:', error);
    return null;
  }
};

const readStoredLearnedMoves = () => {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const rawMoves = window.localStorage.getItem(LEARNED_MOVES_STORAGE_KEY);
    return rawMoves ? JSON.parse(rawMoves) : [];
  } catch (error) {
    console.error('Failed to read stored learned moves:', error);
    return [];
  }
};

const readStoredLearnedMovesDetails = () => {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const rawDetails = window.localStorage.getItem(LEARNED_MOVES_DETAILS_STORAGE_KEY);
    return rawDetails ? JSON.parse(rawDetails) : {};
  } catch (error) {
    console.error('Failed to read stored learned moves details:', error);
    return {};
  }
};

const hasSavedRun = () => {
  return readStoredHeroProgression() !== null && readStoredEncounters() !== null;
};

const mergeHeroState = (baseHero, storedHero) => {
  if (!storedHero) {
    return {
      ...baseHero,
      current_hp: baseHero.max_hp,
      stat_upgrades: {
        attack: 0,
        defense: 0,
        magic: 0,
        max_hp: 0
      }
    };
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
    // merge available skins and ensure secret skins exist
    available_skins: (() => {
      const baseSkins = baseHero.available_skins || {};
      const storedSkins = (storedHero && storedHero.available_skins) ? storedHero.available_skins : {};
      const combined = { ...baseSkins, ...storedSkins };
      // Add two secret skins if missing. These start locked and are shown as ??? in shop.
      if (!combined['knight_secret_left']) {
        combined['knight_secret_left'] = { name: '???', cost: 0, unlocked: false, coords: [0, 0], image: 'easter-egg' };
      }
      if (!combined['knight_secret_right']) {
        combined['knight_secret_right'] = { name: '???', cost: 0, unlocked: false, coords: [32, 0], image: 'easter-egg' };
      }
      return combined;
    })(),
    equipped_moves: baseHero.equipped_moves,
    stat_upgrades: storedHero.stat_upgrades ?? {
      attack: 0,
      defense: 0,
      magic: 0,
      max_hp: 0
    }
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
  const [savedRunExists, setSavedRunExists] = useState(false);

  useEffect(() => {
    setSavedRunExists(hasSavedRun());
  }, []);

  const handleStartGame = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/start-run');
      const data = await response.json();
      // Ensure secret skins exist on fresh runs
      const heroWithSecrets = {
        ...data.hero,
        available_skins: (() => {
          const base = data.hero.available_skins || {};
          const combined = { ...base };
          if (!combined['knight_secret_left']) combined['knight_secret_left'] = { name: '???', cost: 0, unlocked: false, coords: [0, 0], image: 'easter-egg' };
          if (!combined['knight_secret_right']) combined['knight_secret_right'] = { name: '???', cost: 0, unlocked: false, coords: [32, 0], image: 'easter-egg' };
          return combined;
        })()
      };

      heroWithSecrets.learned_moves = data.hero.equipped_moves.map(move => move.id);
      heroWithSecrets.learned_moves_details = data.hero.equipped_moves.reduce((details, move) => {
        details[move.id] = move;
        return details;
      }, {});

      setHeroState(heroWithSecrets);
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

  const handleContinueRun = () => {
    const savedHero = readStoredHeroProgression();
    const savedEncounters = readStoredEncounters();

    if (!savedHero || !savedEncounters) {
      console.error("No saved run found");
      return;
    }

    // Ensure secret skins exist on continued runs
    const patchedHero = {
      ...savedHero,
      available_skins: (() => {
        const base = savedHero.available_skins || {};
        const combined = { ...base };
        if (!combined['knight_secret_left']) combined['knight_secret_left'] = { name: '???', cost: 0, unlocked: false, coords: [0, 0], image: 'easter-egg' };
        if (!combined['knight_secret_right']) combined['knight_secret_right'] = { name: '???', cost: 0, unlocked: false, coords: [32, 0], image: 'easter-egg' };
        return combined;
      })()
    };

    setHeroState(patchedHero);
    setEncounters(savedEncounters);

    // Load learned moves from the saved hero first, then fall back to separate storage
    const savedMoveIds = Array.isArray(savedHero.learned_moves) && savedHero.learned_moves.length > 0
      ? savedHero.learned_moves
      : readStoredLearnedMoves();
    setAllLearnedMoves(savedMoveIds.length > 0 ? savedMoveIds : []);

    // Load learned move details from the saved hero first, then fall back to separate storage
    const savedMoveDetails = savedHero.learned_moves_details && typeof savedHero.learned_moves_details === 'object'
      ? savedHero.learned_moves_details
      : readStoredLearnedMovesDetails();
    setAllLearnedMovesDetails(savedMoveDetails);

    setCurrentScreen('map');
  };

  const handleUnlockSkin = (skinId) => {
    setHeroState(prev => {
      if (!prev) return prev;
      const updatedSkins = { ...prev.available_skins };
      if (!updatedSkins[skinId]) return prev;
      // Reveal the skin name when unlocked (replace ???)
      const revealedName = skinId === 'knight_secret_left' ? 'Golf Player' : (skinId === 'knight_secret_right' ? 'Football Manager' : (updatedSkins[skinId].displayName ?? 'Secret'));
      updatedSkins[skinId] = { ...updatedSkins[skinId], unlocked: true, name: revealedName };

      return {
        ...prev,
        available_skins: updatedSkins
      };
    });
  };

  useEffect(() => {
    if (typeof window === 'undefined' || !heroState) {
      return;
    }

    try {
      const heroProgressToStore = {
        ...heroState,
        learned_moves: allLearnedMoves,
        learned_moves_details: allLearnedMovesDetails
      };
      window.localStorage.setItem(HERO_PROGRESS_STORAGE_KEY, JSON.stringify(heroProgressToStore));
    } catch (error) {
      console.error('Failed to store hero progression:', error);
    }
  }, [heroState, allLearnedMoves, allLearnedMovesDetails]);

  useEffect(() => {
    if (typeof window === 'undefined' || encounters.length === 0) {
      return;
    }

    try {
      window.localStorage.setItem(ENCOUNTERS_STORAGE_KEY, JSON.stringify(encounters));
    } catch (error) {
      console.error('Failed to store encounters:', error);
    }
  }, [encounters]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      window.localStorage.setItem(LEARNED_MOVES_STORAGE_KEY, JSON.stringify(allLearnedMoves));
    } catch (error) {
      console.error('Failed to store learned moves:', error);
    }
  }, [allLearnedMoves]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      window.localStorage.setItem(LEARNED_MOVES_DETAILS_STORAGE_KEY, JSON.stringify(allLearnedMovesDetails));
    } catch (error) {
      console.error('Failed to store learned moves details:', error);
    }
  }, [allLearnedMovesDetails]);

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
      if (!prevHero) return prevHero;

      const upgradeCount = prevHero.stat_upgrades?.[statKey] ?? 0;
      const upgradeCost = calculateUpgradeCost(upgradeCount);

      if (prevHero.current_xp < upgradeCost) {
        return prevHero;
      }

      const nextHero = {
        ...prevHero,
        current_xp: prevHero.current_xp - upgradeCost,
        [statKey]: (prevHero[statKey] ?? 0) + STAT_UPGRADE_AMOUNT,
        stat_upgrades: {
          ...prevHero.stat_upgrades,
          [statKey]: upgradeCount + 1
        }
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
        <MainMenu 
          onStartRun={handleStartGame} 
          onContinueRun={handleContinueRun}
          savedRunExists={savedRunExists}
        />
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
          onUnlockSkin={handleUnlockSkin}
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