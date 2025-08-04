// Enhanced Heart Rate Monitor Dashboard
// Configuration
const API_URL = 'https://raw.githubusercontent.com/sangajay2/ai/docs-only/docs/data/readings.json';
const UPDATE_INTERVAL = 2000;  // Update every 2 seconds
const DEBUG = true;  // Enable console logging
const MAX_DATA_POINTS = 50;  // Show last 50 readings on charts

// Global variables
let hrChart, spo2Chart, tempChart;
let lastUpdateTime = 0;
let consecutiveErrors = 0;
let isOnline = true;

// Zone definitions matching ESP32 code
const HR_ZONES = {
    'calm': { color: '#10B981', emoji: '😌', label: 'Very Relaxed' },
    'normal': { color: '#3B82F6', emoji: '😊', label: 'Normal' },
    'elevated': { color: '#F59E0B', emoji: '😐', label: 'Elevated' },
    'exercise': { color: '#8B5CF6', emoji: '💪', label: 'Exercise' },
    'high': { color: '#EF4444', emoji: '⚠️', label: 'High' }
};

// Initialize charts
function initializeCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: '#374151'
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#6B7280' },
                grid: { color: '#E5E7EB' }
            },
            y: {
                ticks: { color: '#6B7280' },
                grid: { color: '#E5E7EB' }
            }
        },
        elements: {
            point: {
                radius: 3,
                hoverRadius: 5
            }
        }
    };

    // Heart Rate Chart
    hrChart = new Chart(document.getElementById('hrChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Heart Rate (BPM)',
                data: [],
                borderColor: '#EF4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    beginAtZero: false,
                    suggestedMin: 50,
                    suggestedMax: 120
                }
            }
        }
    });

    // SpO2 Chart
    spo2Chart = new Chart(document.getElementById('spo2Chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'SpO2 (%)',
                data: [],
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    beginAtZero: false,
                    suggestedMin: 85,
                    suggestedMax: 100
                }
            }
        }
    });

    // Temperature Chart
    tempChart = new Chart(document.getElementById('tempChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature (°C)',
                data: [],
                borderColor: '#10B981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    beginAtZero: false,
                    suggestedMin: 35,
                    suggestedMax: 40
                }
            }
        }
    });
}

// Update status indicator
function updateStatus(status, message) {
    const statusElement = document.getElementById('status');
    const statusDot = document.getElementById('statusDot');
    
    if (!statusElement || !statusDot) return;
    
    const statusClasses = {
        'online': 'bg-green-500',
        'offline': 'bg-red-500',
        'connecting': 'bg-yellow-500'
    };
    
    // Remove all status classes
    Object.values(statusClasses).forEach(cls => {
        statusDot.classList.remove(cls);
    });
    
    // Add new status class
    statusDot.classList.add(statusClasses[status] || 'bg-gray-500');
    statusElement.textContent = message;
}

// Update heart rate zone display
function updateZoneDisplay(zone, heartRate) {
    const zoneElement = document.getElementById('currentZone');
    const zoneInfo = HR_ZONES[zone] || HR_ZONES['normal'];
    
    if (zoneElement) {
        zoneElement.innerHTML = `
            <span style="color: ${zoneInfo.color}; font-size: 1.5rem;">${zoneInfo.emoji}</span>
            <span style="color: ${zoneInfo.color}; font-weight: bold;">${zoneInfo.label}</span>
        `;
    }
    
    // Update heart rate with zone color
    const hrElement = document.getElementById('currentHR');
    if (hrElement) {
        hrElement.style.color = zoneInfo.color;
    }
}

// Format timestamp for display
function formatTime(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// Update dashboard with new data
function updateDashboard(data) {
    try {
        if (!data || data.length === 0) {
            console.warn('⚠️ No data available');
            updateStatus('offline', 'No data available');
            return;
        }

        // Get the latest reading
        const latestReading = data[data.length - 1];
        if (DEBUG) console.log('📊 Latest reading:', latestReading);
        
        // Update current readings
        const currentTime = new Date();
        const dataTime = new Date(latestReading.timestamp * 1000);
        const timeDiff = (currentTime - dataTime) / 1000; // seconds
        
        // Check if data is fresh (less than 2 minutes old)
        if (timeDiff > 120) {
            updateStatus('offline', `Last update: ${Math.round(timeDiff/60)} min ago`);
        } else {
            updateStatus('online', 'Live data');
            isOnline = true;
            consecutiveErrors = 0;
        }
        
        // Update current values
        document.getElementById('currentHR').textContent = `${Math.round(latestReading.heart_rate)} BPM`;
        document.getElementById('currentSpO2').textContent = `${Math.round(latestReading.spo2)}%`;
        document.getElementById('currentTemp').textContent = `${latestReading.temperature?.toFixed(1) || 'N/A'}°C`;
        
        // Update zone display
        updateZoneDisplay(latestReading.zone || 'normal', latestReading.heart_rate);
        
        // Update last update time
        document.getElementById('lastUpdate').textContent = `Last update: ${formatTime(latestReading.timestamp)}`;
        
        // Prepare chart data (last MAX_DATA_POINTS readings)
        const recentData = data.slice(-MAX_DATA_POINTS);
        const timestamps = recentData.map(reading => formatTime(reading.timestamp));
        const heartRates = recentData.map(reading => reading.heart_rate);
        const spo2Values = recentData.map(reading => reading.spo2);
        const temperatures = recentData.map(reading => reading.temperature || 36.5);

        // Update charts
        updateChart(hrChart, timestamps, heartRates);
        updateChart(spo2Chart, timestamps, spo2Values);
        updateChart(tempChart, timestamps, temperatures);
        
        // Update statistics
        updateStatistics(recentData);
        
        lastUpdateTime = Date.now();
        
    } catch (error) {
        console.error('❌ Error updating dashboard:', error);
        updateStatus('offline', 'Update error');
    }
}

// Update individual chart
function updateChart(chart, labels, data) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update('none'); // Disable animation for better performance
}

