// Fit the projected grid in BOTH visible dimensions, reserving space for controls.
export function gridMapSize(width, height, gridWidth, gridHeight, topPadding, bottomPadding = 20, sidePadding = 20) {
  if (![width, height, gridWidth, gridHeight, topPadding].every(Number.isFinite) || gridWidth <= 0 || gridHeight <= 0) return {width, height};
  const usableWidth = Math.max(1, width - 2 * sidePadding);
  const usableHeight = Math.max(1, height - topPadding - bottomPadding);
  const scale = Math.min(usableWidth / gridWidth, usableHeight / gridHeight);
  return {
    width: Math.min(width, Math.ceil(gridWidth * scale + 2 * sidePadding)),
    height: Math.min(height, Math.ceil(gridHeight * scale + topPadding + bottomPadding)),
  };
}
