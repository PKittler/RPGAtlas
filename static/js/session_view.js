/**
 * session_view.js – Leaflet + WebSocket für die laufende Spiel-Session
 *
 * Globale Variablen (aus Template):
 *   window.SESSION_ID            – Numerische Session-ID
 *   window.IS_GAMEMASTER         – bool
 *   window.CURRENT_MAP_ID        – aktuelle Map-ID
 *   window.CSRF_TOKEN            – Django CSRF-Token
 *   window.CHARACTER_PATH_BASE   – z.B. "/sessions/5/character/"
 */

(function () {
  'use strict';

  // ── JSON-Daten aus DOM lesen ───────────────────────────────────────────
  const sessionData    = JSON.parse(document.getElementById('session-data').textContent);
  const mapData        = JSON.parse(document.getElementById('map-data').textContent);
  const gatesData      = JSON.parse(document.getElementById('gates-data').textContent);
  const elementsData   = JSON.parse(document.getElementById('elements-data').textContent);
  const charactersData = JSON.parse(document.getElementById('characters-data').textContent);

  const IS_GM       = window.IS_GAMEMASTER;
  const CURRENT_MAP = window.CURRENT_MAP_ID;

  // ── Leaflet-Karte initialisieren ────────────────────────────────────────
  let leafletMap;
  const imageWidth  = mapData.image_width  || 1000;
  const imageHeight = mapData.image_height || 1000;

  if (mapData.type === 'image') {
    leafletMap = L.map('session-map', {
      crs: L.CRS.Simple,
      minZoom: -3,
      maxZoom: 4,
      zoomSnap: 0.5,
    });
    const bounds = [[0, 0], [imageHeight, imageWidth]];
    L.imageOverlay(mapData.image_url, bounds).addTo(leafletMap);
    leafletMap.fitBounds(bounds);
  } else {
    const tb = mapData.tiles_bounds || { west: -180, south: -85, east: 180, north: 85 };
    leafletMap = L.map('session-map', {
      minZoom: mapData.zoom_min,
      maxZoom: mapData.zoom_max,
    });
    L.tileLayer(mapData.tiles_url, {
      minZoom: mapData.zoom_min,
      maxZoom: mapData.zoom_max,
      tileSize: 256,
    }).addTo(leafletMap);
    leafletMap.fitBounds([[tb.south, tb.west], [tb.north, tb.east]]);
  }

  // ── Koordinaten-Umrechnung ─────────────────────────────────────────────
  function relToLatLng(x, y) {
    if (mapData.type === 'image') {
      return [y * imageHeight, x * imageWidth];
    }
    const tb = mapData.tiles_bounds || { west: -180, south: -85, east: 180, north: 85 };
    return [
      tb.north - y * (tb.north - tb.south),
      tb.west  + x * (tb.east  - tb.west),
    ];
  }

  function latLngToRel(lat, lng) {
    if (mapData.type === 'image') {
      return { x: lng / imageWidth, y: lat / imageHeight };
    }
    const tb = mapData.tiles_bounds || { west: -180, south: -85, east: 180, north: 85 };
    return {
      x: (lng - tb.west)  / (tb.east  - tb.west),
      y: (tb.north - lat) / (tb.north - tb.south),
    };
  }

  // ── Gate-Marker (nicht-interaktiv, nur zur Anzeige) ───────────────────
  if (typeof getGateIconHtml === 'function') {
    gatesData.forEach(function (gate) {
      const latlng = relToLatLng(gate.x_pos, gate.y_pos);
      const icon = L.divIcon({
        html: '<div style="width:28px;height:28px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));">'
              + getGateIconHtml(gate.icon_type, '#818cf8') + '</div>',
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });
      L.marker(latlng, { icon: icon, interactive: false }).addTo(leafletMap);
    });
  }

  // ── Element-Marker (nur Anzeige, Click öffnet Modal) ─────────────────
  const ELEMENT_COLORS = { npc: '#60a5fa', item: '#fbbf24', trigger: '#f97316' };

  if (typeof getElementIconHtml === 'function') {
    elementsData.forEach(function (el) {
      const color = ELEMENT_COLORS[el.element_type] || '#a78bfa';
      const latlng = relToLatLng(el.x_pos, el.y_pos);
      const icon = L.divIcon({
        html: '<div style="width:28px;height:28px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5));cursor:pointer;">'
              + getElementIconHtml(el.element_type, color) + '</div>',
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });
      const marker = L.marker(latlng, { icon: icon, zIndexOffset: 50 }).addTo(leafletMap);
      marker.on('click', function () {
        htmx.ajax('GET', '/maps/elements/' + el.id + '/modal/', {
          target: '#element-popup-modal-content',
          swap: 'innerHTML',
        }).then(function () {
          var m = document.getElementById('element-popup-modal');
          if (m) m.removeAttribute('hidden');
        });
      });
    });
  }

  // ── Figur-Marker-Verwaltung ───────────────────────────────────────────
  const characterMarkers     = {};   // { charId: L.Marker }
  const characterLastPos     = {};   // { charId: {x, y} }
  const characterMovementLines = {}; // { charId: L.Polyline } – rote Bewegungslinie
  const characterPaths       = {};   // { charId: L.Polyline } – historischer Pfad
  let   selectedCharacters   = new Set();  // für Multi-Drag

  function buildCharacterIcon(char) {
    const color    = char.color || '#6366f1';
    const initials = char.name.charAt(0).toUpperCase();
    const border   = char.is_eliminated ? '#6b7280' : color;
    const opacity  = char.is_eliminated ? '0.45' : '1';
    return L.divIcon({
      html: '<div style="'
            + 'width:36px;height:36px;border-radius:50%;'
            + 'background:' + color + ';'
            + 'border:3px solid ' + border + ';'
            + 'display:flex;align-items:center;justify-content:center;'
            + 'font-weight:700;font-size:15px;color:#fff;'
            + 'cursor:' + (IS_GM ? 'grab' : 'pointer') + ';'
            + 'opacity:' + opacity + ';'
            + 'filter:drop-shadow(0 2px 6px rgba(0,0,0,.6));'
            + '">' + initials + '</div>',
      className: '',
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });
  }

  function addCharacterMarker(char) {
    if (!char.on_current_map) return;
    const latlng = relToLatLng(char.x_pos, char.y_pos);
    const marker = L.marker(latlng, {
      icon: buildCharacterIcon(char),
      title: char.name,
      draggable: IS_GM && !char.is_eliminated,
      zIndexOffset: 100,
    }).addTo(leafletMap);

    characterLastPos[char.id] = { x: char.x_pos, y: char.y_pos };

    if (IS_GM && !char.is_eliminated) {
      marker.on('dragstart', function () {
        // Multi-Drag: alle ausgewählten Figuren mit-bewegen
        if (!selectedCharacters.has(char.id)) {
          selectedCharacters.clear();
          selectedCharacters.add(char.id);
        }
      });

      marker.on('dragend', function (e) {
        const rel = latLngToRel(e.target.getLatLng().lat, e.target.getLatLng().lng);
        const x   = Math.max(0, Math.min(1, rel.x));
        const y   = Math.max(0, Math.min(1, rel.y));

        // Gate-Nähe prüfen (< 3% Distanz)
        const nearGate = findNearestGate(x, y, 0.03);
        if (nearGate && nearGate.target_map_id) {
          sendWsMove(char.id, x, y, nearGate.id);
        } else {
          sendWsMove(char.id, x, y, null);
        }

        // Multi-Drag: alle anderen ausgewählten Figuren an gleiche Position
        selectedCharacters.forEach(function (cid) {
          if (cid !== char.id && characterMarkers[cid]) {
            characterMarkers[cid].setLatLng(e.target.getLatLng());
            sendWsMove(cid, x, y, null);
          }
        });
      });
    }

    // Linksklick: Auswahl für Multi-Drag (Spielleiter) oder Info-Popup
    marker.on('click', function () {
      if (IS_GM) {
        toggleCharacterSelection(char.id);
      }
    });

    characterMarkers[char.id] = marker;
  }

  function removeCharacterMarker(charId) {
    if (characterMarkers[charId]) {
      leafletMap.removeLayer(characterMarkers[charId]);
      delete characterMarkers[charId];
    }
    if (characterMovementLines[charId]) {
      leafletMap.removeLayer(characterMovementLines[charId]);
      delete characterMovementLines[charId];
    }
  }

  // Bestehende Figuren laden
  charactersData.forEach(addCharacterMarker);

  // ── Auswahl-Highlight ─────────────────────────────────────────────────
  function toggleCharacterSelection(charId) {
    if (selectedCharacters.has(charId)) {
      selectedCharacters.delete(charId);
    } else {
      selectedCharacters.add(charId);
    }
    updateSelectionVisuals();
  }

  function updateSelectionVisuals() {
    Object.keys(characterMarkers).forEach(function (cid) {
      const el = characterMarkers[cid].getElement();
      if (el) {
        const inner = el.querySelector('div');
        if (inner) {
          inner.style.outline = selectedCharacters.has(parseInt(cid))
            ? '3px solid #fbbf24'
            : 'none';
        }
      }
    });
    updateSidebarSelection();
  }

  // ── WebSocket ─────────────────────────────────────────────────────────
  const wsProto  = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl    = wsProto + '//' + window.location.host + '/ws/sessions/' + window.SESSION_ID + '/';
  let ws         = null;
  let wsReconnectTimer = null;

  function connectWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = function () {
      clearTimeout(wsReconnectTimer);
      setWsStatus('connected');
    };

    ws.onmessage = function (event) {
      var data;
      try { data = JSON.parse(event.data); } catch (e) { return; }
      handleWsMessage(data);
    };

    ws.onclose = function () {
      setWsStatus('disconnected');
      wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = function () {
      ws.close();
    };
  }

  function setWsStatus(status) {
    var el = document.getElementById('ws-status');
    if (!el) return;
    el.textContent = status === 'connected' ? 'Verbunden' : 'Getrennt – verbinde…';
    el.className   = status === 'connected'
      ? 'text-xs text-green-400'
      : 'text-xs text-red-400';
  }

  function sendWsMove(charId, x, y, gateId) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const msg = { type: 'move_figure', character_id: charId, x_pos: x, y_pos: y };
    if (gateId) msg.gate_id = gateId;
    ws.send(JSON.stringify(msg));
  }

  function handleWsMessage(data) {
    switch (data.type) {
      case 'figure_moved':       onFigureMoved(data);     break;
      case 'figure_eliminated':  onFigureEliminated(data); break;
      case 'figure_joined_map':  onFigureJoinedMap(data); break;
      case 'session_ended':      onSessionEnded();         break;
    }
  }

  // ── WS-Event-Handler ─────────────────────────────────────────────────

  function onFigureMoved(data) {
    const cid  = data.character_id;
    const x    = data.x_pos;
    const y    = data.y_pos;
    const latlng = relToLatLng(x, y);

    if (characterMarkers[cid]) {
      const oldPos = characterLastPos[cid];

      // Rote Bewegungslinie zeichnen
      if (oldPos && showMovementLines) {
        const oldLatLng = relToLatLng(oldPos.x, oldPos.y);
        if (characterMovementLines[cid]) {
          leafletMap.removeLayer(characterMovementLines[cid]);
        }
        characterMovementLines[cid] = L.polyline([oldLatLng, latlng], {
          color: '#ef4444', weight: 2, opacity: 0.8,
        }).addTo(leafletMap);
      }

      characterMarkers[cid].setLatLng(latlng);
      characterLastPos[cid] = { x: x, y: y };
    } else if (data.map_id === CURRENT_MAP) {
      // Figur ist neu auf dieser Karte
      const charInfo = charactersData.find(function (c) { return c.id === cid; });
      if (charInfo) {
        charInfo.on_current_map = true;
        charInfo.x_pos = x;
        charInfo.y_pos = y;
        addCharacterMarker(charInfo);
      }
    }

    updateSidebarFigurePosition(cid, x, y);
  }

  function onFigureEliminated(data) {
    const cid = data.character_id;
    const charInfo = charactersData.find(function (c) { return c.id === cid; });
    if (charInfo) {
      charInfo.is_eliminated = true;
    }
    if (characterMarkers[cid]) {
      // Marker neu bauen mit Eliminierungs-Style
      const latlng = characterMarkers[cid].getLatLng();
      leafletMap.removeLayer(characterMarkers[cid]);
      if (charInfo) {
        characterMarkers[cid] = L.marker(latlng, {
          icon: buildCharacterIcon(charInfo),
          title: charInfo.name,
          draggable: false,
        }).addTo(leafletMap);
      }
    }
  }

  function onFigureJoinedMap(data) {
    // Karte hat gewechselt → Seite neu laden
    window.location.reload();
  }

  function onSessionEnded() {
    alert('Die Session wurde beendet.');
    window.location.href = '/sessions/';
  }

  // ── Rote Linie ein/aus-schalten ──────────────────────────────────────
  var showMovementLines = true;

  var btnToggleLine = document.getElementById('btn-toggle-line');
  if (btnToggleLine) {
    btnToggleLine.addEventListener('click', function () {
      showMovementLines = !showMovementLines;
      btnToggleLine.textContent = showMovementLines ? 'Linie ausblenden' : 'Linie einblenden';
      if (!showMovementLines) {
        Object.values(characterMovementLines).forEach(function (line) {
          leafletMap.removeLayer(line);
        });
      }
    });
  }

  // ── Positionsverlauf anzeigen ─────────────────────────────────────────
  window.showCharacterPath = function (charId, color) {
    // Toggle: bereits angezeigt → ausblenden
    if (characterPaths[charId]) {
      leafletMap.removeLayer(characterPaths[charId]);
      delete characterPaths[charId];
      return;
    }
    fetch(window.CHARACTER_PATH_BASE + charId + '/path/', {
      headers: { 'X-CSRFToken': window.CSRF_TOKEN },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.positions || data.positions.length < 2) return;
        const latlngs = data.positions.map(function (p) {
          return relToLatLng(p.x_pos, p.y_pos);
        });
        characterPaths[charId] = L.polyline(latlngs, {
          color: color || '#818cf8', weight: 3, opacity: 0.7,
        }).addTo(leafletMap);
      });
  };

  // ── Zur Figur springen ─────────────────────────────────────────────────
  window.jumpToCharacter = function (charId) {
    if (characterMarkers[charId]) {
      leafletMap.setView(characterMarkers[charId].getLatLng(), leafletMap.getZoom());
    }
  };

  // ── Näheprüfung für Gates ─────────────────────────────────────────────
  function findNearestGate(x, y, threshold) {
    var nearest = null;
    var minDist = Infinity;
    gatesData.forEach(function (gate) {
      const dx = gate.x_pos - x;
      const dy = gate.y_pos - y;
      const d  = Math.sqrt(dx * dx + dy * dy);
      if (d < threshold && d < minDist) {
        minDist = d;
        nearest = gate;
      }
    });
    return nearest;
  }

  // ── Sidebar-Update ─────────────────────────────────────────────────────
  function updateSidebarFigurePosition(charId, x, y) {
    var el = document.getElementById('sidebar-char-map-' + charId);
    if (el) {
      el.textContent = mapData.title;
    }
  }

  function updateSidebarSelection() {
    charactersData.forEach(function (char) {
      var btn = document.getElementById('sidebar-char-' + char.id);
      if (btn) {
        btn.classList.toggle('ring-2', selectedCharacters.has(char.id));
        btn.classList.toggle('ring-yellow-400', selectedCharacters.has(char.id));
      }
    });
  }

  // ── Alle auswählen (Überlappungs-Popup) ──────────────────────────────
  window.selectAllAtPosition = function (charIds) {
    selectedCharacters = new Set(charIds);
    updateSelectionVisuals();
  };

  // ── Element-Popup schließen ───────────────────────────────────────────
  var btnCloseElementPopup = document.getElementById('btn-close-element-popup-modal');
  if (btnCloseElementPopup) {
    btnCloseElementPopup.addEventListener('click', function () {
      var m = document.getElementById('element-popup-modal');
      if (m) m.setAttribute('hidden', '');
    });
  }
  document.body.addEventListener('elementActionDone', function () {
    var m = document.getElementById('element-popup-modal');
    if (m) m.setAttribute('hidden', '');
  });

  // ── WebSocket starten ─────────────────────────────────────────────────
  connectWebSocket();

})();
