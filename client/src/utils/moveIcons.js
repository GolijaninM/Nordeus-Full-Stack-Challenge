// Dynamically import all move icons using Vite's import.meta.glob
const moveIcons = import.meta.glob('../assets/moves/*.png', { eager: true });

// Create a map of move IDs to their imported image URLs
const moveIconMap = {};

Object.entries(moveIcons).forEach(([path, module]) => {
  // Extract filename from path (e.g., "arcane_surge" from "../../assets/moves/arcane_surge.png")
  const filename = path.split('/').pop().replace('.png', '');
  moveIconMap[filename] = module.default;
});

export const getMoveIcon = (moveId) => {
  return moveIconMap[moveId] || '';
};

export default moveIconMap;
