// 1. Setup Elements
var dropdown = document.getElementById('run-select');
const ctx = document.getElementById('liveChart').getContext('2d');

// 2. Initialize Chart
const myChart = new Chart(ctx, {
    type: 'line',
    data: {
            labels: [], // Initialize labels (Epochs)
            datasets: [
                // --- Dataset 0 (Red): mAP50 ---
                {
                    label: 'mAP50 (B)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    tension: 0.1,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 1,
                },
                // --- Dataset 1 (Blue): mAP50-95 ---
                {
                    label: 'mAP50-95 (B)',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    tension: 0.1,
                    borderWidth: 2,
                    pointRadius: 0
                }
            ]
        },
    
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false, 
        interaction: {
            mode: 'index',
            intersect: false,
        },
        scales: {
            x: {
                title: { display: true, text: 'Epoch' }
            },
            y: {
                beginAtZero: true,
                title: { display: true, text: 'mAP50' }
            }
        }
    }
});

// 3. Fix the Dropdown Listener
dropdown.addEventListener('change', function() {
    var selectedRun = this.value;
    console.log('Switched to run:', selectedRun);
    getTrainingProgress(selectedRun); // <--- THIS WAS MISSING
});

// 4. Fetch Function with Debugging
function getTrainingProgress(run) {
    if (!run) return;

    fetch(`/api/training_data?run=${run}`)
        .then(response => response.json())
        .then(data => {
            // --- DEBUGGING BLOCK ---
            console.log("Received Data:", data); 
            
            // Check if the key actually exists
            const keyName = 'metrics/mAP50(B)';
            const keyName2 ='metrics/mAP50-95(B)';
            if (!data[keyName]) {
                console.error(`Key "${keyName}" not found! Available keys:`, Object.keys(data));
                // Try to find the closest matching key automatically?
                // const fallbackKey = Object.keys(data).find(k => k.includes('mAP50'));
                return;
            }
            // -----------------------

            const epochs = data.epoch;
            const map_50 = data[keyName];

            // Update Chart Data
            myChart.data.labels = epochs;
            
            myChart.data.datasets[0].data = map_50;
            myChart.data.datasets[1].data = data[keyName2];
            
            // Update the chart
            myChart.update(); 
        })
        .catch(error => console.error('Error fetching training progress:', error));
}

// 5. Initial Load (Poll every 5s)
setInterval(() => {
    var selectedRun = dropdown.value;
    if (selectedRun) {
        getTrainingProgress(selectedRun);
    }
}, 5000);

// Trigger immediately on load if a value is selected
if(dropdown.value) {
    getTrainingProgress(dropdown.value);
}