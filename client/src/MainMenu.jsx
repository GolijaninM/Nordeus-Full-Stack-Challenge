import React from 'react';
import './MainMenu.css';

const MainMenu = ({ onStartRun, onContinueRun, savedRunExists }) => {
  
  // Handling the "Exit" button on the web
  const handleExit = () => {
    alert("Thanks for playing! You can safely close this tab.");
  };

  return (
    <div className="main-menu-container">
      <div className="menu-content">
        <h1 className="game-title">Shadows of Nordeus</h1>
        
        <div className="button-group">
          <button className="menu-button start-btn" onClick={onStartRun}>
            Start New Run
          </button>

          {savedRunExists && (
            <button className="menu-button continue-btn" onClick={onContinueRun}>
              Continue Run
            </button>
          )}
          
          <button className="menu-button exit-btn" onClick={handleExit}>
            Exit Game
          </button>
        </div>
      </div>
    </div>
  );
};

export default MainMenu;