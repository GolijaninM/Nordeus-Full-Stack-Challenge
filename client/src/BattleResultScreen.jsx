import React from 'react';
import './BattleResultScreen.css';

const BattleResultScreen = ({ resultData, onContinue }) => {
  const { won, monster, xp, newMove } = resultData;

  return (
    <div className="result-screen-container">
      <div className={`result-modal ${won ? 'victory' : 'defeat'}`}>
        
        <h1 className="result-title">
          {won ? 'VICTORY' : 'DEFEAT'}
        </h1>
        
        <p className="result-subtitle">
          {won 
            ? `You defeated the ${monster.name}!` 
            : `You were struck down by the ${monster.name}.`}
        </p>

        {won && (
          <div className="rewards-container">
            <div className="reward-item">
              <span className="reward-label">XP Gained:</span>
              <span className="reward-value xp-text">+{xp} XP</span>
            </div>
            
            <div className="reward-item">
              <span className="reward-label">Move Learned:</span>
              <span className="reward-value move-text">
                {newMove.name} ({newMove.type})
              </span>
            </div>
          </div>
        )}

        <button className="continue-btn" onClick={onContinue}>
          {won ? 'Return to Map' : 'Try Again'}
        </button>
        
      </div>
    </div>
  );
};

export default BattleResultScreen;