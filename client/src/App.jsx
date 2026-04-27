import { useState } from 'react'
import MainMenu from './MainMenu'
import MapOverview from './MapOverview'

function App() {

  const [currentScreen, setCurrentScreen] = useState('menu');
  
  const [heroState, setHeroState] = useState(null);
  const [encounters, setEncounters] = useState([]);

  const handleStartGame = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/start-run');
      
      if (!response.ok) {
        throw new Error(`Server error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      
      setHeroState(data.hero);
      setEncounters(data.run_encounters);
      setCurrentScreen('map');

    } catch (error) {
      console.error("Failed to fetch game data:", error);
    }
  };

  const handleEnterBattle = (monsterData) => {
    console.log("Entering battle with:", monsterData);
  };

  return (
    <div>
      {currentScreen === 'menu' && <MainMenu onStartRun={handleStartGame} />}
      {currentScreen === 'map' && <MapOverview encounters={encounters} onEnterBattle={handleEnterBattle} />}
    </div>
  )
}

export default App
