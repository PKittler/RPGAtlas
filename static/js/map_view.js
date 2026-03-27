/**
 * map_view.js – Leaflet-Initialisierung und Gate/Ad-Logik für die Karten-Ansicht
 *
 * Erwartet im DOM:
 *   - <div id="map"></div>
 *   - <script id="map-data" type="application/json">…</script>
 *   - <script id="gates-data" type="application/json">…</script>
 *   - <script id="ads-data" type="application/json">…</script>
 *
 * Globale Variablen (aus Template):
 *   - GATE_FORM_URL  – URL für gate_form HTMX-Endpunkt
 *   - GATE_ADD_URL   – URL für gate_add POST-Endpunkt
 *   - IS_OWNER       – bool, ob der User Eigentümer ist
 *   - CSRF_TOKEN     – Django CSRF-Token
 */

(function () {
  'use strict';

  // ── Daten aus JSON-Script-Tags lesen ──────────────────────────────────
  const mapData  = JSON.parse(document.getElementById('map-data').textContent);
  const gatesData = JSON.parse(document.getElementById('gates-data').textContent);
  const adsData   = JSON.parse(document.getElementById('ads-data').textContent);

  // ── Leaflet-Karte initialisieren ──────────────────────────────────────
  let leafletMap;
  let imageWidth  = mapData.image_width  || 1000;
  let imageHeight = mapData.image_height || 1000;

  if (mapData.type === 'image') {
    leafletMap = L.map('map', {
      crs: L.CRS.Simple,
      minZoom: -3,
      maxZoom: 4,
      zoomSnap: 0.5,
    });

    const bounds = [[0, 0], [imageHeight, imageWidth]];
    L.imageOverlay(mapData.image_url, bounds).addTo(leafletMap);
    leafletMap.fitBounds(bounds);

  } else {
    // Kachel-Karte (Standard CRS – EPSG:3857)
    const tb = mapData.tiles_bounds || { west: -180, south: -85, east: 180, north: 85 };
    leafletMap = L.map('map', {
      minZoom: mapData.zoom_min,
      maxZoom: mapData.zoom_max,
    });

    L.tileLayer(mapData.tiles_url, {
      minZoom: mapData.zoom_min,
      maxZoom: mapData.zoom_max,
      tileSize: 256,
    }).addTo(leafletMap);

    const swLat = tb.south, swLng = tb.west;
    const neLat = tb.north, neLng = tb.east;
    leafletMap.fitBounds([[swLat, swLng], [neLat, neLng]]);
  }

  // ── Koordinaten-Umrechnung ────────────────────────────────────────────
  /**
   * Umrechnung relative Position (0-1) → Leaflet LatLng
   */
  function relToLatLng(xRel, yRel) {
    if (mapData.type === 'image') {
      // CRS.Simple: [lat=y, lng=x] — Y ist invertiert (0=oben)
      return [yRel * imageHeight, xRel * imageWidth];
    } else {
      const tb = mapData.tiles_bounds || { west: -180, south: -85, east: 180, north: 85 };
      const lng = tb.west + xRel * (tb.east - tb.west);
      const lat = tb.north - yRel * (tb.north - tb.south);
      return [lat, lng];
    }
  }

  /**
   * Umrechnung Leaflet LatLng → relative Position (0-1)
   */
  function latLngToRel(lat, lng) {
    if (mapData.type === 'image') {
      return { x: lng / imageWidth, y: lat / imageHeight };
    } else {
      const tb = mapData.tiles_bounds || { west: -180, south: -85, east: 180, north: 85 };
      return {
        x: (lng - tb.west) / (tb.east - tb.west),
        y: (tb.north - lat) / (tb.north - tb.south),
      };
    }
  }

  // ── Gate-Marker-Verwaltung ────────────────────────────────────────────
  const gateMarkers = {};  // { gateId: L.Marker }

  function buildGateDivIcon(iconType, label) {
    const svgHtml = typeof getGateIconHtml === 'function'
      ? getGateIconHtml(iconType, '#818cf8')
      : `<div style="width:32px;height:32px;background:#818cf8;border-radius:50%;"></div>`;

    return L.divIcon({
      html: `
        <div class="gate-icon-wrapper" style="position:relative;display:flex;flex-direction:column;align-items:center;cursor:pointer;">
          <div style="width:32px;height:32px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));">
            ${svgHtml}
          </div>
          <span style="
            margin-top:3px;
            font-size:11px;
            font-weight:600;
            color:#fff;
            text-shadow:0 1px 3px rgba(0,0,0,.8);
            white-space:nowrap;
            pointer-events:none;
          ">${label}</span>
        </div>`,
      className: '',
      iconSize: [80, 52],
      iconAnchor: [40, 16],
    });
  }

  function addGateMarker(gate) {
    const latlng = relToLatLng(gate.x_pos, gate.y_pos);
    const icon   = buildGateDivIcon(gate.icon_type, gate.label);
    const marker = L.marker(latlng, { icon, title: gate.label }).addTo(leafletMap);

    // Klick → Zielkarte öffnen
    marker.on('click', function () {
      if (gate.target_map_id) {
        window.location.href = `/maps/map/${gate.target_map_id}/view/`;
      }
    });

    // Rechtsklick → Löschen (nur für Eigentümer)
    if (window.IS_OWNER) {
      marker.on('contextmenu', function (e) {
        L.DomEvent.stopPropagation(e);
        openGateContextMenu(e.originalEvent, gate.id);
      });
    }

    gateMarkers[gate.id] = marker;
  }

  function removeGateMarker(gateId) {
    if (gateMarkers[gateId]) {
      leafletMap.removeLayer(gateMarkers[gateId]);
      delete gateMarkers[gateId];
    }
  }

  // Bestehende Gates laden
  gatesData.forEach(addGateMarker);

  // ── Kontext-Menü zum Gate-Löschen ─────────────────────────────────────
  let contextMenu = null;

  function openGateContextMenu(mouseEvent, gateId) {
    closeContextMenu();
    const menu = document.createElement('div');
    menu.id = 'gate-context-menu';
    menu.className = 'gate-context-menu';
    menu.style.cssText = `
      position:fixed;
      left:${mouseEvent.clientX}px;
      top:${mouseEvent.clientY}px;
      z-index:9999;
      background:#1f2937;
      border:1px solid #374151;
      border-radius:6px;
      padding:4px 0;
      min-width:140px;
      box-shadow:0 4px 12px rgba(0,0,0,.5);
    `;
    const btn = document.createElement('button');
    btn.textContent = '🗑 Gate löschen';
    btn.style.cssText = `
      display:block;width:100%;text-align:left;
      padding:8px 14px;font-size:13px;
      background:none;border:none;color:#f87171;cursor:pointer;
    `;
    btn.onmouseenter = () => { btn.style.background = '#374151'; };
    btn.onmouseleave = () => { btn.style.background = 'none'; };
    btn.onclick = () => { deleteGate(gateId); closeContextMenu(); };
    menu.appendChild(btn);
    document.body.appendChild(menu);
    contextMenu = menu;

    // Außerhalb klicken → schließen
    setTimeout(() => {
      document.addEventListener('click', closeContextMenu, { once: true });
    }, 10);
  }

  function closeContextMenu() {
    if (contextMenu) {
      contextMenu.remove();
      contextMenu = null;
    }
  }

  function deleteGate(gateId) {
    fetch(`/maps/gates/${gateId}/delete/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN, 'HX-Request': 'true' },
    }).then(resp => {
      if (resp.ok) {
        removeGateMarker(gateId);
      }
    });
  }

  // ── Gate hinzufügen (Klick-Modus) ────────────────────────────────────
  let gateAddMode = false;
  let tempMarker  = null;

  const btnAddGate = document.getElementById('btn-add-gate');
  if (btnAddGate) {
    btnAddGate.addEventListener('click', function () {
      gateAddMode = !gateAddMode;
      btnAddGate.classList.toggle('btn-primary',   gateAddMode);
      btnAddGate.classList.toggle('btn-secondary', !gateAddMode);
      btnAddGate.textContent = gateAddMode ? '✕ Abbrechen' : '+ Gate hinzufügen';
      leafletMap.getContainer().style.cursor = gateAddMode ? 'crosshair' : '';
    });
  }

  leafletMap.on('click', function (e) {
    if (!gateAddMode || !window.IS_OWNER) return;
    const rel = latLngToRel(e.latlng.lat, e.latlng.lng);
    const x = Math.max(0, Math.min(1, rel.x));
    const y = Math.max(0, Math.min(1, rel.y));

    // Temporären Marker setzen
    if (tempMarker) leafletMap.removeLayer(tempMarker);
    tempMarker = L.circleMarker(e.latlng, {
      radius: 8, color: '#6366f1', fillColor: '#818cf8', fillOpacity: 0.7,
    }).addTo(leafletMap);

    // Gate-Formular via HTMX laden
    const url = `${window.GATE_FORM_URL}?x=${x.toFixed(6)}&y=${y.toFixed(6)}`;
    htmx.ajax('GET', url, { target: '#gate-modal-content', swap: 'innerHTML' })
      .then(() => openGateModal());
  });

  // ── Gate-Modal ────────────────────────────────────────────────────────
  function openGateModal() {
    const modal = document.getElementById('gate-modal');
    if (modal) modal.removeAttribute('hidden');
  }

  function closeGateModal() {
    const modal = document.getElementById('gate-modal');
    if (modal) modal.setAttribute('hidden', '');
    if (tempMarker) { leafletMap.removeLayer(tempMarker); tempMarker = null; }
    gateAddMode = false;
    if (btnAddGate) {
      btnAddGate.textContent = '+ Gate hinzufügen';
      btnAddGate.classList.remove('btn-primary');
      btnAddGate.classList.add('btn-secondary');
    }
    leafletMap.getContainer().style.cursor = '';
  }

  const btnCloseModal = document.getElementById('btn-close-gate-modal');
  if (btnCloseModal) btnCloseModal.addEventListener('click', closeGateModal);

  // HX-Trigger: gateAdded → Marker hinzufügen + Modal schließen
  document.body.addEventListener('gateAdded', function (e) {
    addGateMarker(e.detail);
    closeGateModal();
  });

  // HX-Trigger: gateDeleted → Marker entfernen
  document.body.addEventListener('gateDeleted', function (e) {
    removeGateMarker(e.detail.id);
  });

  // ── Werbe-Icons ───────────────────────────────────────────────────────
  const adIconHtml = `
    <div style="width:28px;height:28px;background:#f59e0b;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                cursor:pointer;filter:drop-shadow(0 2px 4px rgba(0,0,0,.4));">
      <svg viewBox="0 0 20 20" fill="white" style="width:16px;height:16px;">
        <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z"/>
      </svg>
    </div>`;

  adsData.forEach(function (ad) {
    const latlng = relToLatLng(ad.x_pos, ad.y_pos);
    const icon   = L.divIcon({ html: adIconHtml, className: '', iconSize: [28, 28], iconAnchor: [14, 14] });
    const marker = L.marker(latlng, { icon, zIndexOffset: -100 }).addTo(leafletMap);

    marker.on('click', function () {
      htmx.ajax('GET', `/maps/ads/${ad.id}/modal/`, {
        target: '#ad-modal-content',
        swap: 'innerHTML',
      }).then(() => {
        const modal = document.getElementById('ad-modal');
        if (modal) modal.removeAttribute('hidden');
      });
    });
  });

  // Ad-Modal schließen
  const btnCloseAd = document.getElementById('btn-close-ad-modal');
  if (btnCloseAd) {
    btnCloseAd.addEventListener('click', function () {
      const modal = document.getElementById('ad-modal');
      if (modal) modal.setAttribute('hidden', '');
    });
  }

  // ── Globale Exports für map_elements.js ──────────────────────────────
  window.leafletMap   = leafletMap;
  window.relToLatLng  = relToLatLng;
  window.latLngToRel  = latLngToRel;

})();
