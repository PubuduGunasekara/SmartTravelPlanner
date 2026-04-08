document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Default Times (Tomorrow 9am to 9pm)
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    // Format helper YYYY-MM-DDTHH:MM
    const formatDateTime = (date, hours) => {
        const d = new Date(date);
        d.setHours(hours, 0, 0, 0);
        const pad = n => n.toString().padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    document.getElementById('start_time').value = formatDateTime(tomorrow, 9);
    document.getElementById('end_time').value = formatDateTime(tomorrow, 21);

    // 2. Initialize Map (Centered on Seattle default)
    const map = L.map('map').setView([47.6062, -122.3321], 13);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    let mapMarkers = [];
    let mapPath = null;
    let waypoints = []; // Stores the lat/lng coordinates in order

    // 3. Form Submit Handler
    const form = document.getElementById('planner-form');
    const loading = document.getElementById('loading');
    const timeline = document.getElementById('timeline');
    const tripStats = document.getElementById('trip-stats');
    const submitBtn = document.getElementById('submit-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // UI Loading State
        submitBtn.disabled = true;
        loading.style.display = 'block';
        timeline.innerHTML = '';
        tripStats.innerHTML = '';
        
        clearMap();

        const payload = {
            start_address: document.getElementById('start_address').value,
            end_address: document.getElementById('end_address').value,
            start_time: document.getElementById('start_time').value + ":00",
            end_time: document.getElementById('end_time').value + ":00",
            budget: Number(document.getElementById('budget').value),
            ate_breakfast: document.getElementById('ate_breakfast').checked
        };

        try {
            // NOTE: assuming backend is running on localhost:5000
            const response = await fetch('http://127.0.0.1:5000/plan', {
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
                <p>Error: ${error.message}</p>
            </div>`;
        }
    });

    // 4. Render Timeline HTML
    function renderTimeline(itinerary) {
        let totalCost = 0;
        let stopsCount = 0;

        timeline.innerHTML = ''; // Clear

        itinerary.forEach((item, index) => {
            stopsCount++;
            totalCost += (item.cost || 0);

            // Determine Node content (numbers) and category classes
            let safeType = item.type ? item.type.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'default';
            if (item.food) safeType = 'food';
            if (index === 0) safeType = 'start';
            if (index === itinerary.length - 1) safeType = 'end';
            
            let itemClass = `type-${safeType}`;

            let nodeContent = `<span>${index + 1}</span>`;
            if (index === 0) nodeContent = '<i class="fa-solid fa-plane-departure"></i>';
            if (index === itinerary.length - 1) nodeContent = '<i class="fa-solid fa-flag-checkered"></i>';

            // Formatting time
            const formatTime = (isoStr) => {
                const d = new Date(isoStr);
                return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            };

            const tStart = formatTime(item.arrival);
            const tEnd = formatTime(item.departure);
            const stayMinutes = Math.round((new Date(item.departure) - new Date(item.arrival)) / 60000);

            // Creating Badges
            let badgesHtml = '';
            if (item.type && item.type !== 'start/end') {
                badgesHtml += `<span class="badge badge-type">${item.type.replace('_', ' ').toUpperCase()}</span>`;
            }
            if (item.food) badgesHtml += `<span class="badge badge-food">${item.food.toUpperCase()}</span>`;
            if (item.cost > 0) badgesHtml += `<span class="badge badge-cost">$${item.cost.toFixed(2)}</span>`;
            if (item.must_visit) badgesHtml += `<span class="badge badge-must">Must Visit</span>`;
            if (item.rating) badgesHtml += `<span class="badge badge-rating"><i class="fa-solid fa-star" style="color:#fbbf24; margin-right:4px;"></i>${item.rating}</span>`;

            // Calculate Travel Time
            let travelHtml = '';
            if (index > 0) {
                const prevDeparture = new Date(itinerary[index - 1].departure);
                const currArrival = new Date(item.arrival);
                const travelMinutes = Math.round((currArrival - prevDeparture) / 60000);
                if (travelMinutes > 0) {
                    travelHtml = `<div class="travel-time-indicator"><i class="fa-solid fa-person-walking"></i> ${travelMinutes} min travel</div>`;
                }
            }

            let timeRangeHtml = `<div class="time-range">${tStart} - ${tEnd} <span class="stay-duration">(${stayMinutes} min)</span></div>`;
            if (index === 0) {
                timeRangeHtml = `<div class="time-range">Departure: ${tEnd}</div>`;
            } else if (index === itinerary.length - 1) {
                timeRangeHtml = `<div class="time-range">Arrival: ${tStart}</div>`;
            }

            // Card HTML
            const el = document.createElement('div');
            el.className = `timeline-item ${itemClass}`;
            el.style.animationDelay = `${index * 0.1}s`;
            
            el.innerHTML = `
                ${travelHtml}
                <div class="timeline-node">
                    ${nodeContent}
                </div>
                <div class="timeline-card">
                    ${timeRangeHtml}
                    <h3>${item.name}</h3>
                    <p class="address"><i class="fa-solid fa-map-pin" style="margin-right:4px;"></i> ${item.address}</p>
                    ${badgesHtml ? `<div class="badges">${badgesHtml}</div>` : ''}
                </div>
            `;
            timeline.appendChild(el);
        });

        // Update Stats
        tripStats.innerHTML = `
            <span class="stat-item"><i class="fa-solid fa-map-location-dot"></i> ${stopsCount} Stops</span>
            <span class="stat-item"><i class="fa-solid fa-wallet"></i> $${totalCost.toFixed(2)}</span>
        `;
    }

    // 5. Geocoding and Map Plotting
    function clearMap() {
        mapMarkers.forEach(m => map.removeLayer(m));
        if (mapPath) map.removeLayer(mapPath);
        mapMarkers = [];
        waypoints = [];
        mapPath = null;
    }

    async function plotOnMap(itinerary) {
        const geoStatus = document.getElementById('geo-status');
        geoStatus.style.display = 'block';

        const delay = (ms) => new Promise(res => setTimeout(res, ms));

        // Deduplicate addresses slightly but we need them in order to draw the path
        for (let i = 0; i < itinerary.length; i++) {
            const item = itinerary[i];
            
            let safeType = item.type ? item.type.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'default';
            if (item.food) safeType = 'food';
            if (i === 0) safeType = 'start';
            if (i === itinerary.length - 1) safeType = 'end';
            
            let catClass = `type-${safeType}`;
            
            let iconStr = `<span>${i + 1}</span>`;
            if (i === 0) iconStr = '<i class="fa-solid fa-plane-departure"></i>';
            if (i === itinerary.length - 1) iconStr = '<i class="fa-solid fa-flag-checkered"></i>';

            // Create custom Leaflet icon
            const customIcon = L.divIcon({
                className: 'custom-icon-container',
                html: `<div class="custom-map-marker ${catClass}">${iconStr}</div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15],
                popupAnchor: [0, -15]
            });

            // Nominatim geocoding (with rate limiting respect ~ 1 req / sec)
            try {
                // Using a generic user-agent to bypass basic blocks, but Nominatim requires email/app name ideally.
                // We'll append Seattle if it doesn't have it, but the DB already has Seattle, WA.
                const addressQuery = encodeURIComponent(item.address);
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${addressQuery}`);
                const data = await res.json();

                if (data && data.length > 0) {
                    let lat = parseFloat(data[0].lat);
                    let lon = parseFloat(data[0].lon);
                    
                    // Jitter overlapping pins to ensure they're all visible
                    const overlapCount = waypoints.filter(p => Math.abs(p[0] - lat) < 0.0001 && Math.abs(p[1] - lon) < 0.0001).length;
                    if (overlapCount > 0) {
                        lat += overlapCount * 0.0008; // Small shift
                        lon += overlapCount * 0.0008;
                    }
                    
                    waypoints.push([lat, lon]);

                    const marker = L.marker([lat, lon], { icon: customIcon })
                        .addTo(map)
                        .bindPopup(`<strong>${item.name}</strong><br>${item.address}`);
                    
                    mapMarkers.push(marker);

                    // Update map path drawing progressively
                    if (mapPath) map.removeLayer(mapPath);
                    mapPath = L.polyline(waypoints, {
                        color: '#3b82f6', 
                        weight: 4, 
                        opacity: 0.7, 
                        dashArray: '10, 10',
                        lineCap: 'round'
                    }).addTo(map);

                    // Center map dynamically to bounding box
                    if (waypoints.length > 1) {
                        map.fitBounds(L.latLngBounds(waypoints), { padding: [50, 50] });
                    } else if (waypoints.length === 1) {
                        map.setView([lat, lon], 14);
                    }
                }
            } catch(e) {
                console.warn("Geocoding failed for:", item.address, e);
            }

            // Delay 1s to satisfy Nominatim ToS
            if (i < itinerary.length - 1) {
                await delay(1000);
            }
        }

        geoStatus.style.display = 'none';
    }
});
