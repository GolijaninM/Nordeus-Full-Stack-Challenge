import React, { useState } from 'react';
import MainMenu from './MainMenu';
import MapOverview from './MapOverview';
import BattleScreen from './BattleScreen';
import BattleResultScreen from './BattleResultScreen';

function App() {
  const [currentScreen, setCurrentScreen] = useState('menu');
  const [heroState, setHeroState] = useState(null);
  const [encounters, setEncounters] = useState([]);
  const [activeMonster, setActiveMonster] = useState(null); // Track the current fight
  const [battleResultData, setBattleResultData] = useState(null); // Track battle results

  const handleStartGame = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/start-run');
      const data = await response.json();
      setHeroState(data.hero);
      setEncounters(data.run_encounters);
      setCurrentScreen('map');
    } catch (error) {
      console.error("Failed to fetch game data:", error);
    }
  };

  const handleEnterBattle = (monsterData) => {
    setActiveMonster(monsterData);
    setCurrentScreen('battle');
  };

  const handleBattleEnd = (resultData) => {
    // Save the outcome and switch to the result screen
    setBattleResultData(resultData);
    setCurrentScreen('result');
  };

  const handleCloseResult = () => {
    if (battleResultData.won) {

      setHeroState(prevHero => ({
        ...prevHero,
        current_xp: prevHero.current_xp + battleResultData.xp,
        equipped_moves: [...prevHero.equipped_moves, battleResultData.newMove]
      }));

      setEncounters(prevMap => {
        const newMap = [...prevMap];
        const monsterIndex = newMap.findIndex(m => m.id === battleResultData.monster.id);
        
        // Mark current as completed
        newMap[monsterIndex].status = 'completed';
        
        // Unlock the next one if it exists
        if (monsterIndex + 1 < newMap.length) {
          newMap[monsterIndex + 1].status = 'next';
        }
        return newMap;
      });
    }
    
    // Return to map whether we won or lost
    setCurrentScreen('map');
  };

  return (
    <div>
      {currentScreen === 'menu' && (
        <MainMenu onStartRun={handleStartGame} />
      )}
      
      {currentScreen === 'map' && (
        <MapOverview 
          encounters={encounters} 
          onEnterBattle={handleEnterBattle} 
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