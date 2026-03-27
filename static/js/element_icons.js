/**
 * element_icons.js – SVG-Icons für Karten-Elemente (NPC, Item, Trigger)
 */

var ELEMENT_ICONS = {
  npc: function (color) {
    color = color || '#60a5fa';
    return '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
      + '<circle cx="16" cy="10" r="6" fill="' + color + '"/>'
      + '<path d="M4 30 C4 21.163 9.163 16 16 16 C22.837 16 28 21.163 28 30" fill="' + color + '"/>'
      + '</svg>';
  },
  item: function (color) {
    color = color || '#fbbf24';
    return '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
      + '<rect x="4" y="8" width="24" height="6" rx="2" fill="' + color + '"/>'
      + '<rect x="6" y="14" width="20" height="12" rx="2" fill="' + color + '"/>'
      + '<path d="M4 11 H28" stroke="#92400e" stroke-width="1.5"/>'
      + '<rect x="13" y="17" width="6" height="5" rx="1" fill="#92400e"/>'
      + '<path d="M13 8 C13 6 14 5 16 5 C18 5 19 6 19 8" stroke="' + color + '" stroke-width="2" fill="none"/>'
      + '</svg>';
  },
  trigger: function (color) {
    color = color || '#f97316';
    return '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
      + '<circle cx="16" cy="27" r="4" fill="' + color + '"/>'
      + '<rect x="14" y="11" width="4" height="18" rx="2" fill="' + color + '"/>'
      + '<circle cx="16" cy="8" r="6" fill="' + color + '"/>'
      + '<circle cx="16" cy="8" r="3" fill="#fff" opacity="0.5"/>'
      + '</svg>';
  },
};

/**
 * Gibt den HTML-String für ein Element-Icon zurück.
 * @param {string} elementType - 'npc' | 'item' | 'trigger'
 * @param {string} color       - CSS-Farbwert (optional)
 * @returns {string}
 */
function getElementIconHtml(elementType, color) {
  var fn = ELEMENT_ICONS[elementType];
  return fn ? fn(color) : ELEMENT_ICONS.npc(color);
}
