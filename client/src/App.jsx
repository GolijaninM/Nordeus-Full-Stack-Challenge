import { useState } from 'react'
import MainMenu from './MainMenu'

function App() {

  const handleStartGame = () => {
    console.log("Hello, World!");
  };

  return (
    <div>
      <MainMenu onStartRun={handleStartGame} />
    </div>
  )
}

export default App
