console.log('js loaded')

let drawnLayer = null;
// let map;
let drawControl;
let coords_clicked = []; // max this at 2
var fetch_btn = document.getElementById('fetch-btn');
let date_p = document.getElementById('datetime')
let sidepanel = document.getElementById('sidepanel')
let temp_wipe = document.getElementById('temp-wipe-test');
var overlay = document.getElementById('loading-overlay');
temp_wipe.onclick = clearMapLayers
// until we get the data
let catalogue = null; 
let current_date = null;

// Arrays to keep track of added layers for clearing
let imageOverlays = [];
let pingMarkers = [];
let aiPingMarkers = [];
let pathPredMarkers = [];
let selectionMarkers = [];
let selectionRectangles = [];

let move_left = document.getElementById('move-earlier')
let move_right = document.getElementById('move-later')


function showLoadingSpinner() {
  console.log('showing loading spinner ')

  console.log('loading overlay ')
  console.log(overlay)
  if (overlay) overlay.classList.add('active');
  document.body.style.pointerEvents = 'none';
}
function hideLoadingSpinner() {

  if (overlay) overlay.classList.remove('active');
  document.body.style.pointerEvents = '';
}

async function load_data(startDate,endDate){
    if (!startDate || !endDate) {
      // output.textContent = "Please select both start and end dates.";
      console.log('Please select both start and end dates.')
      return;
    }

    if (coords_clicked.length<2) {
      // output.textContent = "Please draw a bounding box on the map.";
      console.log("Please draw a bounding box on the map.")
      return;
    }

    showLoadingSpinner();
    
    try {
      var bbox = coords_clicked
      console.log(`bbox: ${bbox}`)
      const res = await fetch("/api/get_images", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bbox, start_date: startDate, end_date: endDate }),
      });

      const data = await res.json();
      console.log('received data ',data)
      // output.textContent = data.message || "Done!";
      console.log(data)
      set_map_img_overlay(data)
    } finally {
      hideLoadingSpinner();
    }
}

move_right.onclick = async() => {
    if (current_date){
        try {
            console.log('CATALOGUE')
            console.log(catalogue)
            console.log('CURRENT DATE')
            console.log(current_date.toUTCString())
            // Create a new date object with one second subtracted
            let new_date_index = catalogue.indexOf(current_date.toUTCString())
            console.log('current index:', new_date_index);
            new_date = catalogue[new_date_index-1]
            console.log('New date:', new_date);
            
            if (!new_date){
              console.error('no data before this date')
              return
            }
            new_date = new Date(new_date)
            // Wait for the data to load
            await load_data(new_date, new_date);
            console.log('got new data')
        } catch (error) {
            console.error('Error loading data:', error);
            // You could show an error message to the user here
        }
    }
}
move_left.onclick = async () => {
    if (current_date){
        try {
            console.log('CATALOGUE')
            console.log(catalogue)
            console.log('CURRENT DATE')
            console.log(current_date.toUTCString())
            // Create a new date object with one second subtracted
            let new_date_index = catalogue.indexOf(current_date.toUTCString())
            console.log('current index:', new_date_index);
            new_date = catalogue[new_date_index+1]
            console.log('New date:', new_date);
            
            if (!new_date){
              console.error('no data before this date')
              return
            }
            new_date = new Date(new_date)
            // Wait for the data to load
            await load_data(new_date, new_date);
            console.log('got new data')
        } catch (error) {
            console.error('Error loading data:', error);
            // You could show an error message to the user here
        }
    }
}
fetch_btn.onclick=()=>{
    const startInput = document.getElementById("start-date");
    const endInput = document.getElementById("end-date");

    // Get their values
    const startDate = startInput.value; // e.g., "2025-05-01"
    const endDate = endInput.value;     // e.g., "2025-05-20" 
    console.log(startDate.length)

}
document.addEventListener("DOMContentLoaded", () => {
  const fetchBtn = document.getElementById("fetch-btn");
  const output = document.getElementById("output");



  // Add draw controls
  const drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  drawControl = new L.Control.Draw({
    draw: {
      polygon: false,
      marker: false,
      circle: false,
      circlemarker: false,
      polyline: false,
      rectangle: true
    },
    edit: {
      featureGroup: drawnItems
    }
  });
  map.addControl(drawControl);

  map.on(L.Draw.Event.CREATED, (e) => {
    if (drawnLayer) drawnItems.removeLayer(drawnLayer);
    drawnLayer = e.layer;
    drawnItems.addLayer(drawnLayer);
  });

  fetchBtn.addEventListener("click", async () => {
    const startDate = document.getElementById("start-date").value;
    const endDate = document.getElementById("end-date").value;
    load_data(startDate,endDate)
  });
    //add shaded area to map

// async function load_data(startDate,endDate){
//     if (!startDate || !endDate) {
//       // output.textContent = "Please select both start and end dates.";
//       return;
//     }

//     if (coords_clicked.length<2) {
//       // output.textContent = "Please draw a bounding box on the map.";
//       return;
//     }


//     // output.textContent = "Fetching images...";
//     var bbox = coords_clicked
//     const res = await fetch("/api/get_images", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ bbox, start_date: startDate, end_date: endDate }),
//     });

//     const data = await res.json();
//     console.log('received data ',data)
//     // output.textContent = data.message || "Done!";
//     console.log(data)


//     set_map_img_overlay(data)
// }
    

    
    map.on("click", (e) => {
    const { lat, lng } = e.latlng;
    console.log("Clicked at:", lat, lng);
    if (coords_clicked.length < 2){
    // Example: Add a marker at the click location
        coords_clicked.push([lat,lng])
        const marker = L.marker([lat, lng])
        .addTo(map)
        .bindPopup(`Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`)
        .openPopup();
        selectionMarkers.push(marker);
        
        // Only create rectangle when we have 2 points
        if (coords_clicked.length === 2) {
            const rectangle = L.rectangle(coords_clicked, {
            // color: "#0078d7",     // border color
            weight: 2,            // border thickness
            // fillColor: "#0078d7", // fill color
            fillOpacity: 0      // transparency (0–1)
            }).addTo(map);
            selectionRectangles.push(rectangle);
        }
        
        console.log(coords_clicked.length)
        }
  });
});
function clearMapLayers() {
    // Remove all image overlays
    imageOverlays.forEach(overlay => {
        if (map.hasLayer(overlay)) {
            map.removeLayer(overlay);
        }
    });
    imageOverlays = [];

    // Remove all ping markers
    pingMarkers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    pingMarkers = [];

    // Remove all AI ping markers
    aiPingMarkers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    aiPingMarkers = [];

    // Remove all selection markers
    selectionMarkers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    selectionMarkers = [];

    pathPredMarkers.forEach(marker=>{
      if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    })

    // Remove all selection rectangles
    selectionRectangles.forEach(rectangle => {
        if (map.hasLayer(rectangle)) {
            map.removeLayer(rectangle);
        }
    });
    selectionRectangles = [];
}

