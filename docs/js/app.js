// Configuration
const API_URL = 'YOUR_API_URL';  // Replace with your API URL
const UPDATE_INTERVAL = 2000;  // Update every 2 seconds

// Initialize charts
const hrChart = new Chart(document.getElementById('hrChart'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Heart Rate',
            data: [],
            borderColor: 'rgb(255, 99, 132)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                suggestedMax: 120
            }
        }
    }
});

const spo2Chart = new Chart(document.getElementById('spo2Chart'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'SpO2',
            data: [],
            borderColor: 'rgb(54, 162, 235)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                suggestedMax: 100
            }
        }
    }
});

// Update dashboard with new data
function updateDashboard(data) {
    // Update current readings
    const latestReading = data[data.length - 1];
    document.getElementById('currentHR').textContent = 
        `${Math.round(latestReading.heart_rate)} BPM`;
    document.getElementById('currentSpO2').textContent = 
        `${Math.round(latestReading.spo2)}%`;

    // Update charts
    const timestamps = data.map(reading => {
        const date = new Date(reading.timestamp);
        return date.toLocaleTimeString();
    });
    const heartRates = data.map(reading => reading.heart_rate);
    const spo2Values = data.map(reading => reading.spo2);

    // Update heart rate chart
    hrChart.data.labels = timestamps;
    hrChart.data.datasets[0].data = heartRates;
    hrChart.update();

    // Update SpO2 chart
    spo2Chart.data.labels = timestamps;
    spo2Chart.data.datasets[0].data = spo2Values;
    spo2Chart.update();
}

// Fetch data from API
async function fetchData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Update dashboard periodically
setInterval(fetchData, UPDATE_INTERVAL);

// Initial fetch
fetchData();
