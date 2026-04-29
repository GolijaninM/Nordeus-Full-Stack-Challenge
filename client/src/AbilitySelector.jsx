import React, { useState, useEffect } from 'react';
import './AbilitySelector.css';

const AbilitySelector = ({ heroState, allLearnedMoves, allLearnedMovesDetails, onClose, onConfirm }) => {
  const [selectedAbilities, setSelectedAbilities] = useState([]);
  const MAX_ABILITIES = 4;

  useEffect(() => {
    // Initialize selected with currently equipped abilities
    const equipped = heroState.equipped_moves.map(m => m.id);
    setSelectedAbilities(equipped);
  }, [heroState]);

  const toggleAbility = (abilityId) => {
    setSelectedAbilities(prev => {
      if (prev.includes(abilityId)) {
        // Remove if already selected
        return prev.filter(id => id !== abilityId);
      } else {
        // Add if under limit
        if (prev.length < MAX_ABILITIES) {
          return [...prev, abilityId];
        }
        return prev;
      }
    });
  };

  const handleConfirm = () => {
    onConfirm(selectedAbilities);
    onClose();
  };

  const isAbilitySelected = (abilityId) => selectedAbilities.includes(abilityId);
  const canSelectMore = selectedAbilities.length < MAX_ABILITIES;

  return (
    <div className="ability-selector-overlay">
      <div className="ability-selector-modal">
        <div className="selector-header">
          <h2>Select Abilities ({selectedAbilities.length}/{MAX_ABILITIES})</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="selector-body">
          <div className="abilities-grid">
            {allLearnedMoves.map(moveId => {
              const ability = allLearnedMovesDetails[moveId];
              if (!ability) return null;
              
              return (
                <div
                  key={moveId}
                  className={`ability-card ${ability.type} ${isAbilitySelected(moveId) ? 'selected' : ''} ${!canSelectMore && !isAbilitySelected(moveId) ? 'disabled' : ''}`}
                  onClick={() => toggleAbility(moveId)}
                >
                  <div className="ability-type-badge">{ability.type}</div>
                  <div className="ability-name">{ability.name}</div>
                  <div className="ability-effect">{ability.effect}</div>
                  {isAbilitySelected(moveId) && (
                    <div className="selected-checkmark">✓</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="selector-footer">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button 
            className="btn-confirm" 
            onClick={handleConfirm}
            disabled={selectedAbilities.length === 0}
          >
            Confirm ({selectedAbilities.length}/{MAX_ABILITIES})
          </button>
        </div>
      </div>
    </div>
  );
};

export default AbilitySelector;