function set_map_img_overlay(data) {
  console.log(data)
    if (!data || !data.tiles || data.tiles.length === 0) {
        console.error("No image tiles found.");
        return;
    }

    // Clear existing layers before adding new ones
    clearMapLayers();
    
    // Reset selection coordinates
    // coords_clicked = [];

    if (drawnLayer && map.hasLayer(drawnLayer)) {
        map.removeLayer(drawnLayer);
    }

    if (data.timestamp && date_p) {
        current_date = new Date(data.timestamp)
        date_p.textContent = `Scene Date: ${new Date(data.timestamp).toLocaleString()}`;
    }

    data.tiles.forEach(tile => {
        const imageUrl = tile.image_url;
        const bounds = tile.leaflet_bounds;

        const overlay = L.imageOverlay(imageUrl, bounds, {
            opacity: 1.0,
            interactive: true,
            alt: `Satellite Tile ${tile.row}_${tile.col}`,
            // 2. APPLY GRAYSCALE VIA CSS
            className: 'grayscale-satellite' 
        }).addTo(map);

        overlay.bringToFront();
        // Store reference for later clearing
        imageOverlays.push(overlay);
    });
    console.log(data.pings)
    if (data.pings && Array.isArray(data.pings)) {
        data.pings.forEach(info => {
            // Leaflet expects [lat, lng]. 
            // If your data is [lng, lat], use: [coord[1], coord[0]]
            const latLng = info.coord; 


            const marker = L.circleMarker(latLng, {
                radius: 6,
                fillColor: "#ff3388", // Bright pink/red to pop against grayscale
                color: "#fff",        // White border
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            })
            .addTo(map)
            .bindPopup(`Coordinate: ${latLng[0].toFixed(4)}, ${latLng[1].toFixed(4)}, MMSI: ${info.mmsi}`);
            
            // Store reference for later clearing
            pingMarkers.push(marker);
        });
    }
      if (data.ai_pings && Array.isArray(data.ai_pings)) {
        data.ai_pings.forEach(info => {
            // Leaflet expects [lat, lng]. 
            // If your data is [lng, lat], use: [coord[1], coord[0]]
            const latLng = info; 


            const marker = L.circleMarker(latLng, {
                radius: 6,
                fillColor: "#00FF00", // Bright pink/red to pop against grayscale
                color: "#fff",        // White border
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            })
            .addTo(map)
            .bindPopup(`Coordinate: ${latLng[0].toFixed(4)}, ${latLng[1].toFixed(4)}`);
            
            // Store reference for later clearing
            aiPingMarkers.push(marker);
        });
    }
      if (data.catalogue && Array.isArray(data.catalogue)) {
        catalogue = data.catalogue;
        // TODO put all of these into the side panel
        data.catalogue.forEach(item =>{
          const pTag = document.createElement('p');
    

          pTag.textContent = item; 
          

          sidepanel.appendChild(pTag);
        })
    }
    if (data.catalogue && Array.isArray(data.catalogue)) {
        catalogue = data.catalogue;
        // TODO put all of these into the side panel
        data.catalogue.forEach(item =>{
          const pTag = document.createElement('p');
    

          pTag.textContent = item; 
          

          sidepanel.appendChild(pTag);
        })
    }
    if (data.path_preds){
      for (const [mmsi, dataArray] of Object.entries(data.path_preds)) {
          const marker = L.circleMarker(dataArray, {
                radius: 6,
                fillColor: "#00FFFF", // Bright pink/red to pop against grayscale
                color: "#fff",        // White border
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            })
            .addTo(map)
            .bindPopup(`Predicted Coordinate: ${dataArray[0].toFixed(4)}, ${dataArray[1].toFixed(4)}, MMSI: ${mmsi}`);
            
            // Store reference for later clearing
            pathPredMarkers.push(marker);
          
            // Draw line from last known ping to predicted point
            // Find last ping for this MMSI
            let lastPing = null;
            if (data.pings && Array.isArray(data.pings)) {
              for (const ping of data.pings) {
                if (ping.mmsi === mmsi) {
                  lastPing = ping.coord;
                  break;
                }
              }
            }
            if (lastPing) {
              const line = L.polyline([lastPing, dataArray], {
                color: '#00FFFF',
                weight: 2,
                opacity: 0.8
              }).addTo(map);
              pathPredMarkers.push(line);
            }
}
    }
    const firstBounds = data.tiles[0].leaflet_bounds;
    map.fitBounds(firstBounds);
}
