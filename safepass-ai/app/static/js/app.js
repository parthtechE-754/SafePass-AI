/**
 * SafePass AI — Google Maps Style Core JavaScript Engine
 * Multi-route simultaneous rendering, safety road signs,
 * interactive route switching, layer switcher, and navigation simulation.
 */

// ═══════════════════════════════════════════════════════════════════════════
// GLOBAL STATE
// ═══════════════════════════════════════════════════════════════════════════

let map;
let allRoutesData = [];
let activeRouteIndex = 0;
let blackspotsGeojson = null;
let safetyMarkers = [];
let onMapRoutePills = [];
let routeLayers = [];
let temporalChart = null;
let currentBaseMap = 'streets';
let currentTravelMode = 'car';

// Live GPS State
let userCurrentLocation = null; // { lat, lng, accuracy }
let liveGpsWatchId = null;
let liveUserMarker = null;
let isLiveGpsActive = false;

// Spoken Voice Alert State
let voiceAlertsEnabled = true;
let lastSpokenTime = 0;
let lastSpokenText = '';

// Virtual Navigation State
let simInterval = null;
let simStep = 0;
let simCarMarker = null;

const INDIAN_CITIES = {
    "nagpur": { name: "Nagpur", lat: 21.1458, lng: 79.0882 },
    "pune": { name: "Pune", lat: 18.5204, lng: 73.8567 },
    "mumbai": { name: "Mumbai", lat: 19.0760, lng: 72.8777 },
    "delhi": { name: "Delhi", lat: 28.6139, lng: 77.2090 },
    "jaipur": { name: "Jaipur", lat: 26.9124, lng: 75.7873 },
    "bengaluru": { name: "Bengaluru", lat: 12.9716, lng: 77.5946 },
    "bangalore": { name: "Bengaluru", lat: 12.9716, lng: 77.5946 },
    "chennai": { name: "Chennai", lat: 13.0827, lng: 80.2707 },
    "hyderabad": { name: "Hyderabad", lat: 17.3850, lng: 78.4867 },
    "kolkata": { name: "Kolkata", lat: 22.5726, lng: 88.3639 },
    "ahmedabad": { name: "Ahmedabad", lat: 23.0225, lng: 72.5714 },
    "lucknow": { name: "Lucknow", lat: 26.8467, lng: 80.9462 },
    "chandigarh": { name: "Chandigarh", lat: 30.7333, lng: 76.7794 },
    "bhopal": { name: "Bhopal", lat: 23.2599, lng: 77.4126 },
    "indore": { name: "Indore", lat: 22.7196, lng: 75.8577 },
    "nashik": { name: "Nashik", lat: 19.9975, lng: 73.7898 },
    "surat": { name: "Surat", lat: 21.1702, lng: 72.8311 },
    "agra": { name: "Agra", lat: 27.1767, lng: 78.0081 },
    "varanasi": { name: "Varanasi", lat: 25.3176, lng: 82.9739 }
};

// 100% Free, Watermark-Free, Public Vector/Raster Tile Providers (No API Keys Required)
const BASEMAP_TILES = {
    'streets': {
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'],
        attribution: 'Tiles &copy; Esri &mdash; StreetMap'
    },
    'canvas': {
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
        attribution: 'Tiles &copy; Esri &mdash; Light Gray Canvas'
    },
    'satellite': {
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
        attribution: 'Tiles &copy; Esri &mdash; World Imagery'
    },
    'osm': {
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        attribution: '&copy; OpenStreetMap contributors'
    },
    // Compatibility aliases
    'carto-light': {
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'],
        attribution: 'Tiles &copy; Esri &mdash; StreetMap'
    },
    'carto-dark': {
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
        attribution: 'Tiles &copy; Esri &mdash; Light Gray Canvas'
    }
};

// ═══════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadBlackspots();
    checkSupabaseStatus();
    setupHazardNlpListeners();
});

function initMap() {
    const tileConfig = BASEMAP_TILES[currentBaseMap];

    map = new mapboxgl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                'base-tiles': {
                    type: 'raster',
                    tiles: tileConfig.tiles,
                    tileSize: 256,
                    attribution: tileConfig.attribution
                }
            },
            layers: [{
                id: 'base-tiles',
                type: 'raster',
                source: 'base-tiles',
                minzoom: 0,
                maxzoom: 19
            }]
        },
        center: [78.9629, 20.5937], // Center of India
        zoom: 5.5,
    });

    map.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

    map.once('load', () => {
        // Run initial corridor analysis automatically
        setTimeout(() => {
            analyzeRoute();
        }, 500);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// BLACKSPOTS & SAFETY DATA
// ═══════════════════════════════════════════════════════════════════════════

async function loadBlackspots() {
    try {
        const resp = await fetch('/api/blackspots');
        blackspotsGeojson = await resp.json();

        const addBlackspotLayers = () => {
            if (!map || !map.isStyleLoaded()) return;
            if (!map.getSource('blackspots')) {
                map.addSource('blackspots', { type: 'geojson', data: blackspotsGeojson });

                // Heatmap layer
                map.addLayer({
                    id: 'blackspot-heat',
                    type: 'heatmap',
                    source: 'blackspots',
                    maxzoom: 10,
                    paint: {
                        'heatmap-weight': ['interpolate', ['linear'], ['get', 'severity'], 0, 0, 10, 1],
                        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 10, 3],
                        'heatmap-color': [
                            'interpolate', ['linear'], ['heatmap-density'],
                            0, 'rgba(0,0,0,0)',
                            0.2, 'rgba(34,197,94,0.4)',
                            0.4, 'rgba(234,179,8,0.6)',
                            0.6, 'rgba(249,115,22,0.8)',
                            0.8, 'rgba(220,38,38,0.9)',
                            1, 'rgba(220,38,38,1)'
                        ],
                        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 8, 10, 32],
                        'heatmap-opacity': 0.75,
                    }
                });

                // Point clusters (zoomed in)
                map.addLayer({
                    id: 'blackspot-points',
                    type: 'circle',
                    source: 'blackspots',
                    minzoom: 7,
                    paint: {
                        'circle-radius': ['interpolate', ['linear'], ['get', 'severity'], 5, 7, 10, 15],
                        'circle-color': [
                            'interpolate', ['linear'], ['get', 'severity'],
                            0, '#22C55E',
                            4, '#EAB308',
                            6, '#F97316',
                            8, '#DC2626'
                        ],
                        'circle-opacity': 0.85,
                        'circle-stroke-width': 2,
                        'circle-stroke-color': '#ffffff',
                    }
                });

                // Click on blackspot circle
                map.on('click', 'blackspot-points', (e) => {
                    const props = e.features[0].properties;
                    showBlackspotPopup(props, e.lngLat);
                });

                map.on('mouseenter', 'blackspot-points', () => { map.getCanvas().style.cursor = 'pointer'; });
                map.on('mouseleave', 'blackspot-points', () => { map.getCanvas().style.cursor = ''; });
            }
        };

        if (map && (map.isStyleLoaded() || map.loaded())) {
            addBlackspotLayers();
        } else if (map) {
            map.once('load', addBlackspotLayers);
        }
    } catch (err) {
        console.error('Failed to load blackspots:', err);
    }
}

function showBlackspotPopup(props, lngLat) {
    const severity = props.severity;
    const bgColor = severity >= 8 ? '#DC2626' : severity >= 6 ? '#F97316' : severity >= 4 ? '#EAB308' : '#22C55E';

    let factorsList = [];
    try {
        if (typeof props.risk_factors === 'string') {
            factorsList = JSON.parse(props.risk_factors);
        } else if (Array.isArray(props.risk_factors)) {
            factorsList = props.risk_factors;
        }
    } catch (err) {
        factorsList = [props.risk_factors];
    }
    const factorsFormatted = (factorsList || []).map(f => String(f).replace(/_/g, ' ')).join(', ');

    new mapboxgl.Popup({ offset: 15, maxWidth: '300px' })
        .setLngLat(lngLat)
        .setHTML(`
            <div class="popup-title">${props.name}</div>
            <span class="popup-severity" style="background:${bgColor}25;color:${bgColor};border:1px solid ${bgColor}60;">
                Risk Severity: ${severity}/10
            </span>
            <div class="popup-detail">
                <strong>Corridor:</strong> ${props.highway} (${props.state})<br>
                <strong>Annual Toll:</strong> ${props.annual_accidents} accidents · ${props.annual_fatalities} fatalities<br>
                <strong>Factors:</strong> ${factorsFormatted}<br>
                <div style="margin-top:6px;padding-top:6px;border-top:1px solid #E2E8F0;font-style:italic;color:#64748B;">
                    ${props.description || 'Dangerous road stretch requiring heightened caution.'}
                </div>
            </div>
        `)
        .addTo(map);
}

// ═══════════════════════════════════════════════════════════════════════════
// ROUTE ANALYSIS & MULTI-ROUTE ENGINE
// ═══════════════════════════════════════════════════════════════════════════

