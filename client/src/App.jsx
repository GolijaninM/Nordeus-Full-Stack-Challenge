import React, { useState } from 'react';
import MainMenu from './MainMenu';
import MapOverview from './MapOverview';
import BattleScreen from './BattleScreen'; // Import the new component

function App() {
  const [currentScreen, setCurrentScreen] = useState('menu');
  const [heroState, setHeroState] = useState(null);
  const [encounters, setEncounters] = useState([]);
  const [activeMonster, setActiveMonster] = useState(null); // Track the current fight

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

  const handleBattleEnd = (result) => {
    if (result.won) {
      // Logic for granting XP and updating the map nodes will go here!
      console.log("Hero won! Returning to map...");
      setCurrentScreen('map');
    } else {
      console.log("Hero lost! Returning to map to try again...");
      setCurrentScreen('map');
    }
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
    </div>
  );
}

export default App;