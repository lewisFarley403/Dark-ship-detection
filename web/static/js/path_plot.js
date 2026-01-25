var fetch_btn = document.getElementById('fetch-btn');
var datetime_selector = document.getElementById('start-date')
var MMSI_search_input = document.getElementById('mmsi-search-input')
var MMSI_search_button = document.getElementById('mmsi-search-button')
var predict_button = document.getElementById('predict')
var timestep_input = document.getElementById('prediction-timestep')


var polylineByMMSI = {}; // key is MMSI and value is the path obj
var currently_selected_node = null;
predict_button.onclick = predict_vessel_course
MMSI_search_button.onclick=(e)=>{
    const mmsi_to_search = MMSI_search_input.value
    console.log(`searching ${mmsi_to_search}`)
    const res = polylineByMMSI[mmsi_to_search]
    if (!res){
        alert(`No Vessel Found With MMSI: ${mmsi_to_search}`)
        return
    }
    console.log(res)
    res.bringToFront();
    Object.values(polylineByMMSI).forEach(p =>
        p.setStyle({ opacity: 0.2, weight: 2 })
    );

    res.setStyle({
        color: 'yellow',
        weight: 6,
        opacity: 1
    });

    res.bringToFront();

    map.fitBounds(res.getBounds(), {
        padding: [60, 60],
        maxZoom: 14,
        animate: true
    });
    
}
function getShipTypeDescription(code) {
    if (!code) return `Unknown Type (${code})`;
    
    const shortCode = code.toString().toUpperCase();

    const typeMapping = {
        // --- 1. COMMON GENERIC TYPES ---
        'HSC': 'High Speed Craft (Fast Ferry/Catamaran)',
        'PSG': 'Passenger Ship',
        'PAX': 'Passenger Vessel', // Synonym for PSG
        'MER': 'Merchant Ship',    // General commercial vessel
        'CGO': 'General Cargo',
        'TKR': 'Tanker',
        'TNK': 'Tanker',
        'YHT': 'Yacht',
        'PLS': 'Pleasure Craft / Yacht',
        'FSH': 'Fishing Vessel',
        'TUG': 'Tugboat',
        'PLT': 'Pilot Vessel',
        'SAR': 'Search and Rescue',
        'PRT': 'Port Tender',      // Small service boat for harbor ops

        // --- 2. CARGO VARIANTS ---
        'BLK': 'Bulk Carrier',
        'BBU': 'Bulk Carrier',     // Standard Bulk
        'BCB': 'Bulk/Container Carrier',
        'BCE': 'Cement Carrier',
        'CON': 'Container Ship',
        'UCC': 'Container Ship',   // Unitized Cargo Container
        'GGC': 'General Cargo',
        'RORO': 'Roll-on/Roll-off (Vehicles)',
        'URR': 'Roll-on/Roll-off',
        'PCC': 'Pure Car Carrier',
        'VEC': 'Vehicle Carrier',
        'REE': 'Reefer (Refrigerated Cargo)',
        'GRF': 'Reefer',

        // --- 3. TANKER VARIANTS ---
        'OIL': 'Oil Tanker',
        'TCR': 'Crude Oil Tanker',
        'TPD': 'Product Tanker (Refined Products)',
        'CHM': 'Chemical Tanker',
        'TCH': 'Chemical Tanker',
        'GAS': 'Gas Tanker',
        'LNG': 'LNG Tanker (Liquefied Natural Gas)',
        'LPG': 'LPG Tanker (Liquefied Petroleum Gas)',
        'ASP': 'Asphalt/Bitumen Tanker',

        // --- 4. PASSENGER & FERRY ---
        'FER': 'Ferry',
        'PRR': 'Passenger Ro-Ro Ferry',
        'CRU': 'Cruise Ship',
        'MPR': 'Passenger Ship',

        // --- 5. SPECIAL OPERATIONS & SERVICE ---
        'DRE': 'Dredger',
        'DHD': 'Hopper Dredger',
        'DIV': 'Diving Support Vessel',
        'OSV': 'Offshore Supply Vessel',
        'SUP': 'Supply Vessel',
        'WIG': 'Wing-In-Ground (Ekranoplan)',
        'RES': 'Research / Survey Vessel',
        'RRE': 'Research Vessel',
        'CAB': 'Cable Layer',
        'OCL': 'Cable Layer',
        'ICE': 'Icebreaker',
        'TOW': 'Towing Vessel',
        'SAL': 'Salvage Vessel',
        'LIV': 'Livestock Carrier',

        // --- 6. AUTHORITY & MILITARY ---
        'MIL': 'Military / Naval',
        'NAV': 'Naval Vessel',
        'LAW': 'Law Enforcement / Patrol',
        'PAT': 'Patrol Vessel',
        'MED': 'Medical Transport / Hospital Ship',
        'ANT': 'Anti-Pollution / Environmental',

        // --- 7. STATIONARY / OTHER ---
        'SPP': 'Spare / Unspecified',
        'OTH': 'Other Type',
        'N/A': 'Not Available',
        'UNK': 'Unknown',
        'LHS': 'Lighthouse / Aid to Navigation',
        'BUI': 'Buoy',
        'FLT': 'Floating Structure (Platform)'
    };

    // Return the readable name, or keep the original code (e.g., "XYZ") if we don't know it
    return typeMapping[shortCode] || shortCode;
}
function hide_tbls(e){
    var tbls = document.getElementById('tbls');
    tbls.style.display = 'none';

    panel = document.getElementById('sidepanel')
    panel.style.display = "none";
    currently_selected_node = null;

}
function show_dynamic_ship_info(data) {

    // Helper to safely set text content (handles missing IDs gracefully)
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.innerText = text || '-'; // Use '-' if data is null/empty
    };
    var tbls = document.getElementById('tbls');
    console.log(tbls)
    tbls.style.display = 'flex';
    // --- 1. POPULATE STATIC DATA ---
    setText('val-MMSI', data.MMSI);
    setText('val-IMO', data.IMO);
    setText('val-Name', data.Name);
    setText('val-IRCS', data.IRCS);
    setText('val-Flag', data.Flag);
    setText('val-Type', getShipTypeDescription(data.Type));
    
    // Combine Length and Width (e.g., "76m x 14m")
    setText('val-Dim', `${data.Length}m x ${data.Width}m`);
    
    // Combine Offsets
    setText('val-Offset', `Stern: ${data.ReceiverSternOffset}m / Port: ${data.ReceiverPortOffset}m`);


    // --- 2. POPULATE DYNAMIC DATA ---
    
    // Format Date (remove the 'Timestamp' wrapper if it came as string, or format raw string)
    // Assuming data.DTG is a string like "2023-06-01 09:47:01"
    setText('val-DTG', data.DTG);

    // Format Position (Round to 4 decimals)
    setText('val-Pos', `${parseFloat(data.Lat).toFixed(4)} / ${parseFloat(data.Lon).toFixed(4)}`);

    // Format Speed and Course
    setText('val-SpeedCourse', `${data.Speed} kn / ${data.Course}°`);

    setText('val-Status', data.Status);
    setText('val-Destination', data.Destination); // Will show '-' if empty string
    setText('val-ETA', data.ETA);

    // Boolean Logic for Hazardous (0 = No, 1 = Yes)
    const isHaz = (data.Hazardous == 1 || data.Hazardous === 'True');
    const hazCell = document.getElementById('val-Hazardous');
    if (hazCell) {
        hazCell.innerText = isHaz ? "YES (Hazardous)" : "No";
        hazCell.style.color = isHaz ? "red" : "green"; // Visual cue
        hazCell.style.fontWeight = isHaz ? "bold" : "normal";
    }
}

