import React from 'react';
import './Shop.css';
import roguesImage from '../../../assets/characters/rogues.png';
import topElevenImage from '../../../assets/characters/top-eleven.png';
import golfRivalImage from '../../../assets/characters/golf-rival.png';
import LogicalCropImage from '../../../components/LogicalCropImage';

const Shop = ({ heroState, onBuySkin, onEquipSkin, onClose }) => {
  if (!heroState || !heroState.available_skins) {
    return null;
  }

  return (
    <div className="shop-overlay">
      <div className="shop-modal">
        <div className="shop-header">
          <h2>Skin Shop</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="shop-body">
          <div className="coins-display">
            💰 Coins: <span className="coins-amount">{heroState.coins ?? 0}</span>
          </div>
          
          <div className="skins-grid">
            {Object.entries(heroState.available_skins)
              .sort(([, skinA], [, skinB]) => {
                // Put secret easter-egg skins at the end regardless of cost
                const aSecret = skinA.image === 'easter-egg';
                const bSecret = skinB.image === 'easter-egg';
                if (aSecret && !bSecret) return 1;
                if (!aSecret && bSecret) return -1;
                return (skinA.cost || 0) - (skinB.cost || 0);
              })
              .map(([skinId, skin]) => {
              const isOwned = skin.unlocked;
              const isEquipped = heroState.current_skin === skinId;
              const canAfford = (heroState.coins ?? 0) >= skin.cost;

              // Convert [x, y] coords to cropCoords for LogicalCropImage
              const cropCoords = {
                sx: skin.coords[0],
                sy: skin.coords[1],
                sWidth: 32,
                sHeight: 32
              };

              return (
                <div key={skinId} className={`skin-card ${isEquipped ? 'equipped' : ''}`}>
                  {/* Skin preview using LogicalCropImage */}
                  <div className="skin-preview">
                    {skin.name === '???' && !skin.unlocked ? (
                      // Full black silhouette for secret locked skins
                      <div style={{ width: '64px', height: '64px', background: '#000', borderRadius: 4 }} />
                    ) : skin.image === 'easter-egg' ? (
                      // Show separate easter-egg PNG files
                      <img 
                        src={skinId === 'knight_secret_left' ? golfRivalImage : topElevenImage}
                        alt={skin.name}
                        style={{ maxWidth: '90%', maxHeight: '100%', objectFit: 'contain' }}
                      />
                    ) : (
                      <LogicalCropImage 
                        src={roguesImage}
                        cropCoords={cropCoords}
                        displayScale={3}
                      />
                    )}
                  </div>
                  
                  <div className="skin-info">
                    <div className="skin-name">{skin.name}</div>
                    {isOwned ? (
                      <>
                        {isEquipped ? (
                          <div className="skin-status equipped-badge">✓ Equipped</div>
                        ) : (
                          <button
                            className="skin-btn equip-btn"
                            onClick={() => onEquipSkin(skinId)}
                          >
                            Equip
                          </button>
                        )}
                      </>
                    ) : (
                      // For secret skins (easter-egg) do not allow purchase — only unlock via collectibles
                      skin.image === 'easter-egg' ? (
                        <div className="skin-locked">Locked</div>
                      ) : (
                        <button
                          className={`skin-btn buy-btn ${!canAfford ? 'disabled' : ''}`}
                          onClick={() => onBuySkin(skinId)}
                          disabled={!canAfford}
                        >
                          {skin.cost} coins
                        </button>
                      )
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="shop-footer">
          <button className="btn-cancel" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default Shop;
