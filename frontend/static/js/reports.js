// Get DOM elements
const generateReportBtn = document.getElementById('generateReportBtn');
const downloadReportBtn = document.getElementById('downloadReportBtn');
const reportSection = document.getElementById('reportSection');
const reportContent = document.getElementById('reportContent');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');

// Generate report
async function generateReport() {
    try {
        errorSection.classList.add('hidden');
        reportSection.classList.add('hidden');
        downloadReportBtn.classList.add('hidden');
        reportContent.innerHTML = 'Generating report...';
        reportSection.classList.remove('hidden');
        const response = await fetch('/api/generate-report', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        reportContent.innerHTML = data.content.replace(/\n/g, '<br>');
        downloadReportBtn.classList.remove('hidden');
    } catch (error) {
        showError(error.message);
        reportSection.classList.add('hidden');
        downloadReportBtn.classList.add('hidden');
    }
}

// Download report
async function downloadReport() {
    try {
        const response = await fetch('/api/report-latest', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        // Create blob and download
        const blob = new Blob([data.content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'business_report.txt';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        showError(error.message);
    }
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
}

// Event listeners
generateReportBtn.addEventListener('click', generateReport);
downloadReportBtn.addEventListener('click', downloadReport);

// Optionally, load the latest report on page load
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/report-latest', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        const data = await response.json();
        if (data.content) {
            reportContent.innerHTML = data.content.replace(/\n/g, '<br>');
            reportSection.classList.remove('hidden');
            downloadReportBtn.classList.remove('hidden');
        }
    } catch (error) {
        // Ignore errors on initial load
    }
}); 