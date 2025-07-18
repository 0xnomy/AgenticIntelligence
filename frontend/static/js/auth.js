// Auth state management
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// Define public routes that don't require authentication
const publicRoutes = ['/login', '/register'];

// Check if current route is public
function isPublicRoute() {
    return publicRoutes.some(route => window.location.pathname.startsWith(route));
}

// Check if user is authenticated
async function checkAuth() {
    // Skip auth check for public routes
    if (isPublicRoute()) {
        return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    try {
        const response = await fetch('/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Authentication failed');
        }

        const data = await response.json();
        updateUsername(data.username);
    } catch (error) {
        console.error('Auth error:', error);
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
}

// Update username in UI
function updateUsername(username) {
    const usernameElement = document.getElementById('username');
    if (usernameElement) {
        usernameElement.textContent = username;
    }
}

// Handle login
async function login(event) {
    event.preventDefault();
    const errorElement = document.getElementById('error');
    errorElement.classList.add('hidden');

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        localStorage.setItem('token', data.access_token);
        window.location.href = '/';
    } catch (error) {
        errorElement.textContent = error.message;
        errorElement.classList.remove('hidden');
    }
}

// Handle registration
async function register(event) {
    event.preventDefault();
    const errorElement = document.getElementById('error');
    errorElement.classList.add('hidden');

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        const data = await response.json();

        if (!response.ok) {
            if (data.errors) {
                throw new Error(data.errors.join('\n'));
            }
            throw new Error(data.detail || 'Registration failed');
        }

        // Redirect to login page on successful registration
        window.location.href = '/login';
    } catch (error) {
        errorElement.textContent = error.message;
        errorElement.classList.remove('hidden');
    }
}

// Handle logout
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

// Update user info in navbar
async function updateUserInfo() {
    const userInfo = document.getElementById('userInfo');
    if (userInfo && authToken) {
        try {
            const response = await fetch('/api/me', {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                currentUser = data;
                userInfo.textContent = `Welcome, ${data.username}`;
            }
        } catch (error) {
            console.error('Error fetching user info:', error);
        }
    }
}

// Add auth token to all API requests
function addAuthHeader(headers = {}) {
    if (authToken) {
        return {
            ...headers,
            'Authorization': `Bearer ${authToken}`
        };
    }
    return headers;
}

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function () {
    checkAuth();
    updateUserInfo();
}); 