console.log('js loaded')

let drawnLayer = null;
// let map;
let drawControl;
let coords_clicked = []; // max this at 2
var fetch_btn = document.getElementById('fetch-btn');
let date_p = document.getElementById('datetime')

function set_map_img_overlay(data){
    console.log('DATA')
    console.log(data)
    var datetime = data.meta.datetime
    var bbox = [[data.bbox[1],data.bbox[0]],[data.bbox[3],data.bbox[2]]]
    console.log(datetime)
    const dateObj = new Date(datetime);
    date_p.textContent = dateObj.toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    });
    // date_p.setAttribute('datetime',datetime)
    
    const imageUrl = `/api/image_overlay?id=${data.id}`;
    console.log(bbox)
    L.imageOverlay(imageUrl, bbox, { opacity: 1 }).addTo(map); 
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

  // Initialize Leaflet map
  
  // map = L.map("map").setView([50.73, -3.52], 13);

  // L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  //   attribution: "© OpenStreetMap contributors",
  // }).addTo(map);

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
    var first = data.img_data[0]

    set_map_img_overlay(first)
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
        color: "#0078d7",     // border color
        weight: 2,            // border thickness
        fillColor: "#0078d7", // fill color
        fillOpacity: 0.3      // transparency (0–1)
        }).addTo(map);
        console.log(coords_clicked.length)
        }
  });
});
