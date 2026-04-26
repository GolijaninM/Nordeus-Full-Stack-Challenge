import { useState } from 'react'
import MainMenu from './MainMenu'

function App() {

  const handleStartGame = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/start-run');
      
      if (!response.ok) {
        throw new Error(`Server error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log(data);

    } catch (error) {
      console.error("Failed to fetch game data:", error);
    }
  };

  return (
    <div>
      <MainMenu onStartRun={handleStartGame} />
    </div>
  )
}

export default App
