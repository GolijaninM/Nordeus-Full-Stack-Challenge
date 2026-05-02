import React from 'react';
import './StatUpgradePanel.css';

const BASE_STAT_UPGRADE_COST = 20;
const STAT_UPGRADE_AMOUNT = 5;
const STAT_UPGRADE_COST_INCREMENT = 10;

const calculateUpgradeCost = (upgradeCount) => {
  return BASE_STAT_UPGRADE_COST + (upgradeCount * STAT_UPGRADE_COST_INCREMENT);
};

const STAT_LABELS = {
  attack: 'Attack',
  defense: 'Defense',
  max_hp: 'Max Health',
  magic: 'Magic'
};

const STAT_KEYS = ['attack', 'defense', 'magic', 'max_hp'];

const StatUpgradePanel = ({ heroState, onUpgradeStat }) => {
  const availableXp = heroState?.current_xp ?? 0;

  return (
    <div className="stat-upgrade-panel">
      <div className="stat-upgrade-header">
        <div>
          <h2>Stat Upgrades</h2>
        </div>
        <div className="stat-upgrade-xp">
          <span>XP</span>
          <strong>{availableXp}</strong>
        </div>
      </div>

      <div className="stat-upgrade-list">
        {STAT_KEYS.map(statKey => {
          const currentValue = heroState?.[statKey] ?? 0;
          const upgradeCount = heroState?.stat_upgrades?.[statKey] ?? 0;
          const upgradeCost = calculateUpgradeCost(upgradeCount);
          const canUpgrade = availableXp >= upgradeCost;

          return (
            <div key={statKey} className="stat-upgrade-row">
              <div className="stat-upgrade-info">
                <span className="stat-upgrade-name">{STAT_LABELS[statKey]}</span>
                <span className="stat-upgrade-value">{currentValue}</span>
              </div>

              <button
                type="button"
                className="stat-upgrade-button"
                onClick={() => onUpgradeStat(statKey)}
                disabled={!canUpgrade}
              >
                +{STAT_UPGRADE_AMOUNT} for {upgradeCost} XP
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StatUpgradePanel;