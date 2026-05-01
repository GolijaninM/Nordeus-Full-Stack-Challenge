import React, { useState, useEffect, useRef } from 'react';
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

  // Tooltip state for floating tooltip rendered in the overlay
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, content: null });
  const overlayRef = useRef(null);

  const showTooltip = (e, ability) => {
    const rect = e.currentTarget.getBoundingClientRect();
    // position above the card, centered
    const x = rect.left + rect.width / 2;
    const y = rect.top - 10; // 10px above the card
    setTooltip({ visible: true, x, y, content: ability });
  };

  const hideTooltip = () => setTooltip({ visible: false, x: 0, y: 0, content: null });

  const handleConfirm = () => {
    onConfirm(selectedAbilities);
    onClose();
  };

  const isAbilitySelected = (abilityId) => selectedAbilities.includes(abilityId);
  const canSelectMore = selectedAbilities.length < MAX_ABILITIES;

  return (
    <div className="ability-selector-overlay" ref={overlayRef}>
      {/* Floating tooltip placed at overlay level so it can't be clipped by modal children */}
      {tooltip.visible && tooltip.content && (
        <div
          className="floating-tooltip"
          style={{ left: tooltip.x, top: tooltip.y, position: 'fixed' }}
          role="tooltip"
        >
          {tooltip.content.description && <div className="tooltip-desc">{tooltip.content.description}</div>}
        </div>
      )}

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
                  onMouseEnter={(e) => showTooltip(e, ability)}
                  onMouseLeave={hideTooltip}
                >
                  <div className="ability-type-badge">{ability.type}</div>
                  <div className="ability-name">{ability.name}</div>
                  <div className="ability-effect">{ability.effect}</div>
                  {/* inline tooltip removed — using floating tooltip in overlay */}
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
