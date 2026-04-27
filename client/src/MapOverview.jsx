import React from 'react';
import './MapOverview.css';
import forestMap from '../images/forest-map.jpg'; 

const MapOverview = ({ encounters, onEnterBattle }) => {
  return (
    <div className="map-page-container">

      <div 
        className="game-board-wrapper" 
        style={{ backgroundImage: `url(${forestMap})` }}
      >
        {encounters.map((encounter, index) => {
          const isNext = encounter.status === 'next';
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
    </div>
  );
};

export default MapOverview;