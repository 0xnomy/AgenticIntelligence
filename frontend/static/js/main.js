// Global state
let currentJobId = null;
let statusCheckInterval = null;
let charts = {
    priceComparison: null,
    productCategory: null
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    initializeAnalysisForm();
    initializeCharts();
    initializeDownloadButton();
    initializeHistoryFilters();
    loadHistoryData();
});

// Handle analysis form submission
function initializeAnalysisForm() {
    const form = document.getElementById('analysisForm');
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const question = document.getElementById('question').value;

            try {
                const response = await fetch('/run_pipeline/', {
                    method: 'POST',
                    headers: addAuthHeader({
                        'Content-Type': 'application/json'
                    }),
                    body: JSON.stringify({ question })
                });

                const data = await response.json();
                if (response.ok) {
                    currentJobId = data.job_id;
                    showProgressSection();
                    startStatusChecking();
                }
            } catch (error) {
                console.error('Error starting analysis:', error);
                showError('Failed to start analysis. Please try again.');
            }
        });
    }
}

// Progress tracking
function showProgressSection() {
    const progressSection = document.getElementById('progressSection');
    progressSection.classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
}

function startStatusChecking() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    statusCheckInterval = setInterval(async () => {
        if (!currentJobId) return;

        try {
            const response = await fetch(`/status/${currentJobId}`, {
                headers: addAuthHeader()
            });
            const data = await response.json();

            updateProgress(data);

            if (data.status === 'complete') {
                clearInterval(statusCheckInterval);
                loadResults();
            } else if (data.status === 'failed') {
                clearInterval(statusCheckInterval);
                showError(data.error || 'Analysis failed');
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }, 2000);
}

function updateProgress(data) {
    const statusElement = document.getElementById('progressStatus');
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const agentMessages = document.getElementById('agentMessages');

    // Update status text and progress bar
    statusElement.textContent = data.progress_status || 'In Progress';
    const percentage = calculateProgress(data.progress_status);
    progressBar.style.width = `${percentage}%`;
    progressPercentage.textContent = `${percentage}%`;

    // Update agent messages
    if (data.agent_messages && data.agent_messages.length > 0) {
        agentMessages.innerHTML = data.agent_messages
            .map(msg => `<div class="p-2 bg-gray-50 rounded">
                <span class="font-medium">${msg.agent}:</span> ${msg.message}
            </div>`)
            .join('');
    }
}

function calculateProgress(status) {
    const stages = {
        'initializing': 0,
        'scraping': 25,
        'analyzing': 50,
        'qa_processing': 75,
        'generating_report': 90,
        'completed': 100
    };
    return stages[status] || 0;
}

// Results handling
async function loadResults() {
    try {
        const response = await fetch(`/download_report/${currentJobId}`, {
            headers: addAuthHeader()
        });
        const data = await response.text();

        // Show results section
        document.getElementById('resultsSection').classList.remove('hidden');

        // Update charts
        updateCharts(data);

        // Update comparison table
        updateComparisonTable(data);
    } catch (error) {
        console.error('Error loading results:', error);
        showError('Failed to load results');
    }
}

// Chart initialization and updates
function initializeCharts() {
    const priceCtx = document.getElementById('priceComparisonChart');
    const categoryCtx = document.getElementById('productCategoryChart');

    if (priceCtx) {
        charts.priceComparison = new Chart(priceCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Price Distribution',
                    data: [],
                    backgroundColor: 'rgba(99, 102, 241, 0.5)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    if (categoryCtx) {
        charts.productCategory = new Chart(categoryCtx, {
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgba(99, 102, 241, 0.5)',
                        'rgba(167, 139, 250, 0.5)',
                        'rgba(139, 92, 246, 0.5)',
                        'rgba(129, 140, 248, 0.5)'
                    ]
                }]
            },
            options: {
                responsive: true
            }
        });
    }
}

function updateCharts(data) {
    // Parse data and update charts
    // This is a placeholder - you'll need to parse the actual data format
    const parsedData = parseReportData(data);

    if (charts.priceComparison) {
        charts.priceComparison.data.labels = parsedData.priceLabels;
        charts.priceComparison.data.datasets[0].data = parsedData.priceData;
        charts.priceComparison.update();
    }

    if (charts.productCategory) {
        charts.productCategory.data.labels = parsedData.categoryLabels;
        charts.productCategory.data.datasets[0].data = parsedData.categoryData;
        charts.productCategory.update();
    }
}

function parseReportData(data) {
    // Placeholder function - implement actual parsing logic based on your data format
    return {
        priceLabels: ['0-50', '51-100', '101-150', '150+'],
        priceData: [10, 20, 15, 5],
        categoryLabels: ['Clothing', 'Accessories', 'Footwear', 'Other'],
        categoryData: [40, 20, 30, 10]
    };
}

// Comparison table updates
function updateComparisonTable(data) {
    const tbody = document.getElementById('comparisonTableBody');
    if (!tbody) return;

    // Clear existing rows
    tbody.innerHTML = '';

    // Add new rows - this is a placeholder, implement actual data parsing
    const products = parseProductData(data);
    products.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${product.name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${product.price}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${product.source}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${product.category}</td>
        `;
        tbody.appendChild(row);
    });
}

function parseProductData(data) {
    // Placeholder function - implement actual parsing logic
    return [
        { name: 'Product 1', price: '$99.99', source: 'Breakout', category: 'Clothing' },
        { name: 'Product 2', price: '$149.99', source: 'Rastah', category: 'Footwear' }
    ];
}

// Download functionality
function initializeDownloadButton() {
    const downloadBtn = document.getElementById('downloadReport');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async () => {
            if (!currentJobId) return;

            try {
                const response = await fetch(`/download_report/${currentJobId}`, {
                    headers: addAuthHeader()
                });
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `analysis_report_${currentJobId}.txt`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } catch (error) {
                console.error('Error downloading report:', error);
                showError('Failed to download report');
            }
        });
    }
}

// History page functionality
function initializeHistoryFilters() {
    const dateFilter = document.getElementById('dateFilter');
    const statusFilter = document.getElementById('statusFilter');

    if (dateFilter) {
        dateFilter.addEventListener('change', loadHistoryData);
    }
    if (statusFilter) {
        statusFilter.addEventListener('change', loadHistoryData);
    }
}

async function loadHistoryData() {
    const dateFilter = document.getElementById('dateFilter');
    const statusFilter = document.getElementById('statusFilter');

    if (!dateFilter || !statusFilter) return;

    try {
        const response = await fetch(`/history?date=${dateFilter.value}&status=${statusFilter.value}`, {
            headers: addAuthHeader()
        });
        const data = await response.json();
        updateHistoryTable(data);
    } catch (error) {
        console.error('Error loading history:', error);
        showError('Failed to load history');
    }
}

function updateHistoryTable(data) {
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) return;

    tbody.innerHTML = '';
    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatDate(item.date)}</td>
            <td class="px-6 py-4 text-sm text-gray-900">${item.question}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(item.status)}">
                    ${item.status}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <button onclick="viewReport('${item.id}')" class="text-indigo-600 hover:text-indigo-900">View</button>
                <button onclick="downloadReport('${item.id}')" class="ml-3 text-indigo-600 hover:text-indigo-900">Download</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function getStatusClass(status) {
    const classes = {
        'complete': 'bg-green-100 text-green-800',
        'failed': 'bg-red-100 text-red-800',
        'in_progress': 'bg-yellow-100 text-yellow-800'
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Error handling
function showError(message) {
    // Implement error display logic
    console.error(message);
} 