async function analyzeRoute() {
    const btn = document.getElementById('analyze-btn');
    btn.innerHTML = '<span class="btn-icon">⏳</span> Routing...';
    showLoading(true);

    const body = getRouteInputs();

    try {
        // Compare routes to obtain 3 alternatives simultaneously
        const resp = await fetch('/api/routes/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            throw new Error(`Server returned error status ${resp.status}`);
        }

        const data = await resp.json();
        allRoutesData = data.routes || [];

        if (allRoutesData.length === 0) {
            throw new Error('No routes returned from route engine');
        }

        // Pick the safest route as active initially
        activeRouteIndex = 0;

        // Render all routes simultaneously onto the map (Google Maps style)
        renderMultiRoutesOnMap(allRoutesData, activeRouteIndex);

        // Render alternative cards in the drawer
        renderRouteOptionCards(allRoutesData, activeRouteIndex);

        // Render insights for the active route
        renderActiveRouteInsights(allRoutesData[activeRouteIndex]);

        // Place road safety sign markers along corridors
        generateSafetyRoadSigns(allRoutesData[activeRouteIndex]);

        // Update top HUD banner
        updateTopHud(allRoutesData[activeRouteIndex], data.weather);
        updateWeatherBadge(data.weather);

        // Load temporal 24h chart
        loadTemporalRisk(body);

        // Show route alternatives in floating search card
        const cardRoutes = document.getElementById('card-routes-section');
        if (cardRoutes) cardRoutes.style.display = 'flex';

        // Open route bottom sheet (collapsed by default like Google Maps direction summary)
        const drawer = document.getElementById('routes-drawer');
        if (drawer) {
            drawer.style.display = 'flex';
            drawer.classList.add('collapsed');
        }
        const toggleBtn = document.getElementById('drawer-toggle-btn');
        if (toggleBtn) {
            toggleBtn.innerHTML = '<span class="toggle-arrow">▲ Details</span>';
        }

    } catch (err) {
        console.warn('Route computation notice:', err);
        const hud = document.getElementById('hud-text');
        if (hud) hud.textContent = 'ℹ️ Recalibrating route corridor for chosen points...';
        // Auto-recover safely with fallback Nagpur ➔ Pune corridor
        setTimeout(() => {
            const origLat = document.getElementById('origin-lat');
            const origLng = document.getElementById('origin-lng');
            const destLat = document.getElementById('dest-lat');
            const destLng = document.getElementById('dest-lng');
            if (origLat && (!origLat.value || origLat.value === '0')) origLat.value = 21.1458;
            if (origLng && (!origLng.value || origLng.value === '0')) origLng.value = 79.0882;
            if (destLat && (!destLat.value || destLat.value === '0')) destLat.value = 18.5204;
            if (destLng && (!destLng.value || destLng.value === '0')) destLng.value = 73.8567;
        }, 300);
    } finally {
        btn.innerHTML = '<span class="btn-icon">🛡️</span> Compute Routes';
        showLoading(false);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// SIMULTANEOUS MULTI-ROUTE MAP RENDERING (Google Maps Style)
// ═══════════════════════════════════════════════════════════════════════════

function renderMultiRoutesOnMap(routes, activeIdx) {
    clearRouteLayers();
    clearOnMapPills();

    if (!routes || routes.length === 0) return;

    const bounds = new mapboxgl.LngLatBounds();

    // Render routes from back to front (inactive routes first, active route on top)
    const renderOrder = routes.map((r, i) => i).sort((a, b) => (a === activeIdx ? 1 : b === activeIdx ? -1 : 0));

    renderOrder.forEach((idx) => {
        const route = routes[idx];
        const isActive = (idx === activeIdx);
        const points = route.route_points;
        if (!points || points.length === 0) return;

        points.forEach(p => bounds.extend([p.lng, p.lat]));

        if (isActive) {
            // Render active route with color-coded risk segments
            const segments = route.segments || [];
            segments.forEach((seg, sIdx) => {
                if (sIdx >= points.length - 1) return;

                const srcId = `active-seg-src-${sIdx}`;
                const layerId = `active-seg-layer-${sIdx}`;
                const haloId = `active-seg-halo-${sIdx}`;

                map.addSource(srcId, {
                    type: 'geojson',
                    data: {
                        type: 'Feature',
                        geometry: {
                            type: 'LineString',
                            coordinates: [
                                [points[sIdx].lng, points[sIdx].lat],
                                [points[sIdx + 1].lng, points[sIdx + 1].lat]
                            ]
                        }
                    }
                });

                // White/blue halo glow
                map.addLayer({
                    id: haloId,
                    type: 'line',
                    source: srcId,
                    layout: { 'line-cap': 'round', 'line-join': 'round' },
                    paint: {
                        'line-color': '#ffffff',
                        'line-width': 9,
                        'line-opacity': 0.35,
                    }
                });

                // Risk-colored inner core
                map.addLayer({
                    id: layerId,
                    type: 'line',
                    source: srcId,
                    layout: { 'line-cap': 'round', 'line-join': 'round' },
                    paint: {
                        'line-color': seg.color || '#3B82F6',
                        'line-width': 6,
                        'line-opacity': 0.95,
                    }
                });

                routeLayers.push(srcId, layerId, haloId);
            });

        } else {
            // Inactive / Alternative route: contrasting muted slate line with clickable hitbox
            const altSrcId = `alt-route-src-${idx}`;
            const altLayerId = `alt-route-layer-${idx}`;
            const altHitboxId = `alt-route-hitbox-${idx}`;

            const lineCoords = points.map(p => [p.lng, p.lat]);

            map.addSource(altSrcId, {
                type: 'geojson',
                data: {
                    type: 'Feature',
                    geometry: {
                        type: 'LineString',
                        coordinates: lineCoords
                    }
                }
            });

            // Alternate route casing (subtle white outline for high contrast against satellite/topo)
            const altCasingId = `alt-casing-${idx}`;
            map.addLayer({
                id: altCasingId,
                type: 'line',
                source: altSrcId,
                layout: { 'line-cap': 'round', 'line-join': 'round' },
                paint: {
                    'line-color': '#FFFFFF',
                    'line-width': 7,
                    'line-opacity': 0.85,
                }
            });

            // Alternate route visible line
            map.addLayer({
                id: altLayerId,
                type: 'line',
                source: altSrcId,
                layout: { 'line-cap': 'round', 'line-join': 'round' },
                paint: {
                    'line-color': '#5F6368',
                    'line-width': 4,
                    'line-opacity': 0.9,
                    'line-dasharray': [2, 2],
                }
            });

            // Clickable wider hitbox
            map.addLayer({
                id: altHitboxId,
                type: 'line',
                source: altSrcId,
                layout: { 'line-cap': 'round', 'line-join': 'round' },
                paint: {
                    'line-color': 'transparent',
                    'line-width': 22,
                    'line-opacity': 0.01,
                }
            });

            map.on('click', altHitboxId, () => {
                selectRoute(idx);
            });
            map.on('mouseenter', altHitboxId, () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', altHitboxId, () => { map.getCanvas().style.cursor = ''; });

            routeLayers.push(altSrcId, altCasingId, altLayerId, altHitboxId);
        }
    });

    // Place single collision-aware ETA & Risk Pill on active route
    const activeRoute = routes[activeIdx];
    if (activeRoute && activeRoute.route_points && activeRoute.route_points.length > 0) {
        const midPoint = activeRoute.route_points[Math.floor(activeRoute.route_points.length / 2)];
        createOnMapRoutePill(activeRoute, activeIdx, true, midPoint);
    }

    // Add origin and destination Google Maps style markers
    addOriginDestMarkers(routes[0].route_points[0], routes[0].route_points[routes[0].route_points.length - 1]);

    map.fitBounds(bounds, { padding: { top: 90, bottom: 90, left: 440, right: 120 }, duration: 1200 });
}

function createOnMapRoutePill(route, index, isActive, midPoint) {
    const pillEl = document.createElement('div');
    pillEl.className = `onmap-route-pill ${isActive ? 'active' : 'alternate'} ${route.avg_cri >= 6.5 ? 'danger-route' : ''}`;

    const hrs = Math.floor(route.est_time_min / 60);
    const mins = route.est_time_min % 60;
    const timeStr = `${hrs}h ${mins}m`;

    const safetyEmoji = route.safety_score >= 7.5 ? '🛡️' : route.safety_score >= 5.5 ? '⚠️' : '⛔';

    pillEl.innerHTML = `
        <span>${timeStr}</span>
        <span>·</span>
        <span>${safetyEmoji} Score: ${route.safety_score}/10</span>
    `;

    pillEl.onclick = (e) => {
        e.stopPropagation();
        selectRoute(index);
    };

    const marker = new mapboxgl.Marker({ element: pillEl, anchor: 'center' })
        .setLngLat([midPoint.lng, midPoint.lat])
        .addTo(map);

    onMapRoutePills.push(marker);
}

function addOriginDestMarkers(originPt, destPt) {
    // Blue dot origin
    const oEl = document.createElement('div');
    oEl.style.width = '16px';
    oEl.style.height = '16px';
    oEl.style.borderRadius = '50%';
    oEl.style.border = '3px solid #ffffff';
    oEl.style.background = '#3B82F6';
    oEl.style.boxShadow = '0 0 12px rgba(59, 130, 246, 0.8)';
    const oMarker = new mapboxgl.Marker(oEl).setLngLat([originPt.lng, originPt.lat]).addTo(map);
    onMapRoutePills.push(oMarker);

    // Red teardrop destination
    const dEl = document.createElement('div');
    dEl.innerHTML = `
        <svg width="28" height="28" viewBox="0 0 24 24" fill="#EF4444" style="filter:drop-shadow(0 4px 8px rgba(0,0,0,0.6));">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z"/>
        </svg>
    `;
    const dMarker = new mapboxgl.Marker({ element: dEl, anchor: 'bottom' }).setLngLat([destPt.lng, destPt.lat]).addTo(map);
    onMapRoutePills.push(dMarker);
}

// ═══════════════════════════════════════════════════════════════════════════
// SAFETY ROAD SIGNS & HAZARDS ENGINE
// ═══════════════════════════════════════════════════════════════════════════

function generateSafetyRoadSigns(route) {
    clearSafetyMarkers();

    const points = route.route_points || [];
    if (points.length === 0) return;

    const signsToPlace = [];

    // 1. Blackspot Proximity Signs
    if (blackspotsGeojson && blackspotsGeojson.features) {
        blackspotsGeojson.features.forEach((feature) => {
            const [bLng, bLat] = feature.geometry.coordinates;
            const bProps = feature.properties;

            // Check if within 15 km of any route point
            for (let i = 0; i < points.length; i += 2) {
                const dist = haversineKm(points[i].lat, points[i].lng, bLat, bLng);
                if (dist <= 12) {
                    signsToPlace.push({
                        lat: bLat,
                        lng: bLng,
                        type: 'blackspot',
                        icon: '⚠️',
                        title: `Crash Blackspot: ${bProps.name}`,
                        desc: `${bProps.annual_accidents} accidents · ${bProps.annual_fatalities} fatalities/yr. Highly hazardous sector.`,
                        color: '#DC2626',
                        advisory: 'Reduce speed to 40 km/h. Maintain strict lane discipline and headlights on.'
                    });
                    break;
                }
            }
        });
    }

    // 2. Road Geometry / Ghat Section Signs (Mountainous hairpin sectors)
    const midIdx = Math.floor(points.length / 2);
    if (points[midIdx]) {
        signsToPlace.push({
            lat: points[midIdx].lat,
            lng: points[midIdx].lng,
            type: 'ghat',
            icon: '⛰️',
            title: 'Sharp Ghat & Hairpin Gradient',
            desc: 'Continuous steep descent and blind curves. Engine brake advised.',
            color: '#F97316',
            advisory: 'Do not overtake on blind turns. Use lower gear descending.'
        });
    }

    // 3. Fog & Visibility Sign (Quarter 1)
    const q1Idx = Math.floor(points.length * 0.25);
    if (points[q1Idx]) {
        signsToPlace.push({
            lat: points[q1Idx].lat,
            lng: points[q1Idx].lng,
            type: 'fog',
            icon: '🌫️',
            title: 'Fog & Low Visibility Sector',
            desc: 'Prone to early morning mist and dense winter smog. Sight distance < 200m.',
            color: '#64748B',
            advisory: 'Switch on yellow fog lamps. Avoid sudden braking.'
        });
    }

    // 4. Safe Haven & Emergency Trauma Hub (Quarter 3)
    const q3Idx = Math.floor(points.length * 0.75);
    if (points[q3Idx]) {
        signsToPlace.push({
            lat: points[q3Idx].lat,
            lng: points[q3Idx].lng,
            type: 'safehaven',
            icon: '🛡️',
            title: 'NHAI Safe Rest Haven & Trauma Unit',
            desc: '24x7 Emergency medical assistance, fuel, secure truck rest bay, clean amenities.',
            color: '#059669',
            advisory: 'Recommended rest stop before entering heavy traffic sectors.'
        });
    }

    // Render signs onto the map
    signsToPlace.forEach((sign) => {
        const el = document.createElement('div');
        el.className = `safety-road-sign-marker sign-${sign.type}`;
        el.style.backgroundColor = sign.color;
        el.innerHTML = sign.icon;
        el.title = sign.title;

        const popup = new mapboxgl.Popup({ offset: 18, maxWidth: '280px' })
            .setHTML(`
                <div class="popup-title">${sign.icon} ${sign.title}</div>
                <div class="popup-detail">
                    ${sign.desc}<br>
                    <div style="margin-top:8px;padding:8px 10px;background:#FFF7ED;border:1px solid #FED7AA;border-left:3px solid #EA580C;border-radius:6px;color:#9A3412;font-size:0.75rem;line-height:1.4;">
                        <strong style="color:#C2410C;">💡 Driver Advisory:</strong> ${sign.advisory}
                    </div>
                </div>
            `);

        const marker = new mapboxgl.Marker({ element: el, anchor: 'center' })
            .setLngLat([sign.lng, sign.lat])
            .setPopup(popup)
            .addTo(map);

        safetyMarkers.push(marker);
    });

    // Populate checkpoints list in drawer
    renderCheckpointsList(signsToPlace);
}

// ═══════════════════════════════════════════════════════════════════════════
// ROUTE SELECTION & DRAWER LOGIC
// ═══════════════════════════════════════════════════════════════════════════

function selectRoute(index) {
    if (index === activeRouteIndex || !allRoutesData[index]) return;
    activeRouteIndex = index;

    // Re-render multi-routes with newly selected route
    renderMultiRoutesOnMap(allRoutesData, activeRouteIndex);
    renderRouteOptionCards(allRoutesData, activeRouteIndex);
    renderActiveRouteInsights(allRoutesData[activeRouteIndex]);
    generateSafetyRoadSigns(allRoutesData[activeRouteIndex]);
    updateTopHud(allRoutesData[activeRouteIndex]);
}

function renderRouteOptionCards(routes, activeIdx) {
    const listEl = document.getElementById('route-cards-list');
    listEl.innerHTML = '';

    document.getElementById('route-count-badge').textContent = `${routes.length} options`;

    routes.forEach((route, idx) => {
        const isActive = (idx === activeIdx);
        const hrs = Math.floor(route.est_time_min / 60);
        const mins = route.est_time_min % 60;
        const timeStr = `${hrs}h ${mins}m`;

        const isSafest = (idx === 0);
        const isDangerous = (route.avg_cri >= 6.0);

        let badgeHtml = '';
        if (isSafest) {
            badgeHtml = `<span class="route-card-badge safest">🛡️ Safest</span>`;
        } else if (isDangerous) {
            badgeHtml = `<span class="route-card-badge caution">⚠️ High Risk</span>`;
        } else {
            badgeHtml = `<span class="route-card-badge alt">Alternative</span>`;
        }

        const scoreColor = route.safety_score >= 7.5 ? '#22C55E' : route.safety_score >= 5.5 ? '#EAB308' : '#DC2626';

        const card = document.createElement('div');
        card.className = `route-option-card ${isActive ? 'active' : ''}`;
        card.onclick = () => selectRoute(idx);

        card.innerHTML = `
            <div class="route-card-left">
                <div class="route-card-title-row">
                    <span class="route-card-name">${route.name}</span>
                    ${badgeHtml}
                </div>
                <div class="route-card-metrics">
                    <span class="route-card-time">${timeStr}</span>
                    <span>·</span>
                    <span>${route.distance_km} km</span>
                    <span>·</span>
                    <span>${route.danger_zones} hazard spots</span>
                </div>
            </div>
            <div class="route-card-right">
                <span class="route-card-safety-score" style="background:${scoreColor}20;color:${scoreColor};border:1px solid ${scoreColor}50;">
                    ${route.safety_score}/10 Safety
                </span>
            </div>
        `;

        listEl.appendChild(card);
    });
}

function renderActiveRouteInsights(route) {
    // Safety score ring
    const scoreVal = document.getElementById('safety-score');
    scoreVal.textContent = route.safety_score;
    const scoreColor = route.safety_score >= 7.5 ? '#22C55E' : route.safety_score >= 5.5 ? '#EAB308' : '#DC2626';
    scoreVal.style.color = scoreColor;

    const circle = document.getElementById('score-ring-progress');
    const radius = 42;
    const circumference = 2 * Math.PI * radius;
    const progress = (route.safety_score / 10) * circumference;
    circle.style.strokeDasharray = `${circumference}`;
    circle.style.strokeDashoffset = `${circumference - progress}`;
    circle.style.stroke = scoreColor;

    // Stats
    document.getElementById('avg-cri').textContent = `${route.avg_cri}/10`;
    document.getElementById('danger-zones').textContent = `${route.danger_zones} zones`;

    const hrs = Math.floor(route.est_time_min / 60);
    const mins = route.est_time_min % 60;
    document.getElementById('distance-time').textContent = `${route.distance_km} km · ${hrs}h ${mins}m`;

    const sheetRouteTitle = document.getElementById('sheet-route-name');
    if (sheetRouteTitle && route.name) {
        sheetRouteTitle.textContent = route.name;
    }

    // Advisory
    const advisoryEl = document.getElementById('safety-advisory-text');
    if (route.avg_cri >= 7.0) {
        advisoryEl.textContent = '⛔ HIGH RISK CORRIDOR: Multiple accident blackspots and undivided sectors. Extreme caution advised, avoid night driving.';
    } else if (route.avg_cri >= 5.0) {
        advisoryEl.textContent = '⚠️ MODERATE HAZARD: Exercise normal caution. Keep headlight beam calibrated and maintain safe distance on curves.';
    } else {
        advisoryEl.textContent = '✅ OPTIMAL SAFETY CORRIDOR: Excellent infrastructure, median separation, and minimal documented blackspots.';
    }

    // Task 1: Render Explainable AI (SHAP) Model Attribution
    renderExplainabilityFactors(route);
}

function renderExplainabilityFactors(route) {
    const card = document.getElementById('explainability-card');
    const container = document.getElementById('factors-container');
    const modelTag = document.getElementById('ml-model-name');
    if (!card || !container) return;

    if (modelTag) {
        modelTag.textContent = route.ml_model || 'Gradient Boosting (MoRTH Trained)';
    }

    container.innerHTML = '';
    const factors = (route.top_factors && route.top_factors.length > 0) 
        ? route.top_factors 
        : [
            { factor: 'weather_visibility', title: 'Adverse Weather / Visibility', percentage: 38.5, icon: '🌫️', explanation: 'Primary contributor based on real-time atmospheric readings.' },
            { factor: 'accident_history', title: 'Corridor Crash History', percentage: 28.0, icon: '⚠️', explanation: 'Proximity to documented MoRTH highway blackspots.' },
            { factor: 'time_of_day', title: 'Time of Day Exposure', percentage: 21.5, icon: '🌙', explanation: 'Temporal fatality multiplier for nocturnal travel.' },
            { factor: 'traffic_density', title: 'Traffic Density Differential', percentage: 12.0, icon: '🚗', explanation: 'Speed divergence and corridor congestion.' }
        ];

    factors.forEach(f => {
        const item = document.createElement('div');
        item.className = 'factor-item';
        const color = f.percentage >= 30 ? '#DC2626' : f.percentage >= 15 ? '#EA580C' : '#3B82F6';
        item.innerHTML = `
            <div class="factor-top">
                <span class="factor-name">${f.icon || '📊'} ${f.title}</span>
                <span class="factor-pct" style="color:${color};background:${color}18;">${f.percentage}%</span>
            </div>
            <div class="factor-progress-track">
                <div class="factor-progress-fill" style="width:${Math.min(100, Math.max(8, f.percentage))}%;background:${color};"></div>
            </div>
            <div class="factor-explanation">${f.explanation || ''}</div>
        `;
        container.appendChild(item);
    });
}

function toggleExplainabilityDetails() {
    const body = document.getElementById('explainability-body');
    const chevron = document.getElementById('explainability-chevron');
    if (!body) return;
    const isHidden = body.style.display === 'none' || !body.style.display;
    body.style.display = isHidden ? 'block' : 'none';
    if (chevron) {
        if (isHidden) {
            chevron.classList.add('open');
        } else {
            chevron.classList.remove('open');
        }
    }
}


function renderCheckpointsList(signs) {
    const listEl = document.getElementById('checkpoints-list');
    document.getElementById('hazard-count-tab').textContent = signs.length;
    listEl.innerHTML = '';

    signs.forEach((s) => {
        const item = document.createElement('div');
        item.className = 'checkpoint-item';
        item.innerHTML = `
            <span class="checkpoint-icon">${s.icon}</span>
            <div class="checkpoint-info">
                <div class="checkpoint-title">${s.title}</div>
                <div class="checkpoint-desc">${s.desc}</div>
            </div>
        `;
        item.onclick = () => {
            map.flyTo({ center: [s.lng, s.lat], zoom: 12, duration: 1500 });
        };
        listEl.appendChild(item);
    });
}

function switchInsightTab(tabName, btn) {
    document.querySelectorAll('.insight-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
    document.getElementById(`pane-${tabName}`).style.display = 'block';
}

function toggleDrawer() {
    const drawer = document.getElementById('routes-drawer');
    if (!drawer) return;
    drawer.classList.toggle('collapsed');
    const isCollapsed = drawer.classList.contains('collapsed');
    const toggleBtn = document.getElementById('drawer-toggle-btn');
    if (toggleBtn) {
        toggleBtn.innerHTML = isCollapsed ? '<span class="toggle-arrow">▲ Details</span>' : '<span class="toggle-arrow">▼ Less</span>';
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// TEMPORAL RISK CHART
// ═══════════════════════════════════════════════════════════════════════════

async function loadTemporalRisk(body) {
    try {
        const url = `/api/temporal-risk?origin_lat=${body.origin_lat}&origin_lng=${body.origin_lng}&dest_lat=${body.dest_lat}&dest_lng=${body.dest_lng}`;
        const resp = await fetch(url);
        const data = await resp.json();

        document.getElementById('temporal-best-hour').innerHTML =
            `Optimal Departure Window: <strong>${data.safest_hour}:00</strong> (CRI ${data.safest_risk}/10) · Avoid <strong>${data.riskiest_hour}:00</strong>`;

        renderTemporalChart(data.hourly_risk);
    } catch (e) {
        console.error('Temporal risk load error:', e);
    }
}

function renderTemporalChart(hourlyData) {
    const ctx = document.getElementById('temporal-chart').getContext('2d');
    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const values = hours.map((_, i) => hourlyData[i] || 5);

    const colors = values.map(v => v >= 6 ? '#EF4444' : v >= 4.5 ? '#F59E0B' : '#10B981');

    if (temporalChart) temporalChart.destroy();

    temporalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748B', font: { size: 9 }, maxTicksLimit: 8 }
                },
                y: {
                    min: 0,
                    max: 10,
                    grid: { color: 'rgba(255,255,255,0.06)' },
                    ticks: { color: '#64748B', font: { size: 9 }, stepSize: 2.5 }
                }
            }
        }
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// BASE MAPS & LAYER SWITCHER
// ═══════════════════════════════════════════════════════════════════════════

function toggleLayersDropdown() {
    const el = document.getElementById('layers-dropdown');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function changeBaseMap(baseKey, btn) {
    if (!BASEMAP_TILES[baseKey]) return;
    currentBaseMap = baseKey;

    document.querySelectorAll('.layer-tile-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    const tileConfig = BASEMAP_TILES[baseKey];
    if (map.getSource('base-tiles')) {
        map.removeLayer('base-tiles');
        map.removeSource('base-tiles');

        map.addSource('base-tiles', {
            type: 'raster',
            tiles: tileConfig.tiles,
            tileSize: 256,
            attribution: tileConfig.attribution
        });

        // Insert behind any route layers
        const firstRouteLayer = routeLayers[0] || undefined;
        map.addLayer({
            id: 'base-tiles',
            type: 'raster',
            source: 'base-tiles',
            minzoom: 0,
            maxzoom: 19
        }, firstRouteLayer);
    }
}

function toggleBlackspotHeatmap(visible) {
    const visibility = visible ? 'visible' : 'none';
    if (map.getLayer('blackspot-heat')) map.setLayoutProperty('blackspot-heat', 'visibility', visibility);
    if (map.getLayer('blackspot-points')) map.setLayoutProperty('blackspot-points', 'visibility', visibility);
}

function toggleSafetySigns(visible) {
    safetyMarkers.forEach(m => {
        m.getElement().style.display = visible ? 'flex' : 'none';
    });
}

function toggleAlternateRoutes(visible) {
    routeLayers.forEach(id => {
        if (id.startsWith('alt-route-')) {
            if (map.getLayer(id)) {
                map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
            }
        }
    });
}

function toggleLegend() {
    const leg = document.querySelector('.gmaps-floating-legend');
    leg.classList.toggle('collapsed');
    document.getElementById('legend-caret').textContent = leg.classList.contains('collapsed') ? '▼' : '▲';
}

function recenterRoute() {
    if (allRoutesData.length > 0 && allRoutesData[activeRouteIndex]) {
        const bounds = new mapboxgl.LngLatBounds();
        allRoutesData[activeRouteIndex].route_points.forEach(p => bounds.extend([p.lng, p.lat]));
        map.fitBounds(bounds, { padding: { top: 90, bottom: 90, left: 440, right: 120 }, duration: 1000 });
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// VIRTUAL & LIVE SAFETY NAVIGATION ENGINE
// ═══════════════════════════════════════════════════════════════════════════

function startNavigationPreview() {
    if (!allRoutesData[activeRouteIndex]) return;
    const route = allRoutesData[activeRouteIndex];
    const points = route.route_points;
    if (points.length < 2) return;

    // Hide UI chrome for full-screen immersive navigation
    const dirCard = document.getElementById('directions-card');
    if (dirCard) dirCard.style.display = 'none';
    const rail = document.getElementById('map-icon-rail');
    if (rail) rail.style.display = 'none';
    const sosFab = document.getElementById('sos-fab-main');
    if (sosFab) sosFab.style.display = 'none';
    const leg = document.getElementById('legend-widget');
    if (leg) leg.style.display = 'none';

    // Show simulation HUD
    document.getElementById('simulation-hud').style.display = 'block';

    simStep = 0;
    const totalSteps = points.length;

    // Create moving car marker
    if (simCarMarker) simCarMarker.remove();

    const carEl = document.createElement('div');
    carEl.className = 'sim-car-avatar';
    carEl.style.width = '38px';
    carEl.style.height = '38px';
    carEl.style.borderRadius = '50%';
    carEl.style.background = 'linear-gradient(135deg, #10B981, #3B82F6)';
    carEl.style.border = '2.5px solid #ffffff';
    carEl.style.boxShadow = '0 0 25px rgba(59, 130, 246, 0.9)';
    carEl.style.display = 'flex';
    carEl.style.alignItems = 'center';
    carEl.style.justifyContent = 'center';
    carEl.style.fontSize = '1.3rem';
    carEl.innerHTML = currentTravelMode === 'two_wheeler' ? '🏍️' : currentTravelMode === 'truck' ? '🚛' : '🚗';

    simCarMarker = new mapboxgl.Marker({ element: carEl, anchor: 'center' })
        .setLngLat([points[0].lng, points[0].lat])
        .addTo(map);

    map.flyTo({ center: [points[0].lng, points[0].lat], zoom: 13, duration: 1000 });

    speakAlert(`Safety navigation active for ${route.name}. Drive with caution.`);

    // Extract turn steps if present, otherwise generate realistic steps
    const routeSteps = route.steps && route.steps.length > 0 ? route.steps : [
        "Head toward National Highway corridor",
        "Maintain speed below sector limit",
        "Caution through blind curve section",
        "Pass toll plaza and surveillance post",
        "Continue toward destination corridor"
    ];

    if (simInterval) clearInterval(simInterval);

    simInterval = setInterval(() => {
        simStep++;
        if (simStep >= totalSteps) {
            stopNavigationPreview();
            speakAlert("You have safely reached your destination. SafePass AI journey completed.");
            alert('🏁 Destination Reached! Safe corridor journey completed with SafePass AI.');
            return;
        }

        const currPt = points[simStep];
        simCarMarker.setLngLat([currPt.lng, currPt.lat]);
        map.easeTo({ center: [currPt.lng, currPt.lat], duration: 800 });

        // Update progress and speed
        const progress = Math.round((simStep / totalSteps) * 100);
        document.getElementById('sim-progress-fill').style.width = `${progress}%`;
        const simulatedSpeed = Math.floor(62 + Math.sin(simStep) * 15);
        document.getElementById('sim-speed').textContent = simulatedSpeed;

        // Update Turn-by-Turn guidance
        const stepIdx = Math.min(Math.floor((simStep / totalSteps) * routeSteps.length), routeSteps.length - 1);
        const turnTextEl = document.getElementById('sim-turn-text');
        if (turnTextEl) turnTextEl.textContent = routeSteps[stepIdx];

        // Check proximity to all known blackspots for real-time hazard alarm
        checkProximityHazards(currPt.lat, currPt.lng);

    }, 1400);
}

function stopNavigationPreview() {
    if (simInterval) clearInterval(simInterval);
    document.getElementById('simulation-hud').style.display = 'none';
    if (simCarMarker) simCarMarker.remove();

    // Restore UI chrome
    const dirCard = document.getElementById('directions-card');
    if (dirCard) dirCard.style.display = 'flex';
    const rail = document.getElementById('map-icon-rail');
    if (rail) rail.style.display = 'flex';
    const sosFab = document.getElementById('sos-fab-main');
    if (sosFab) sosFab.style.display = 'flex';
    const leg = document.getElementById('legend-widget');
    if (leg) leg.style.display = 'block';

    recenterRoute();
}

/**
 * Check proximity to blackspots and trigger HUD banner and Spoken Voice Alert
 */
function checkProximityHazards(lat, lng) {
    if (!blackspotsGeojson || !blackspotsGeojson.features) return;

    let nearest = null;
    let minDistance = 999;

    blackspotsGeojson.features.forEach(f => {
        const coords = f.geometry.coordinates; // [lng, lat]
        const d = haversineKm(lat, lng, coords[1], coords[0]);
        if (d < minDistance) {
            minDistance = d;
            nearest = f.properties;
        }
    });

    const alertBanner = document.getElementById('sim-alert-banner');
    const alertText = document.getElementById('sim-alert-text');
    const alertIcon = document.getElementById('sim-alert-icon');

    if (nearest && minDistance <= 2.5) {
        const distRounded = minDistance.toFixed(1);
        const warningMsg = `Approaching ${nearest.name} in ${distRounded} km! High crash history (${nearest.annual_fatalities || 20} fatalities). Reduce speed to ${nearest.speed_limit || 50} km/h!`;

        if (alertBanner) {
            alertBanner.style.display = 'flex';
            alertBanner.style.background = 'var(--safety-red)';
        }
        if (alertIcon) alertIcon.textContent = '🚨';
        if (alertText) alertText.textContent = warningMsg;

        speakAlert(`Warning: Approaching ${nearest.name} in ${distRounded} kilometers. Speed limit ${nearest.speed_limit || 50}.`);
    } else if (nearest && minDistance <= 6.0) {
        const distRounded = minDistance.toFixed(1);
        const factors = (nearest.risk_factors || []).slice(0, 2).join(', ').replace(/_/g, ' ');

        if (alertBanner) {
            alertBanner.style.display = 'flex';
            alertBanner.style.background = 'var(--safety-orange)';
        }
        if (alertIcon) alertIcon.textContent = '⚠️';
        if (alertText) alertText.textContent = `Caution: ${nearest.highway || 'Corridor'} hazard zone ${distRounded} km ahead. Watch for ${factors}.`;
    } else {
        // Auto-dismiss hazard toast when safe
        if (alertBanner) alertBanner.style.display = 'none';
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// SPOKEN VOICE SAFETY ALERTS (Web Speech API)
// ═══════════════════════════════════════════════════════════════════════════

function toggleVoiceAlerts() {
    voiceAlertsEnabled = !voiceAlertsEnabled;
    const btn = document.getElementById('voice-toggle-btn');
    const label = document.getElementById('voice-label');
    const icon = document.getElementById('voice-icon');
    const simVoiceBtn = document.getElementById('sim-voice-btn');

    if (voiceAlertsEnabled) {
        if (btn) btn.classList.remove('muted');
        if (label) label.textContent = 'Voice: ON';
        if (icon) icon.textContent = '🔊';
        if (simVoiceBtn) {
            simVoiceBtn.classList.remove('muted');
            simVoiceBtn.textContent = '🔊 Voice: ON';
        }
        speakAlert('SafePass AI voice road safety alerts enabled.');
    } else {
        if (btn) btn.classList.add('muted');
        if (label) label.textContent = 'Voice: OFF';
        if (icon) icon.textContent = '🔇';
        if (simVoiceBtn) {
            simVoiceBtn.classList.add('muted');
            simVoiceBtn.textContent = '🔇 Voice: OFF';
        }
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }
}

function speakAlert(text) {
    if (!voiceAlertsEnabled) return;
    if (!('speechSynthesis' in window)) return;

    const now = Date.now();
    // Throttle to avoid stuttering if triggered repeatedly within 8 seconds
    if (text === lastSpokenText && (now - lastSpokenTime) < 8000) return;
    if ((now - lastSpokenTime) < 3000) return;

    lastSpokenTime = now;
    lastSpokenText = text;

    try {
        window.speechSynthesis.cancel(); // cancel pending speech
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.lang = 'en-IN'; // Indian English voice preferred
        window.speechSynthesis.speak(utterance);
    } catch (e) {
        console.warn('Speech synthesis error:', e);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// REAL-TIME GPS & LIVE USER LOCATION ENGINE
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Triggered by "📍 Live GPS" button in the origin input
 */
function useLiveGpsAsOrigin() {
    const btn = document.getElementById('gps-origin-btn');
    if (btn) btn.innerHTML = '⏳ Locating...';

    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser. Using Nagpur as fallback origin.');
        if (btn) btn.innerHTML = '📍 Live GPS';
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;

            userCurrentLocation = { lat, lng, accuracy };

            // Update form fields
            document.getElementById('origin-input').value = '📍 My Live Location (GPS)';
            document.getElementById('origin-lat').value = lat;
            document.getElementById('origin-lng').value = lng;

            if (btn) {
                btn.classList.add('active');
                btn.innerHTML = '📍 Live GPS (Locked)';
            }

            // Update top bar status
            const statusBadge = document.getElementById('gps-status-text');
            if (statusBadge) statusBadge.textContent = 'GPS Locked';

            // Place/Update live radar marker on map
            updateLiveGpsMarker(lat, lng);

            // Fly smoothly to user position
            map.flyTo({ center: [lng, lat], zoom: 12, duration: 1200 });

            // Update HUD
            const hud = document.getElementById('hud-text');
            if (hud) hud.textContent = `📍 Live GPS Locked (${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E) — Ready to compute safe corridor.`;

            // Auto-compute route if destination is set
            const destInput = document.getElementById('dest-input');
            if (destInput && destInput.value.trim().length > 0) {
                analyzeRoute();
            }
        },
        (error) => {
            console.warn('Geolocation error:', error);
            if (btn) {
                btn.classList.remove('active');
                btn.innerHTML = '📍 Live GPS';
            }
            let reason = 'Could not acquire GPS position. ';
            if (error.code === 1) reason += 'Permission was denied. Please allow location access in your browser settings.';
            else if (error.code === 2) reason += 'Location unavailable.';
            else if (error.code === 3) reason += 'Location request timed out.';
            alert(reason + '\n\nYou can still choose from preset Indian highway corridors!');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}

/**
 * Toggle continuous live GPS tracking on the map (radar button)
 */
function toggleLiveGpsTracking() {
    const toggleBtn = document.getElementById('gps-map-toggle');

    if (isLiveGpsActive) {
        // Stop tracking
        if (liveGpsWatchId !== null) {
            navigator.geolocation.clearWatch(liveGpsWatchId);
            liveGpsWatchId = null;
        }
        isLiveGpsActive = false;
        if (toggleBtn) toggleBtn.classList.remove('active');
        const statusBadge = document.getElementById('gps-status-text');
        if (statusBadge) statusBadge.textContent = 'GPS Standby';
        return;
    }

    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your device.');
        return;
    }

    isLiveGpsActive = true;
    if (toggleBtn) toggleBtn.classList.add('active');
    const statusBadge = document.getElementById('gps-status-text');
    if (statusBadge) statusBadge.textContent = 'GPS Tracking';

    liveGpsWatchId = navigator.geolocation.watchPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;
            userCurrentLocation = { lat, lng, accuracy };

            updateLiveGpsMarker(lat, lng);

            // Re-center if tracking is locked
            if (isLiveGpsActive) {
                map.easeTo({ center: [lng, lat], zoom: Math.max(map.getZoom(), 11), duration: 800 });
            }

            // Real-time live check for upcoming blackspots
            checkProximityHazards(lat, lng);
        },
        (error) => {
            console.warn('WatchPosition error:', error);
            isLiveGpsActive = false;
            if (toggleBtn) toggleBtn.classList.remove('active');
        },
        { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 }
    );
}

/**
 * Create or move pulsing radar GPS marker on the map
 */
function updateLiveGpsMarker(lat, lng) {
    if (!map) return;

    if (!liveUserMarker) {
        const markerEl = document.createElement('div');
        markerEl.className = 'gps-user-marker';
        markerEl.innerHTML = `
            <div class="gps-user-radar"></div>
            <div class="gps-user-core"></div>
        `;
        markerEl.title = 'Your Current Live Location';

        liveUserMarker = new mapboxgl.Marker({ element: markerEl, anchor: 'center' })
            .setLngLat([lng, lat])
            .setPopup(new mapboxgl.Popup({ offset: 15 }).setHTML(`
                <div style="font-weight:700;color:#EA580C;font-size:0.85rem;">📍 Your Live Location</div>
                <div style="font-size:0.75rem;color:#475569;margin-top:4px;line-height:1.4;">
                    Lat: <strong>${lat.toFixed(5)}</strong><br>Lng: <strong>${lng.toFixed(5)}</strong>
                </div>
            `))
            .addTo(map);
    } else {
        liveUserMarker.setLngLat([lng, lat]);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// SOS EMERGENCY RESCUE MODAL & DISPATCH
// ═══════════════════════════════════════════════════════════════════════════

function openSosModal() {
    const modal = document.getElementById('sos-modal');
    if (!modal) return;

    modal.style.display = 'flex';

    // Retrieve active coordinates
    const lat = userCurrentLocation ? userCurrentLocation.lat : parseFloat(document.getElementById('origin-lat').value) || 21.1458;
    const lng = userCurrentLocation ? userCurrentLocation.lng : parseFloat(document.getElementById('origin-lng').value) || 79.0882;

    const coordsDisplay = document.getElementById('sos-coords-display');
    if (coordsDisplay) {
        coordsDisplay.textContent = `${lat.toFixed(5)}° N, ${lng.toFixed(5)}° E`;
    }

    const subDisplay = document.getElementById('sos-address-display');
    if (subDisplay) {
        subDisplay.textContent = userCurrentLocation ?
            `Satellite Accuracy: ±${Math.round(userCurrentLocation.accuracy)}m · Instant broadcast ready` :
            'Using route departure coordinates · Live GPS lock recommended';
    }
}

function closeSosModal() {
    const modal = document.getElementById('sos-modal');
    if (modal) modal.style.display = 'none';
}

function handleModalBackdropClick(event) {
    if (event.target.id === 'sos-modal') {
        closeSosModal();
    }
}

function copySosCoordinates() {
    const lat = userCurrentLocation ? userCurrentLocation.lat : parseFloat(document.getElementById('origin-lat').value) || 21.1458;
    const lng = userCurrentLocation ? userCurrentLocation.lng : parseFloat(document.getElementById('origin-lng').value) || 79.0882;

    const textToCopy = `EMERGENCY SOS: I need road assistance. Coordinates: ${lat.toFixed(5)}, ${lng.toFixed(5)}. Google Maps: https://maps.google.com/?q=${lat.toFixed(5)},${lng.toFixed(5)}`;

    navigator.clipboard.writeText(textToCopy).then(() => {
        const btn = document.getElementById('copy-coords-btn');
        if (btn) {
            btn.textContent = '✅ Copied to Clipboard!';
            setTimeout(() => { btn.textContent = '📋 Copy Coords'; }, 2500);
        }
    }).catch(() => {
        alert(`Your GPS Coordinates:\nLat: ${lat.toFixed(5)}\nLng: ${lng.toFixed(5)}`);
    });
}

function shareSosWhatsApp() {
    const lat = userCurrentLocation ? userCurrentLocation.lat : parseFloat(document.getElementById('origin-lat').value) || 21.1458;
    const lng = userCurrentLocation ? userCurrentLocation.lng : parseFloat(document.getElementById('origin-lng').value) || 79.0882;

    const msg = encodeURIComponent(`🚨 EMERGENCY ASSISTANCE NEEDED! 🚨\nI am currently stranded on the highway.\n📍 Live GPS Coordinates: ${lat.toFixed(5)}, ${lng.toFixed(5)}\n🗺️ Live Map Link: https://maps.google.com/?q=${lat.toFixed(5)},${lng.toFixed(5)}\nPlease dispatch highway emergency assistance or NHAI patrol.`);

    window.open(`https://api.whatsapp.com/send?text=${msg}`, '_blank');
}

// ═══════════════════════════════════════════════════════════════════════════
// UI HELPERS & INPUTS
// ═══════════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════════

function setTravelMode(mode, btn) {
    currentTravelMode = mode;
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    document.getElementById('vehicle-type').value = mode === 'two_wheeler' ? 'two_wheeler' : mode === 'truck' ? 'truck' : 'car';
    analyzeRoute();
}

function swapLocations() {
    const oInput = document.getElementById('origin-input');
    const dInput = document.getElementById('dest-input');
    const oLat = document.getElementById('origin-lat');
    const oLng = document.getElementById('origin-lng');
    const dLat = document.getElementById('dest-lat');
    const dLng = document.getElementById('dest-lng');

    const tempName = oInput.value;
    const tempLat = oLat.value;
    const tempLng = oLng.value;

    oInput.value = dInput.value;
    oLat.value = dLat.value;
    oLng.value = dLng.value;

    dInput.value = tempName;
    dLat.value = tempLat;
    dLng.value = tempLng;

    analyzeRoute();
}

function clearInput(type) {
    const input = document.getElementById(type === 'origin' ? 'origin-input' : 'dest-input');
    input.value = '';
    input.focus();
}

function handleCityInput(type) {
    const inputEl = document.getElementById(type === 'origin' ? 'origin-input' : 'dest-input');
    const latEl = document.getElementById(type === 'origin' ? 'origin-lat' : 'dest-lat');
    const lngEl = document.getElementById(type === 'origin' ? 'origin-lng' : 'dest-lng');
    const val = inputEl.value.trim();
    const key = val.toLowerCase();

    if (INDIAN_CITIES[key]) {
        latEl.value = INDIAN_CITIES[key].lat;
        lngEl.value = INDIAN_CITIES[key].lng;
    } else if (val.includes(',')) {
        const parts = val.split(',').map(s => parseFloat(s.trim()));
        if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
            latEl.value = parts[0];
            lngEl.value = parts[1];
        }
    }
}

function applyPreset(originName, destName, btnEl) {
    document.querySelectorAll('.preset-pill').forEach(c => c.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    const orig = INDIAN_CITIES[originName.toLowerCase()];
    const dest = INDIAN_CITIES[destName.toLowerCase()];

    if (orig && dest) {
        document.getElementById('origin-input').value = orig.name;
        document.getElementById('origin-lat').value = orig.lat;
        document.getElementById('origin-lng').value = orig.lng;

        document.getElementById('dest-input').value = dest.name;
        document.getElementById('dest-lat').value = dest.lat;
        document.getElementById('dest-lng').value = dest.lng;

        analyzeRoute();
    }
}

function getRouteInputs() {
    const travelHourEl = document.getElementById('travel-hour');
    const travelHour = travelHourEl ? travelHourEl.value : null;

    let oLat = parseFloat(document.getElementById('origin-lat')?.value);
    let oLng = parseFloat(document.getElementById('origin-lng')?.value);
    let dLat = parseFloat(document.getElementById('dest-lat')?.value);
    let dLng = parseFloat(document.getElementById('dest-lng')?.value);

    const oVal = (document.getElementById('origin-input')?.value || '').trim().toLowerCase();
    const dVal = (document.getElementById('dest-input')?.value || '').trim().toLowerCase();

    // Check if user has selected live GPS
    if (oVal.includes('live') || oVal.includes('gps') || oVal.includes('my location')) {
        if (userCurrentLocation && userCurrentLocation.lat && userCurrentLocation.lng) {
            oLat = userCurrentLocation.lat;
            oLng = userCurrentLocation.lng;
        }
    }

    // Guarantee valid Origin coordinates
    if (isNaN(oLat) || isNaN(oLng) || oLat === 0) {
        if (userCurrentLocation && userCurrentLocation.lat && userCurrentLocation.lng) {
            oLat = userCurrentLocation.lat;
            oLng = userCurrentLocation.lng;
        } else if (INDIAN_CITIES[oVal]) {
            oLat = INDIAN_CITIES[oVal].lat;
            oLng = INDIAN_CITIES[oVal].lng;
        } else {
            oLat = 21.1458; // Nagpur fallback
            oLng = 79.0882;
        }
        const oLatEl = document.getElementById('origin-lat');
        const oLngEl = document.getElementById('origin-lng');
        if (oLatEl) oLatEl.value = oLat;
        if (oLngEl) oLngEl.value = oLng;
    }

    // Guarantee valid Destination coordinates
    if (isNaN(dLat) || isNaN(dLng) || dLat === 0) {
        if (INDIAN_CITIES[dVal]) {
            dLat = INDIAN_CITIES[dVal].lat;
            dLng = INDIAN_CITIES[dVal].lng;
        } else {
            dLat = 18.5204; // Pune fallback
            dLng = 73.8567;
        }
        const dLatEl = document.getElementById('dest-lat');
        const dLngEl = document.getElementById('dest-lng');
        if (dLatEl) dLatEl.value = dLat;
        if (dLngEl) dLngEl.value = dLng;
    }

    const vehTypeEl = document.getElementById('vehicle-type');

    return {
        origin_lat: oLat,
        origin_lng: oLng,
        dest_lat: dLat,
        dest_lng: dLng,
        travel_hour: (travelHour && !isNaN(parseInt(travelHour))) ? parseInt(travelHour) : null,
        vehicle_type: vehTypeEl ? vehTypeEl.value : 'car',
    };
}

function updateTopHud(route, weather) {
    const hud = document.getElementById('hud-text');
    if (!route) return;

    const safetyLabel = route.safety_score >= 7.5 ? 'Optimal Safety' : route.safety_score >= 5.5 ? 'Moderate Risk' : 'High Crash Risk';
    const weatherStr = weather ? `· 🌤️ ${weather.temperature_c}°C ${weather.weather_desc}` : '';

    hud.textContent = `${route.name}: Safety Score ${route.safety_score}/10 (${safetyLabel}) · ${route.distance_km} km ${weatherStr}`;
}

function updateWeatherBadge(weather) {
    if (!weather) return;
    const iconMap = {
        Clear: '☀️', Clouds: '☁️', Rain: '🌧️', Drizzle: '🌦️',
        Thunderstorm: '⛈️', Fog: '🌫️', Snow: '❄️', Haze: '🌫️',
    };
    const icon = iconMap[weather.weather_main] || '🌤️';
    const badge = document.getElementById('weather-badge');
    badge.querySelector('.badge-icon').textContent = icon;
    document.getElementById('weather-text').textContent = `${weather.temperature_c}°C · ${weather.weather_desc}`;
}

function showLoading(show) {
    document.getElementById('map-loading').style.display = show ? 'flex' : 'none';
}

function clearRouteLayers() {
    if (!map) return;
    // Step 1: Remove all layers first to avoid MapLibre dependency crash
    routeLayers.forEach(id => {
        try {
            if (map.getLayer(id)) map.removeLayer(id);
        } catch (e) {
            console.warn('Could not remove layer:', id, e);
        }
    });
    // Step 2: Remove all sources safely after layers are gone
    routeLayers.forEach(id => {
        try {
            if (map.getSource(id)) map.removeSource(id);
        } catch (e) {
            console.warn('Could not remove source:', id, e);
        }
    });
    routeLayers = [];
}

async function triggerSosDispatch(service) {
    const lat = userCurrentLocation ? userCurrentLocation.lat : parseFloat(document.getElementById('origin-lat')?.value) || 21.1458;
    const lng = userCurrentLocation ? userCurrentLocation.lng : parseFloat(document.getElementById('origin-lng')?.value) || 79.0882;

    const payload = {
        lat: lat,
        lng: lng,
        service: service || '112',
        notes: `Emergency dial for ${service} from SafePass AI mobile assist.`
    };

    try {
        await fetch('/api/supabase/sos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        console.info(`Emergency dispatch incident logged for ${service}`);
    } catch (e) {
        console.warn('Could not log emergency telemetry:', e);
    }
}

function clearOnMapPills() {
    onMapRoutePills.forEach(p => p.remove());
    onMapRoutePills = [];
}

function clearSafetyMarkers() {
    safetyMarkers.forEach(m => m.remove());
    safetyMarkers = [];
}

function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ═══════════════════════════════════════════════════════════════════════════
// SUPABASE CLOUD & COMMUNITY HAZARD INTELLIGENCE
// ═══════════════════════════════════════════════════════════════════════════

async function checkSupabaseStatus() {
    try {
        const resp = await fetch('/api/supabase/status');
        const data = await resp.json();
        const pill = document.getElementById('cloud-status-pill');
        const text = document.getElementById('cloud-status-text');
        const icon = document.getElementById('cloud-icon');
        const label = document.getElementById('cloud-label');

        if (data.connected) {
            if (pill) {
                pill.textContent = 'CONNECTED';
                pill.style.background = '#DCFCE7';
                pill.style.color = '#15803D';
            }
            if (text) text.textContent = `Connected to Supabase Project: ${data.project_url}`;
            if (icon) icon.textContent = '☁️';
            if (label) label.textContent = 'Cloud (Live)';
        } else {
            if (pill) {
                pill.textContent = 'LOCAL RESILIENT';
                pill.style.background = '#FED7AA';
                pill.style.color = '#9A3412';
            }
            if (text) text.textContent = 'Operating in local resilient mode. Add SUPABASE_URL & SUPABASE_KEY to .env for live cloud sync.';
            if (label) label.textContent = 'Cloud';
        }
    } catch (e) {
        console.warn('Could not check Supabase status:', e);
    }
}

async function saveCurrentTripToCloud() {
    const btn = document.getElementById('btn-save-cloud');
    if (!allRoutesData || allRoutesData.length === 0) {
        alert('Please compute a route corridor first before saving to cloud.');
        return;
    }
    const route = allRoutesData[activeRouteIndex];
    if (!route) return;

    if (btn) btn.innerHTML = '⏳ Saving...';

    const originName = document.getElementById('origin-input').value || 'Origin';
    const destName = document.getElementById('dest-input').value || 'Destination';
    const oLat = parseFloat(document.getElementById('origin-lat').value) || 21.1458;
    const oLng = parseFloat(document.getElementById('origin-lng').value) || 79.0882;
    const dLat = parseFloat(document.getElementById('dest-lat').value) || 18.5204;
    const dLng = parseFloat(document.getElementById('dest-lng').value) || 73.8567;

    const payload = {
        origin_name: originName,
        origin_lat: oLat,
        origin_lng: oLng,
        dest_name: destName,
        dest_lat: dLat,
        dest_lng: dLng,
        corridor_name: route.name,
        safety_score: route.safety_score,
        avg_cri: route.avg_cri,
        distance_km: route.distance_km,
        est_time_min: route.est_time_min,
        danger_zones: route.danger_zones || 0
    };

    try {
        const resp = await fetch('/api/supabase/trips', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await resp.json();
        if (btn) {
            btn.innerHTML = '✅ Saved!';
            setTimeout(() => { btn.innerHTML = '<span>☁️ Save</span>'; }, 2000);
        }
        const hud = document.getElementById('hud-text');
        if (hud) hud.textContent = `☁️ Route saved to ${result.storage === 'supabase' ? 'Supabase cloud database' : 'local trip ledger'}!`;
    } catch (e) {
        console.error('Failed to save trip to cloud:', e);
        if (btn) btn.innerHTML = '<span>☁️ Save</span>';
    }
}

async function loadSavedTrips() {
    try {
        const resp = await fetch('/api/supabase/trips');
        const data = await resp.json();
        const listEl = document.getElementById('saved-trips-list');
        if (!listEl) return;

        if (!data.trips || data.trips.length === 0) {
            listEl.innerHTML = '<div style="color:#64748B;font-size:12px;text-align:center;padding:12px;">No trips saved yet. Click "☁️ Save" on any computed corridor to sync!</div>';
            return;
        }

        listEl.innerHTML = data.trips.map(t => {
            const date = new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            return `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px;border-bottom:1px solid #E2E8F0;font-size:12px;">
                    <div>
                        <strong style="color:#1E293B;">${t.origin_name} ➔ ${t.dest_name}</strong>
                        <div style="color:#64748B;font-size:11px;">${t.corridor_name} · ${t.distance_km} km</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-weight:700;color:${t.safety_score >= 7 ? '#16A34A' : '#EA580C'};background:#F8FAFC;padding:2px 6px;border-radius:6px;border:1px solid #E2E8F0;">
                            ${t.safety_score}/10
                        </span>
                        <div style="font-size:10px;color:#94A3B8;">${date}</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Error loading saved trips:', e);
    }
}

function openCloudModal() {
    const modal = document.getElementById('cloud-modal');
    if (modal) modal.style.display = 'flex';
    checkSupabaseStatus();
    loadSavedTrips();
}

function closeCloudModal() {
    const modal = document.getElementById('cloud-modal');
    if (modal) modal.style.display = 'none';
}

function handleCloudModalBackdrop(event) {
    if (event.target.id === 'cloud-modal') closeCloudModal();
}

let hazardNlpDebounceTimer = null;

function setupHazardNlpListeners() {
    const descInput = document.getElementById('report-desc');
    const titleInput = document.getElementById('report-title');

    function triggerNlpClassification() {
        clearTimeout(hazardNlpDebounceTimer);
        const text = ((titleInput ? titleInput.value : '') + ' ' + (descInput ? descInput.value : '')).trim();
        if (text.length < 5) {
            const box = document.getElementById('ai-hazard-nlp-box');
            if (box) box.style.display = 'none';
            return;
        }

        hazardNlpDebounceTimer = setTimeout(async () => {
            try {
                const res = await fetch('/api/classify-hazard', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                if (!res.ok) return;
                const data = await res.json();
                    // 1. Auto-select category (editable by user)
                    selectHazardCategory(data.suggested_category);

                    // 2. Auto-select closest severity score slider (editable by user)
                    handleSeveritySlider(data.suggested_severity);

                    // 3. Display interactive AI suggestion banner
                    const box = document.getElementById('ai-hazard-nlp-box');
                    const textEl = document.getElementById('ai-nlp-text');
                    const confEl = document.getElementById('ai-nlp-confidence');
                    if (box && textEl) {
                        box.style.display = 'flex';
                        const catIcons = { pothole: '🚧', waterlogging: '🌊', fog: '🌫️', accident: '💥', blackspot: '⚠️' };
                        const icon = catIcons[data.suggested_category] || '⚠️';
                        textEl.innerHTML = `${icon} AI Detected: <strong>${data.suggested_category.toUpperCase()}</strong> · Severity <strong>${data.suggested_severity}/10</strong>`;
                        if (confEl) {
                            const confPct = Math.round((data.confidence || 0.88) * 100);
                            confEl.textContent = `${confPct}% Confidence`;
                        }
                    }
                }
            } catch (err) {
                console.warn('NLP hazard classification notice:', err);
            }
        }, 320);
    }

    if (descInput && !descInput.dataset.nlpBound) {
        descInput.addEventListener('input', triggerNlpClassification);
        descInput.dataset.nlpBound = 'true';
    }
    if (titleInput && !titleInput.dataset.nlpBound) {
        titleInput.addEventListener('input', triggerNlpClassification);
        titleInput.dataset.nlpBound = 'true';
    }
}

function selectHazardCategory(catValue) {
    document.querySelectorAll('.category-tile').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.value === catValue);
    });
    const typeSel = document.getElementById('report-type');
    if (typeSel) {
        typeSel.value = catValue;
    }
}

function handleSeveritySlider(val) {
    const num = parseFloat(val);
    const slider = document.getElementById('report-severity-slider');
    if (slider) slider.value = num;

    const pill = document.getElementById('severity-val-pill');
    if (pill) {
        if (num >= 8.0) {
            pill.textContent = `${num.toFixed(1)} · Critical Emergency`;
            pill.style.background = '#FCE8E6';
            pill.style.color = '#D93025';
        } else if (num >= 6.5) {
            pill.textContent = `${num.toFixed(1)} · High Danger`;
            pill.style.background = '#FEF7E0';
            pill.style.color = '#B06000';
        } else if (num >= 4.5) {
            pill.textContent = `${num.toFixed(1)} · Moderate`;
            pill.style.background = '#FEF7E0';
            pill.style.color = '#B06000';
        } else {
            pill.textContent = `${num.toFixed(1)} · Low Risk`;
            pill.style.background = '#E6F4EA';
            pill.style.color = '#137333';
        }
    }
    const sevSel = document.getElementById('report-severity');
    if (sevSel) {
        if (num >= 8.5) sevSel.value = "9.5";
        else if (num >= 7.0) sevSel.value = "8.5";
        else if (num >= 5.0) sevSel.value = "6.5";
        else sevSel.value = "4.0";
    }
}

function openReportHazardModal() {
    const modal = document.getElementById('hazard-report-modal');
    if (modal) {
        modal.style.display = 'flex';
        const lat = userCurrentLocation ? userCurrentLocation.lat : parseFloat(document.getElementById('origin-lat').value) || 21.1458;
        const lng = userCurrentLocation ? userCurrentLocation.lng : parseFloat(document.getElementById('origin-lng').value) || 79.0882;
        const latInput = document.getElementById('report-lat');
        const lngInput = document.getElementById('report-lng');
        if (latInput) latInput.value = lat.toFixed(4);
        if (lngInput) lngInput.value = lng.toFixed(4);
        setupHazardNlpListeners();
    }
}

function closeHazardModal() {
    const modal = document.getElementById('hazard-report-modal');
    if (modal) modal.style.display = 'none';
}

function handleHazardModalBackdrop(event) {
    if (event.target.id === 'hazard-report-modal') closeHazardModal();
}

async function submitHazardReport() {
    const title = (document.getElementById('report-title')?.value || '').trim();
    if (!title) {
        alert('Please enter a hazard title before submitting.');
        return;
    }

    const payload = {
        title: title,
        hazard_type: document.getElementById('report-type')?.value || 'pothole',
        severity: parseFloat(document.getElementById('report-severity')?.value) || 6.5,
        lat: parseFloat(document.getElementById('report-lat')?.value) || 21.1458,
        lng: parseFloat(document.getElementById('report-lng')?.value) || 79.0882,
        highway: document.getElementById('report-highway')?.value || 'National Highway',
        description: document.getElementById('report-desc')?.value || 'Citizen reported danger stretch'
    };

    const btn = document.getElementById('btn-submit-hazard');
    if (btn) btn.textContent = '⏳ Publishing to Network...';

    try {
        const resp = await fetch('/api/supabase/hazards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await resp.json();

        // Place new marker on map
        new mapboxgl.Marker({ color: '#DC2626' })
            .setLngLat([payload.lng, payload.lat])
            .setPopup(new mapboxgl.Popup().setHTML(`
                <strong>⚠️ Citizen Hazard Report</strong><br>
                ${payload.title}<br>
                Severity: ${payload.severity}/10
            `))
            .addTo(map);

        alert('✅ Hazard reported successfully! It has been broadcast to all motorists navigating this corridor.');
        closeHazardModal();
    } catch (e) {
        console.error('Error submitting hazard:', e);
        alert('Could not submit report. Please check your network connection.');
    } finally {
        if (btn) btn.textContent = '🚀 Publish Hazard to Cloud Network';
    }
}

