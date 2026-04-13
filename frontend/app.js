document.addEventListener('DOMContentLoaded', () => {
    const API = 'http://127.0.0.1:5000';

    // Initialize Map
    const map = L.map('map').setView([47.6062, -122.3321], 13);
    // Map tiles
    const lightTiles = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
    const darkTiles = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

    let currentTileLayer = L.tileLayer(lightTiles, {
        attribution: '&copy; OSM &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Dark mode toggle
    const themeBtn = document.getElementById('theme-toggle');
    let isDark = false;

    themeBtn.addEventListener('click', () => {
        isDark = !isDark;
        document.body.classList.toggle('dark', isDark);
        themeBtn.innerHTML = isDark ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
        map.removeLayer(currentTileLayer);
        currentTileLayer = L.tileLayer(isDark ? darkTiles : lightTiles, {
            attribution: '&copy; OSM &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);
    });

    let mapMarkers = [];
    let markerByIndex = {}; // itinerary index -> marker
    let mapPath = null;

    // Must-Visit state
    const MAX_MUST_VISIT = 2;
    let selectedMustVisit = new Set();
    let transportMode = 'foot';

    // Transport toggle
    document.querySelectorAll('.transport-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.transport-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            transportMode = btn.dataset.mode;
        });
    });

    // Load activities for must-visit picker
    (async function loadMustVisitOptions() {
        const mvList = document.getElementById('mv-list');
        try {
            const resp = await fetch(API + '/activities');
            const data = await resp.json();
            mvList.innerHTML = '';
            data.activities.forEach(a => {
                const item = document.createElement('div');
                item.className = 'mv-item';
                item.dataset.id = a.id;
                item.innerHTML = `
                    <div class="mv-check"></div>
                    <span class="mv-name">${a.name}</span>
                    <span class="mv-type">${a.type || ''}</span>
                `;
                item.addEventListener('click', () => toggleMustVisit(a.id, item));
                mvList.appendChild(item);
            });
        } catch (e) {
            mvList.innerHTML = '<p class="mv-loading">Could not load activities</p>';
        }
    })();

    function toggleMustVisit(id, el) {
        if (selectedMustVisit.has(id)) {
            selectedMustVisit.delete(id);
            el.classList.remove('selected');
            el.querySelector('.mv-check').textContent = '';
        } else {
            if (selectedMustVisit.size >= MAX_MUST_VISIT) return;
            selectedMustVisit.add(id);
            el.classList.add('selected');
            el.querySelector('.mv-check').textContent = '✓';
        }
        document.getElementById('mv-count').textContent = `(${selectedMustVisit.size}/${MAX_MUST_VISIT})`;
        document.querySelectorAll('.mv-item').forEach(item => {
            const iid = parseInt(item.dataset.id);
            if (!selectedMustVisit.has(iid) && selectedMustVisit.size >= MAX_MUST_VISIT) {
                item.classList.add('disabled');
            } else {
                item.classList.remove('disabled');
            }
        });
    }

    // Form handler
    const form = document.getElementById('planner-form');
    const loading = document.getElementById('loading');
    const timeline = document.getElementById('timeline');
    const submitBtn = document.getElementById('submit-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        submitBtn.disabled = true;
        loading.style.display = 'block';
        timeline.innerHTML = '';
        clearMap();

        const payload = {
            start_address: document.getElementById('start_address').value,
            end_address: document.getElementById('end_address').value,
            start_time: document.getElementById('start_time').value + ':00',
            end_time: document.getElementById('end_time').value + ':00',
            budget: Number(document.getElementById('budget').value),
            ate_breakfast: document.getElementById('ate_breakfast').checked,
            must_visit: Array.from(selectedMustVisit),
            transport_mode: transportMode
        };

        try {
            const response = await fetch(API + '/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to generate itinerary');
            }

            const data = await response.json();
            loading.style.display = 'none';
            submitBtn.disabled = false;

            renderTimeline(data.itinerary);
            plotOnMap(data.itinerary);

        } catch (error) {
            loading.style.display = 'none';
            submitBtn.disabled = false;
            timeline.innerHTML = `<div class="empty-state">
                <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i>
                <p>${error.message}</p>
            </div>`;
        }
    });

    // ── Render Timeline ──

    function renderTimeline(itinerary) {
        timeline.innerHTML = '';
        let totalCost = 0;
        let totalTravel = 0;
        let stopNum = 0;

        for (let i = 0; i < itinerary.length; i++) {
            const item = itinerary[i];
            const isHome = item.type === 'home';
            const isFirst = i === 0;
            const isLast = i === itinerary.length - 1;

            totalCost += (item.cost || 0);

            // Check if this is a same-location sub-item (e.g. café at same address as previous)
            const prevItem = i > 0 ? itinerary[i - 1] : null;
            const isSameLocation = prevItem && !isHome && !isFirst &&
                prevItem.address === item.address && prevItem.type !== 'home';

            // Travel time
            let travelMin = 0;
            if (i > 0) {
                const prevDep = new Date(itinerary[i - 1].departure);
                const thisArr = new Date(item.arrival);
                travelMin = Math.max(0, Math.round((thisArr - prevDep) / 60000));
                totalTravel += travelMin;
            }

            // Time formatting
            const fmt = iso => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const tStart = fmt(item.arrival);
            const tEnd = fmt(item.departure);
            const stayMin = Math.max(0, Math.round((new Date(item.departure) - new Date(item.arrival)) / 60000));

            // Travel indicator (skip for same-location sub-items)
            let travelHtml = '';
            if (travelMin > 0 && !isSameLocation) {
                travelHtml = `<div class="travel-time-indicator"><i class="fa-solid fa-person-walking"></i> ${travelMin} min</div>`;
            }

            // Number label
            if (!isSameLocation) stopNum++;
            const numLabel = isHome ? '🏠' : stopNum;

            // Type class
            let safeType = item.type ? item.type.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'default';
            if (item.food) safeType = 'food';

            // Badges
            let badgesHtml = '';
            if (item.type && item.type !== 'home') {
                badgesHtml += `<span class="badge badge-type">${item.type.replace('_', ' ')}</span>`;
            }
            if (item.cost > 0) badgesHtml += `<span class="badge badge-cost">$${item.cost}</span>`;
            if (item.must_visit) badgesHtml += `<span class="badge badge-must">★ Must Visit</span>`;
            if (item.rating) badgesHtml += `<span class="badge badge-rating"><i class="fa-solid fa-star"></i> ${item.rating}</span>`;

            // Meal badge (prominent)
            let mealHtml = '';
            if (item.food) {
                const mealName = item.food.charAt(0).toUpperCase() + item.food.slice(1);
                mealHtml = `<div class="meal-indicator"><i class="fa-solid fa-utensils"></i> ${mealName}</div>`;
            }

            // End location notice
            let endLocHtml = '';
            if (item.end_address && item.end_address !== item.address) {
                endLocHtml = `<p class="end-address"><i class="fa-solid fa-arrow-right"></i> Ends at: ${item.end_address}</p>`;
            }

            // Time display
            let timeHtml = '';
            if (isHome && isFirst) {
                timeHtml = `<div class="time-range">Departing ${tEnd}</div>`;
            } else if (isHome && isLast) {
                timeHtml = `<div class="time-range">Arriving ${tStart}</div>`;
            } else {
                timeHtml = `<div class="time-range">${tStart} – ${tEnd} <span class="stay-duration">(${stayMin} min)</span></div>`;
            }

            // Build element
            const el = document.createElement('div');
            el.className = `timeline-item type-${safeType}${isSameLocation ? ' sub-item' : ''}`;
            el.style.animationDelay = `${i * 0.08}s`;
            el.style.cursor = 'pointer';
            el.dataset.index = i;

            el.innerHTML = `
                ${travelHtml}
                ${!isSameLocation ? `<div class="timeline-node"><span>${numLabel}</span></div>` : '<div class="timeline-node sub-node">+</div>'}
                <div class="timeline-card">
                    ${timeHtml}
                    <h3>${item.name}</h3>
                    <p class="address"><i class="fa-solid fa-map-pin"></i> ${item.address}</p>
                    ${endLocHtml}
                    ${mealHtml}
                    ${badgesHtml ? `<div class="badges">${badgesHtml}</div>` : ''}
                </div>
            `;

            // Click to zoom
            el.addEventListener('click', () => {
                const marker = markerByIndex[i];
                if (marker) {
                    const pos = marker.getLatLng();
                    map.flyTo(pos, 16, { duration: 0.6 });
                    marker.openPopup();
                }
            });

            timeline.appendChild(el);
        }

        // Summary footer
        const summary = document.createElement('div');
        summary.className = 'trip-summary';
        summary.innerHTML = `
            <div class="summary-item"><i class="fa-solid fa-wallet"></i> Total: $${totalCost.toFixed(0)}</div>
            <div class="summary-item"><i class="fa-solid fa-person-walking"></i> Travel: ${totalTravel} min</div>
            <div class="summary-item"><i class="fa-solid fa-map-location-dot"></i> ${stopNum} stops</div>
        `;
        timeline.appendChild(summary);
    }

    // ── Map ──

    function clearMap() {
        mapMarkers.forEach(m => map.removeLayer(m));
        if (mapPath) map.removeLayer(mapPath);
        mapMarkers = [];
        markerByIndex = {};
        mapPath = null;
    }

    function plotOnMap(itinerary) {
        const waypoints = [];
        let stopNum = 0;
        let lastMarkerIndex = null;

        for (let i = 0; i < itinerary.length; i++) {
            const item = itinerary[i];
            if (item.lat == null || item.lng == null) continue;

            const isHome = item.type === 'home';
            const prevItem = i > 0 ? itinerary[i - 1] : null;
            const isSameLocation = prevItem && !isHome && i > 0 &&
                prevItem.address === item.address && prevItem.type !== 'home';

            if (!isSameLocation) stopNum++;

            let safeType = item.type ? item.type.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'default';
            if (item.food) safeType = 'food';

            // Determine label
            let label = isHome ? '🏠' : String(stopNum);
            const hasEndLoc = item.end_address && item.end_address !== item.address;
            if (hasEndLoc) label = stopNum + 'a';

            // Sub-items share the parent's marker
            if (isSameLocation) {
                if (lastMarkerIndex != null) markerByIndex[i] = markerByIndex[lastMarkerIndex];
                continue;
            }

            const lat = item.lat;
            const lng = item.lng;

            const marker = addMarker(lat, lng, label, safeType, item.name, item.address);
            markerByIndex[i] = marker;
            lastMarkerIndex = i;
            waypoints.push([lat, lng]);

            // If end_location differs, add a second marker
            if (hasEndLoc && item.end_lat && item.end_lng) {
                addMarker(item.end_lat, item.end_lng, stopNum + 'b', safeType, item.name + ' (end)', item.end_address);
                waypoints.push([item.end_lat, item.end_lng]);
            }
        }

        // Draw route line
        if (waypoints.length > 1) {
            fetchRoute(waypoints);
        }
    }

    function addMarker(lat, lng, label, typeClass, name, address) {
        const icon = L.divIcon({
            className: 'custom-icon-container',
            html: `<div class="custom-map-marker type-${typeClass}">${label}</div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            popupAnchor: [0, -12]
        });

        const marker = L.marker([lat, lng], { icon })
            .addTo(map)
            .bindPopup(`<strong>${name}</strong><br>${address}`);

        mapMarkers.push(marker);
        return marker;
    }

    async function fetchRoute(waypoints) {
        // Try OSRM for actual walking route
        const coordStr = waypoints.map(w => `${w[1]},${w[0]}`).join(';');
        try {
            const osrmProfile = transportMode === 'car' ? 'car' : 'foot';
        const resp = await fetch(`https://router.project-osrm.org/route/v1/${osrmProfile}/${coordStr}?overview=full&geometries=geojson`);
            const data = await resp.json();
            if (data.code === 'Ok' && data.routes && data.routes[0]) {
                const coords = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
                mapPath = L.polyline(coords, {
                    color: '#e67e22',
                    weight: 2.5,
                    opacity: 0.7,
                    lineCap: 'round'
                }).addTo(map);
                map.fitBounds(mapPath.getBounds().pad(0.1));
                return;
            }
        } catch (e) {
            console.warn('OSRM route failed, falling back to straight lines');
        }

        // Fallback: straight lines
        mapPath = L.polyline(waypoints, {
            color: '#e67e22',
            weight: 2,
            opacity: 0.5,
            dashArray: '6, 8',
            lineCap: 'round'
        }).addTo(map);
        map.fitBounds(L.latLngBounds(waypoints).pad(0.1));
    }
});
