// Configuration
const API_URL = 'https://raw.githubusercontent.com/sangajay2/ai/docs-only/docs/data/readings.json';  // GitHub raw content URL
const UPDATE_INTERVAL = 2000;  // Update every 2 seconds
const DEBUG = true;  // Enable console logging

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
    try {
        // Get the latest reading
        const latestReading = data[data.length - 1];
        if (DEBUG) console.log('📊 Latest reading:', latestReading);
        
        // Update current readings
        document.getElementById('currentHR').textContent = 
            `${Math.round(latestReading.heart_rate)} BPM`;
        document.getElementById('currentSpO2').textContent = 
            `${Math.round(latestReading.spo2)}%`;
            
        // Add source indicator if available
        const sourceText = latestReading.source ? ` (${latestReading.source})` : '';
        document.getElementById('currentHR').title = `Last updated: ${new Date(latestReading.timestamp * 1000).toLocaleString()}${sourceText}`;

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
        if (DEBUG) console.log('🔍 Fetching data from:', API_URL);
        
        const response = await fetch(API_URL, {
            cache: 'no-store'  // Disable caching to get fresh data
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        if (DEBUG) console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        if (DEBUG) console.log('📊 Received data:', data.length, 'readings');
        
        if (data && Array.isArray(data) && data.length > 0) {
            updateDashboard(data);
            if (DEBUG) console.log('✅ Dashboard updated with latest data');
        } else {
            console.warn('⚠️ No readings found in the data');
        }
    } catch (error) {
        console.error('❌ Error fetching data:', error);
    }
}

// Update dashboard periodically
setInterval(fetchData, UPDATE_INTERVAL);

// Initial fetch
fetchData();

