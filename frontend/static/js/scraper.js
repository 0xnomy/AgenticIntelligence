// Check authentication on page load
checkAuth();

// Get DOM elements
const startScraperBtn = document.getElementById('startScraper');
const stopScraperBtn = document.getElementById('stopScraper');
const totalProductsInput = document.getElementById('totalProducts');
const headlessModeSelect = document.getElementById('headlessMode');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressPercentage = document.getElementById('progressPercentage');
const breakoutProgress = document.getElementById('breakoutProgress');
const rastahProgress = document.getElementById('rastahProgress');
const breakoutStatus = document.getElementById('breakoutStatus');
const rastahStatus = document.getElementById('rastahStatus');
const statusMessages = document.getElementById('statusMessages');
const resultsSection = document.getElementById('resultsSection');
const scrapedDataTable = document.getElementById('scrapedDataTable');
const downloadDataBtn = document.getElementById('downloadData');
const totalScraped = document.getElementById('totalScraped');
const breakoutCount = document.getElementById('breakoutCount');
const rastahCount = document.getElementById('rastahCount');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');

let currentJobId = null;
let isRunning = false;

// Add event listeners
startScraperBtn.addEventListener('click', startScraping);
stopScraperBtn.addEventListener('click', stopScraping);
downloadDataBtn.addEventListener('click', downloadData);

// Start scraping
async function startScraping() {
    try {
        // Validate input
        const totalProducts = parseInt(totalProductsInput.value);
        if (totalProducts < 2 || totalProducts > 200) {
            throw new Error('Total products must be between 2 and 200');
        }

        // Reset UI
        resetUI();
        isRunning = true;
        startScraperBtn.disabled = true;
        stopScraperBtn.disabled = false;
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        errorSection.classList.add('hidden');

        // Start scraping (new endpoint)
        const response = await fetch('/start-scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ max_products: totalProducts })
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || 'Failed to start scraping');
        }

        // Download the CSV file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'all_products.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        addStatusMessage('Scraping completed and CSV downloaded.');
        resetControls();
    } catch (error) {
        showError(error.message);
        resetControls();
    }
}

// Stop scraping
async function stopScraping() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/scraper/stop/${currentJobId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to stop scraping');
        }

        addStatusMessage('Scraping stopped by user');
        isRunning = false;
        resetControls();
    } catch (error) {
        showError(error.message);
    }
}

// Check scraping status
async function checkStatus() {
    if (!currentJobId || !isRunning) return;

    try {
        const response = await fetch(`/api/scraper/status/${currentJobId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to get status');
        }

        const data = await response.json();
        updateProgress(data);

        if (data.status === 'completed') {
            showResults(data);
            resetControls();
        } else if (data.status === 'failed') {
            showError(data.error || 'Scraping failed');
            resetControls();
        } else {
            // Check again in 1 second
            setTimeout(checkStatus, 1000);
        }
    } catch (error) {
        showError(error.message);
        resetControls();
    }
}

// Update progress UI
function updateProgress(data) {
    // Update overall progress
    const progress = data.progress || 0;
    progressBar.style.width = `${progress}%`;
    progressPercentage.textContent = `${progress}%`;

    // Update source progress
    if (data.breakout_progress) {
        breakoutProgress.style.width = `${data.breakout_progress}%`;
        breakoutStatus.textContent = `${data.breakout_progress}% complete`;
    }
    if (data.rastah_progress) {
        rastahProgress.style.width = `${data.rastah_progress}%`;
        rastahStatus.textContent = `${data.rastah_progress}% complete`;
    }

    // Add status message if provided
    if (data.message) {
        addStatusMessage(data.message);
    }
}

// Show scraping results
function showResults(data) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    // Update counts
    totalScraped.textContent = data.total_scraped || 0;
    breakoutCount.textContent = data.breakout_count || 0;
    rastahCount.textContent = data.rastah_count || 0;

    // Clear existing table rows
    scrapedDataTable.innerHTML = '';

    // Add new rows
    if (data.data && Array.isArray(data.data)) {
        data.data.forEach(product => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product[0]}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product[1]}</td>
                <td class="px-6 py-4 text-sm text-gray-900">${product[2]}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product[3]}</td>
            `;
            scrapedDataTable.appendChild(row);
        });
    }

    addStatusMessage('Scraping completed successfully');
}

// Download scraped data
async function downloadData() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/scraper/download/${currentJobId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to download data');
        }

        // Create and click a temporary download link
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `scraped_data_${currentJobId}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (error) {
        showError(error.message);
    }
}

// Add status message
function addStatusMessage(message) {
    const timestamp = new Date().toLocaleTimeString();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'text-gray-600';
    messageDiv.innerHTML = `<span class="font-medium">${timestamp}</span>: ${message}`;
    statusMessages.insertBefore(messageDiv, statusMessages.firstChild);
}

// Show error message
function showError(message) {
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
    addStatusMessage(`Error: ${message}`);
}

// Reset UI controls
function resetControls() {
    isRunning = false;
    startScraperBtn.disabled = false;
    stopScraperBtn.disabled = true;
}

// Reset entire UI
function resetUI() {
    // Reset progress
    progressBar.style.width = '0%';
    progressPercentage.textContent = '0%';
    breakoutProgress.style.width = '0%';
    rastahProgress.style.width = '0%';
    breakoutStatus.textContent = 'Waiting to start...';
    rastahStatus.textContent = 'Waiting to start...';

    // Clear status messages
    statusMessages.innerHTML = '';

    // Reset counts
    totalScraped.textContent = '0';
    breakoutCount.textContent = '0';
    rastahCount.textContent = '0';

    // Clear table
    scrapedDataTable.innerHTML = '';

    // Hide error
    errorSection.classList.add('hidden');
} 