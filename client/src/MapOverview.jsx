import React, { useState } from 'react';
import './MapOverview.css';
import forestMap from '../images/forest-map.png';
import AbilitySelector from './AbilitySelector';
import StatUpgradePanel from './StatUpgradePanel';

const MapOverview = ({ encounters, heroState, allLearnedMoves, allLearnedMovesDetails, onEnterBattle, onSelectAbilities, onUpgradeStat }) => {
  const [showAbilitySelector, setShowAbilitySelector] = useState(false);

  const handleSelectAbilities = (selectedMoveIds) => {
    onSelectAbilities(selectedMoveIds);
  };

  return (
    <div className="map-page-container">
      {/* Ability Selector Button */}
      <button className="ability-selector-btn" onClick={() => setShowAbilitySelector(true)}>
        ⚔️ Select Abilities
      </button>

      <StatUpgradePanel heroState={heroState} onUpgradeStat={onUpgradeStat} />

      <div 
        className="game-board-wrapper" 
        style={{ backgroundImage: `url(${forestMap})` }}
      >
        {encounters.map((encounter, index) => {
          const isNext = encounter.status === 'next' || encounter.status === 'completed';
          const isLocked = encounter.status === 'locked';

          return (
            <div 
              key={encounter.id}
              className={`level-node-wrapper pos-${index}`}
            >
              <div 
                className={`level-node ${encounter.status}`}
                onClick={() => isNext && onEnterBattle(encounter)}
              >
                <span className="node-number">{encounter.order}</span>
              </div>
              
              <div className="node-info">
                <span className="monster-name">
                  {isLocked ? "???" : encounter.name}
                </span>
                {!isLocked && <span className="monster-hp">HP: {encounter.max_hp}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Ability Selector Modal */}
      {showAbilitySelector && heroState && (
        <AbilitySelector
          heroState={heroState}
          allLearnedMoves={allLearnedMoves}
          allLearnedMovesDetails={allLearnedMovesDetails}
          onClose={() => setShowAbilitySelector(false)}
          onConfirm={handleSelectAbilities}
        />
      )}
    </div>
  );
};

export default MapOverview;