/**
 * map_elements.js – Leaflet-Marker-Logik für Karten-Elemente (NPC/Item/Trigger)
 *
 * Erwartet im DOM:
 *   - <script id="elements-data" type="application/json">…</script>
 *
 * Globale Variablen (aus Template):
 *   - window.leafletMap          – Leaflet-Map-Instanz (aus map_view.js)
 *   - window.relToLatLng         – Koordinaten-Hilfsfunktion (aus map_view.js)
 *   - window.latLngToRel         – Koordinaten-Hilfsfunktion (aus map_view.js)
 *   - window.IS_OWNER            – bool
 *   - window.CSRF_TOKEN          – Django CSRF-Token
 *   - window.ELEMENT_FORM_URL    – URL für element_type_select
 *   - window.ELEMENT_ADD_URL     – URL für element_add POST
 */

(function () {
  'use strict';

  var elementsData = JSON.parse(document.getElementById('elements-data').textContent);
  var elementMarkers = {};  // { elementId: L.Marker }

  // ── Icon-Builder ─────────────────────────────────────────────────────
  var ELEMENT_COLORS = {
    npc:     '#60a5fa',
    item:    '#fbbf24',
    trigger: '#f97316',
  };

  function buildElementDivIcon(elementType) {
    var color = ELEMENT_COLORS[elementType] || '#a78bfa';
    var svgHtml = typeof getElementIconHtml === 'function'
      ? getElementIconHtml(elementType, color)
      : '<div style="width:28px;height:28px;background:' + color + ';border-radius:50%;"></div>';

    return L.divIcon({
      html: '<div style="width:28px;height:28px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));cursor:pointer;">'
            + svgHtml
            + '</div>',
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
  }

  // ── Marker hinzufügen ────────────────────────────────────────────────
  function addElementMarker(el) {
    var latlng = window.relToLatLng(el.x_pos, el.y_pos);
    var icon   = buildElementDivIcon(el.element_type);
    var marker = L.marker(latlng, { icon: icon, zIndexOffset: 50 }).addTo(window.leafletMap);

    // Linksklick → Popup-Modal via HTMX laden
    marker.on('click', function () {
      openElementPopup(el.id);
    });

    // Rechtsklick → Löschen (nur Eigentümer)
    if (window.IS_OWNER) {
      marker.on('contextmenu', function (e) {
        L.DomEvent.stopPropagation(e);
        openElementContextMenu(e.originalEvent, el.id);
      });
    }

    elementMarkers[el.id] = marker;
  }

  function removeElementMarker(elementId) {
    if (elementMarkers[elementId]) {
      window.leafletMap.removeLayer(elementMarkers[elementId]);
      delete elementMarkers[elementId];
    }
  }

  // Bestehende Elemente laden
  elementsData.forEach(addElementMarker);

  // ── Popup-Modal ───────────────────────────────────────────────────────
  function openElementPopup(elementId) {
    var url = '/maps/elements/' + elementId + '/modal/';
    htmx.ajax('GET', url, { target: '#element-popup-modal-content', swap: 'innerHTML' })
      .then(function () {
        var modal = document.getElementById('element-popup-modal');
        if (modal) modal.removeAttribute('hidden');
      });
  }

  function closeElementPopup() {
    var modal = document.getElementById('element-popup-modal');
    if (modal) modal.setAttribute('hidden', '');
  }

  var btnClosePopup = document.getElementById('btn-close-element-popup-modal');
  if (btnClosePopup) btnClosePopup.addEventListener('click', closeElementPopup);

  // elementActionDone → Modal schließen
  document.body.addEventListener('elementActionDone', function () {
    closeElementPopup();
  });

  // ── Kontext-Menü zum Löschen ─────────────────────────────────────────
  var elementContextMenu = null;

  function openElementContextMenu(mouseEvent, elementId) {
    closeElementContextMenu();
    var menu = document.createElement('div');
    menu.style.cssText = 'position:fixed;left:' + mouseEvent.clientX + 'px;top:' + mouseEvent.clientY + 'px;'
      + 'z-index:9999;background:#1f2937;border:1px solid #374151;border-radius:6px;'
      + 'padding:4px 0;min-width:150px;box-shadow:0 4px 12px rgba(0,0,0,.5);';

    var btn = document.createElement('button');
    btn.textContent = 'Element löschen';
    btn.style.cssText = 'display:block;width:100%;text-align:left;padding:8px 14px;'
      + 'font-size:13px;background:none;border:none;color:#f87171;cursor:pointer;';
    btn.onmouseenter = function () { btn.style.background = '#374151'; };
    btn.onmouseleave = function () { btn.style.background = 'none'; };
    btn.onclick = function () { deleteElement(elementId); closeElementContextMenu(); };
    menu.appendChild(btn);
    document.body.appendChild(menu);
    elementContextMenu = menu;

    setTimeout(function () {
      document.addEventListener('click', closeElementContextMenu, { once: true });
    }, 10);
  }

  function closeElementContextMenu() {
    if (elementContextMenu) {
      elementContextMenu.remove();
      elementContextMenu = null;
    }
  }

  function deleteElement(elementId) {
    fetch('/maps/elements/' + elementId + '/delete/', {
      method: 'POST',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN, 'HX-Request': 'true' },
    }).then(function (resp) {
      if (resp.ok) {
        removeElementMarker(elementId);
      }
    });
  }

  // ── Element-Add-Modal (Eigentümer) ────────────────────────────────────
  var elementAddMode = false;
  var tempElementMarker = null;

  var btnAddElement = document.getElementById('btn-add-element');
  if (btnAddElement) {
    btnAddElement.addEventListener('click', function () {
      elementAddMode = !elementAddMode;
      btnAddElement.classList.toggle('btn-primary',   elementAddMode);
      btnAddElement.classList.toggle('btn-secondary', !elementAddMode);
      btnAddElement.textContent = elementAddMode ? 'Abbrechen' : '+ Element';
      window.leafletMap.getContainer().style.cursor = elementAddMode ? 'crosshair' : '';
    });
  }

  window.leafletMap.on('click', function (e) {
    if (!elementAddMode || !window.IS_OWNER) return;
    var rel = window.latLngToRel(e.latlng.lat, e.latlng.lng);
    var x = Math.max(0, Math.min(1, rel.x));
    var y = Math.max(0, Math.min(1, rel.y));

    // Temporären Marker setzen
    if (tempElementMarker) window.leafletMap.removeLayer(tempElementMarker);
    tempElementMarker = L.circleMarker(e.latlng, {
      radius: 8, color: '#a78bfa', fillColor: '#c4b5fd', fillOpacity: 0.7,
    }).addTo(window.leafletMap);

    // Typ-Auswahl via HTMX laden
    var url = window.ELEMENT_FORM_URL + '?x=' + x.toFixed(6) + '&y=' + y.toFixed(6);
    htmx.ajax('GET', url, { target: '#element-add-modal-content', swap: 'innerHTML' })
      .then(function () { openElementAddModal(); });
  });

  function openElementAddModal() {
    var modal = document.getElementById('element-add-modal');
    if (modal) modal.removeAttribute('hidden');
  }

  function closeElementAddModal() {
    var modal = document.getElementById('element-add-modal');
    if (modal) modal.setAttribute('hidden', '');
    if (tempElementMarker) { window.leafletMap.removeLayer(tempElementMarker); tempElementMarker = null; }
    elementAddMode = false;
    if (btnAddElement) {
      btnAddElement.textContent = '+ Element';
      btnAddElement.classList.remove('btn-primary');
      btnAddElement.classList.add('btn-secondary');
    }
    window.leafletMap.getContainer().style.cursor = '';
  }

  var btnCloseAddModal = document.getElementById('btn-close-element-add-modal');
  if (btnCloseAddModal) btnCloseAddModal.addEventListener('click', closeElementAddModal);

  // HX-Trigger: elementAdded → Marker hinzufügen + Modal schließen
  document.body.addEventListener('elementAdded', function (e) {
    addElementMarker(e.detail);
    closeElementAddModal();
  });

  // HX-Trigger: elementDeleted → Marker entfernen
  document.body.addEventListener('elementDeleted', function (e) {
    removeElementMarker(e.detail.id);
  });

})();