// Update statistics panel
function updateStatistics(data) {
    if (data.length === 0) return;
    
    const heartRates = data.map(d => d.heart_rate).filter(hr => hr > 0);
    const spo2Values = data.map(d => d.spo2).filter(spo2 => spo2 > 0);
    
    if (heartRates.length > 0) {
        const avgHR = heartRates.reduce((a, b) => a + b, 0) / heartRates.length;
        const minHR = Math.min(...heartRates);
        const maxHR = Math.max(...heartRates);
        
        document.getElementById('avgHR').textContent = `${Math.round(avgHR)} BPM`;
        document.getElementById('minHR').textContent = `${minHR} BPM`;
        document.getElementById('maxHR').textContent = `${maxHR} BPM`;
    }
    
    if (spo2Values.length > 0) {
        const avgSpO2 = spo2Values.reduce((a, b) => a + b, 0) / spo2Values.length;
        document.getElementById('avgSpO2').textContent = `${Math.round(avgSpO2)}%`;
    }
    
    // Update total readings count
    document.getElementById('totalReadings').textContent = data.length.toString();
}

// Fetch data from API with improved error handling
async function fetchData() {
    try {
        if (DEBUG) console.log('🔍 Fetching data from:', API_URL);
        
        updateStatus('connecting', 'Fetching data...');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await fetch(API_URL, {
            cache: 'no-store',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        if (DEBUG) console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        if (DEBUG) console.log('📊 Received data:', data.length, 'readings');
        
        if (data && Array.isArray(data) && data.length > 0) {
            updateDashboard(data);
            consecutiveErrors = 0;
            if (DEBUG) console.log('✅ Dashboard updated successfully');
        } else {
            console.warn('⚠️ No readings found in the data');
            updateStatus('offline', 'No readings available');
        }
        
    } catch (error) {
        consecutiveErrors++;
        console.error('❌ Error fetching data:', error);
        
        if (error.name === 'AbortError') {
            updateStatus('offline', 'Request timeout');
        } else if (consecutiveErrors < 3) {
            updateStatus('connecting', `Retrying... (${consecutiveErrors}/3)`);
        } else {
            updateStatus('offline', 'Connection failed');
            isOnline = false;
        }
    }
}

// Initialize dashboard
function initializeDashboard() {
    console.log('🚀 Initializing Heart Rate Monitor Dashboard');
    
    // Initialize charts
    initializeCharts();
    
    // Set initial status
    updateStatus('connecting', 'Initializing...');
    
    // Initial data fetch
    fetchData();
    
    // Set up periodic updates
    setInterval(fetchData, UPDATE_INTERVAL);
    
    // Add refresh button functionality
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            console.log('🔄 Manual refresh triggered');
            fetchData();
        });
    }
    
    // Add auto-refresh toggle
    const autoRefreshToggle = document.getElementById('autoRefresh');
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', (e) => {
            if (e.target.checked) {
                console.log('✅ Auto-refresh enabled');
                fetchData();
            } else {
                console.log('⏸️ Auto-refresh disabled');
            }
        });
    }
    
    console.log('✅ Dashboard initialized successfully');
}

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && isOnline) {
        // Page became visible, fetch fresh data
        fetchData();
    }
});

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDashboard);
} else {
    initializeDashboard();
}

// Error handling for chart.js
window.addEventListener('error', (e) => {
    if (e.message.includes('Chart')) {
        console.error('❌ Chart.js error:', e.message);
        updateStatus('offline', 'Chart error');
    }
});

// Export functions for debugging
if (DEBUG) {
    window.dashboardDebug = {
        fetchData,
        updateDashboard,
        charts: { hrChart, spo2Chart, tempChart },
        config: { API_URL, UPDATE_INTERVAL, MAX_DATA_POINTS }
    };
}
