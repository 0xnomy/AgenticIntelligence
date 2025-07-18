// Check authentication on page load
checkAuth();

// Get DOM elements
const startAnalysisBtn = document.getElementById('startAnalysis');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const statusMessage = document.getElementById('statusMessage');
const resultsSection = document.getElementById('resultsSection');
const analysisResults = document.getElementById('analysisResults');
const downloadReportBtn = document.getElementById('downloadReport');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');

let currentJobId = null;

// Start analysis
startAnalysisBtn.addEventListener('click', async () => {
    try {
        startAnalysisBtn.disabled = true;
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        errorSection.classList.add('hidden');
        progressBar.style.width = '0%';
        statusMessage.textContent = 'Starting market analysis...';

        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            let errorMsg = '';
            if (typeof data.detail === 'string') {
                errorMsg = data.detail;
            } else if (data.detail && typeof data.detail.message === 'string') {
                errorMsg = data.detail.message;
            } else {
                errorMsg = 'Failed to start analysis';
            }
            if (response.status === 401) {
                errorMsg = 'Your session has expired. Please log in again.';
            } else if (response.status === 400) {
                errorMsg = errorMsg || 'Invalid request. Please check the data and try again.';
            } else if (response.status === 500) {
                errorMsg = errorMsg || 'An internal server error occurred. Please try again later.';
            }
            throw new Error(errorMsg);
        }

        currentJobId = data.job_id;

        if (data.status === 'completed') {
            await loadResults();
        } else {
            checkStatus();
        }
    } catch (error) {
        showError(error.message);
        startAnalysisBtn.disabled = false;
    }
});

// Check job status
async function checkStatus() {
    try {
        const response = await fetch(`/status/${currentJobId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Analysis job not found. Please try starting a new analysis.');
            }
            throw new Error('Failed to get analysis status');
        }

        const data = await response.json();
        updateProgress(data);

        if (data.status === 'completed') {
            await loadResults();
        } else if (data.status === 'failed') {
            let errorMsg = data.error || 'Analysis failed';
            if (errorMsg.includes('No product data found')) {
                errorMsg += '. Please run the scraper first to collect product data.';
            }
            showError(errorMsg);
            startAnalysisBtn.disabled = false;
        } else {
            setTimeout(checkStatus, 1000);
        }
    } catch (error) {
        showError(error.message);
        startAnalysisBtn.disabled = false;
    }
}

// Load analysis results
async function loadResults() {
    try {
        const response = await fetch(`/api/report/${currentJobId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Analysis report not found. The file might have been moved or deleted.');
            }
            throw new Error('Failed to load analysis results');
        }

        const data = await response.json();
        analysisResults.textContent = data.content;
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        startAnalysisBtn.disabled = false;
    } catch (error) {
        showError(error.message);
        startAnalysisBtn.disabled = false;
    }
}

// Update progress UI
function updateProgress(data) {
    const progress = data.progress || 0;
    progressBar.style.width = `${progress}%`;
    statusMessage.textContent = data.message || 'Processing analysis...';

    // Add specific status messages based on progress
    if (progress < 25) {
        statusMessage.textContent = 'Preparing data for analysis...';
    } else if (progress < 50) {
        statusMessage.textContent = 'Analyzing product information...';
    } else if (progress < 75) {
        statusMessage.textContent = 'Identifying market trends...';
    } else if (progress < 100) {
        statusMessage.textContent = 'Generating analysis report...';
    }
}

// Show error message with formatting
function showError(message) {
    // Format common error messages
    if (message.includes('GROQ_API_KEY')) {
        message = 'API configuration error. Please contact support.';
    } else if (message.includes('No product data found')) {
        message = 'No product data available. Please run the scraper first to collect data from the e-commerce sites.';
    } else if (message.includes('Failed to get status')) {
        message = 'Lost connection to the server. Please check your internet connection and try again.';
    }

    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
}

// Download report
downloadReportBtn.addEventListener('click', async () => {
    try {
        const response = await fetch(`/api/report/${currentJobId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Report file not found. The analysis might need to be run again.');
            } else if (response.status === 401) {
                throw new Error('Your session has expired. Please log in again to download the report.');
            }
            throw new Error('Failed to download report');
        }

        const data = await response.json();

        // Create blob and download
        const blob = new Blob([data.content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'market_analysis_report.txt';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        showError(error.message);
    }
}); 