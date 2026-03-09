console.log('js loaded')

let drawnLayer = null;
// let map;
let drawControl;
let coords_clicked = []; // max this at 2
var fetch_btn = document.getElementById('fetch-btn');
let date_p = document.getElementById('datetime')



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

    if (!startDate || !endDate) {
      output.textContent = "Please select both start and end dates.";
      return;
    }

    if (coords_clicked.length<2) {
      output.textContent = "Please draw a bounding box on the map.";
      return;
    }


    output.textContent = "Fetching images...";
    var bbox = coords_clicked
    const res = await fetch("/api/get_images", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bbox, start_date: startDate, end_date: endDate }),
    });

    const data = await res.json();
    console.log('received data ',data)
    output.textContent = data.message || "Done!";
    console.log(data)


    set_map_img_overlay(data)
  });
    //add shaded area to map

    
    

    
    map.on("click", (e) => {
    const { lat, lng } = e.latlng;
    console.log("Clicked at:", lat, lng);
    if (coords_clicked.length <2){
    // Example: Add a marker at the click location
        coords_clicked.push([lat,lng])
        L.marker([lat, lng])
        .addTo(map)
        .bindPopup(`Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`)
        .openPopup();
        L.rectangle(coords_clicked, {
        // color: "#0078d7",     // border color
        weight: 2,            // border thickness
        // fillColor: "#0078d7", // fill color
        fillOpacity: 0      // transparency (0–1)
        }).addTo(map);
        console.log(coords_clicked.length)
        }
  });
});
function set_map_img_overlay(data) {
    if (!data || !data.tiles || data.tiles.length === 0) {
        console.error("No image tiles found.");
        return;
    }


    if (drawnLayer && map.hasLayer(drawnLayer)) {
        map.removeLayer(drawnLayer);
    }

    if (data.timestamp && date_p) {
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
    });
    console.log(data.pings)
    if (data.pings && Array.isArray(data.pings)) {
        data.pings.forEach(info => {
            // Leaflet expects [lat, lng]. 
            // If your data is [lng, lat], use: [coord[1], coord[0]]
            const latLng = info.coord; 


            L.circleMarker(latLng, {
                radius: 6,
                fillColor: "#ff3388", // Bright pink/red to pop against grayscale
                color: "#fff",        // White border
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            })
            .addTo(map)
            .bindPopup(`Coordinate: ${latLng[0].toFixed(4)}, ${latLng[1].toFixed(4)}`);
        });
    }
      if (data.ai_pings && Array.isArray(data.ai_pings)) {
        data.ai_pings.forEach(info => {
            // Leaflet expects [lat, lng]. 
            // If your data is [lng, lat], use: [coord[1], coord[0]]
            const latLng = info; 


            L.circleMarker(latLng, {
                radius: 6,
                fillColor: "#00FF00", // Bright pink/red to pop against grayscale
                color: "#fff",        // White border
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            })
            .addTo(map)
            .bindPopup(`Coordinate: ${latLng[0].toFixed(4)}, ${latLng[1].toFixed(4)}`);
        });
    }
    const firstBounds = data.tiles[0].leaflet_bounds;
    map.fitBounds(firstBounds);
}