function open_tracking_window(data){
    var panel = document.getElementById('sidepanel')
    panel.style.display = "block";
    currently_selected_node = data;
}

function drawVesselPaths(pathsData) {
    
    // Loop through every ship (MMSI) in the data
    for (const [mmsi, pings] of Object.entries(pathsData)) {
        var randomColor = '#' + Math.floor(Math.random()*16777215).toString(16);
        var latlngs = []
        for (ping of pings){
            latlngs.push([ping.Lat,ping.Lon])
        }

        
        // 1. Generate a random color for this ship so they don't look the same
        

        // 2. Create the Polyline
        const path = L.polyline(latlngs, {
            color: randomColor,
            weight: 3,        // Thickness of the line
            opacity: 0.8,     // See-through
            smoothFactor: 0   // Higher = smoother line, less detail
        });
        polylineByMMSI[mmsi] = path;

        // 3. Add a Popup (so you can click the line to see who it is)
        path.bindPopup(`<b>Vessel MMSI:</b> ${mmsi}`);


        // 4. Add to Map
        path.addTo(map);


        for (const ping of pings){
            function handle_node_click(e){
                show_dynamic_ship_info(ping)
                open_tracking_window(ping);
                // predict_vessel_course(ping)
            
            }
            L.circleMarker([ping.Lat, ping.Lon], {
                // renderer: myRenderer, // Optimization
                radius: 10,            // Small radius
                color: randomColor,   // Match the line
                fillColor: '#fff',    // White center
                fillOpacity: 1,
                weight: 1
            })
            .bindPopup(`
                <b>MMSI:</b> ${mmsi}<br>
                <b>Time:</b> ${ping.DTG}<br>
                <b>Speed:</b> ${ping.Speed}
            `)
            .on('click',handle_node_click)
            .on('popupclose', hide_tbls)
            .addTo(map);
        }
        
    }
}


fetch_btn.onclick=()=>{
    console.log('clicking something')
    console.log(datetime_selector)
    startDate = datetime_selector.value
    fetch('/api/get_paths',{
        method:'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({start_date: startDate}),
    })
    .then(response=>response.json())
    .then((data)=>{drawVesselPaths(data);})
}


function predict_vessel_course(e){
    var predictor = document.getElementById('selector').value
    console.log(currently_selected_node)
    const dt =timestep_input.value
    fetch('/api/predict_path',{
        method:'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({node_data: currently_selected_node,predictor:predictor,dt:dt}),
    })
    .then(response=>response.json())
    .then(data=>logPredicted(data))


}

function logPredicted(data) {
    const prediction = data.prediction;

    if (!Array.isArray(prediction) || prediction.length !== 2) {
        console.error('Invalid prediction format:', data);
        return;
    }

    const [lat, lon] = prediction;

    const mmsi = currently_selected_node?.MMSI;
    const polyline = polylineByMMSI[mmsi];
    if (!polyline) return;

    // polyline.addLatLng([Number(lat), Number(lon)]);

    // Optional: mark predicted point
    L.circleMarker([lat, lon], {
        radius: 6,
        color: 'red',
        fillOpacity: 1
    }).addTo(map);
}