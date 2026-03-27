/**
 * gate_icons.js – SVG-Definitionen für alle Gate-Icon-Typen
 * Rückgabe: SVG-HTML-String für L.divIcon
 */
const GATE_ICONS = {
  city: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="9" y="9" width="14" height="18"/><rect x="9" y="5" width="3" height="4"/>
    <rect x="14.5" y="5" width="3" height="4"/><rect x="20" y="5" width="3" height="4"/>
    <rect x="13" y="20" width="6" height="7"/><rect x="13" y="12" width="3" height="4"/>
    <rect x="18" y="12" width="3" height="4"/></svg>`,

  village: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="6" y="16" width="20" height="11"/><polyline points="3,16 16,5 29,16"/>
    <rect x="13" y="21" width="6" height="6"/><rect x="19" y="7" width="3" height="5"/></svg>`,

  cave: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="2,28 16,4 30,28"/>
    <path d="M10 28 Q10 21 16 21 Q22 21 22 28"/></svg>`,

  plateau: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="7" y1="13" x2="25" y2="13"/>
    <path d="M2 28 L7 13 L25 13 L30 28 Z"/>
    <line x1="2" y1="28" x2="30" y2="28"/></svg>`,

  canyon: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="2,4 2,28 12,28 12,11"/>
    <polyline points="20,11 20,28 30,28 30,4"/>
    <path d="M12 28 Q16 23 20 28"/></svg>`,

  trapdoor: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="4" y="9" width="24" height="16"/><line x1="16" y1="9" x2="16" y2="25"/>
    <circle cx="12" cy="17" r="2"/><circle cx="20" cy="17" r="2"/></svg>`,

  stairs: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="4,28 4,22 10,22 10,16 16,16 16,10 22,10 22,4 28,4"/>
    <line x1="4" y1="28" x2="28" y2="28"/><line x1="28" y1="4" x2="28" y2="28"/></svg>`,

  ladder: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="10" y1="2" x2="10" y2="30"/><line x1="22" y1="2" x2="22" y2="30"/>
    <line x1="10" y1="8" x2="22" y2="8"/><line x1="10" y1="14" x2="22" y2="14"/>
    <line x1="10" y1="20" x2="22" y2="20"/><line x1="10" y1="26" x2="22" y2="26"/></svg>`,

  hole: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <ellipse cx="16" cy="22" rx="12" ry="5"/>
    <ellipse cx="16" cy="20" rx="7" ry="3" stroke-dasharray="3 2"/></svg>`,
};

/**
 * Gibt das SVG-HTML für einen Gate-Icon-Typ zurück.
 * @param {string} iconType - einer der 9 Gate-Typen
 * @param {string} color - CSS-Farbe (default: '#6366f1')
 * @returns {string} HTML-String
 */
function getGateIconHtml(iconType, color = '#6366f1') {
  const svg = GATE_ICONS[iconType] || GATE_ICONS['cave'];
  return svg.replace('stroke="currentColor"', `stroke="${color}"`);
}
