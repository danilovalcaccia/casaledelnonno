document.addEventListener('DOMContentLoaded', async () => {
    const dashboardTableBody = document.getElementById('dashboardTableBody');
    const logoutButton = document.getElementById('logoutButton');
    const errorMessageElement = document.getElementById('errorMessage');
    const loadingMessageElement = document.getElementById('loadingMessage');

    // --- Utility to display errors ---
    function displayError(message) {
        if (errorMessageElement) {
            errorMessageElement.textContent = message;
            errorMessageElement.style.display = 'block';
            errorMessageElement.style.color = 'red'; // Make errors more visible
        }
        if (loadingMessageElement) loadingMessageElement.style.display = 'none';
        if (dashboardTableBody) dashboardTableBody.innerHTML = ''; // Clear table
    }

    function clearError() {
        if (errorMessageElement) {
            errorMessageElement.textContent = '';
            errorMessageElement.style.display = 'none';
        }
    }

    function showLoading() {
        clearError();
        if (loadingMessageElement) loadingMessageElement.style.display = 'block';
        if (dashboardTableBody) dashboardTableBody.innerHTML = '';
    }

    function hideLoading() {
        if (loadingMessageElement) loadingMessageElement.style.display = 'none';
    }

    // --- Authentication Check ---
    try {
        const authResponse = await fetch('/auth/status');
        if (!authResponse.ok) { // Handles HTTP errors like 500, 404 etc.
             // Attempt to parse error from backend if available
            let errorMsg = `Authentication status check failed: ${authResponse.status}`;
            try {
                const errorData = await authResponse.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore if response is not json */ }
            displayError(errorMsg + ' Please try logging in again.');
            setTimeout(() => { window.location.href = 'login.html'; }, 3000);
            return;
        }

        const authData = await authResponse.json();
        if (!authData.isLoggedIn) {
            // Not logged in, redirect to login page
            window.location.href = 'login.html';
            return; // Stop further execution
        }
        // User is logged in, proceed to fetch dashboard data
    } catch (error) { // Catches network errors or if authResponse.json() fails
        console.error('Auth check failed:', error);
        displayError('Authentication check failed due to a network error or invalid response. Please try logging in again.');
        setTimeout(() => { window.location.href = 'login.html'; }, 3000);
        return;
    }

    // --- Fetch and Display Dashboard Data ---
    async function fetchDashboardData() {
        showLoading();
        try {
            const response = await fetch('/dashboard-data');
            if (!response.ok) {
                if (response.status === 401) { // Unauthorized
                    displayError('Your session has expired. Redirecting to login...');
                    setTimeout(() => { window.location.href = 'login.html'; }, 2000);
                    return;
                }
                // Try to parse error message from backend
                let errorMsg = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch(e) { /* Ignore if response is not json */ }
                throw new Error(errorMsg);
            }
            const data = await response.json();
            hideLoading();
            renderDashboard(data);
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            displayError(`Failed to load dashboard: ${error.message}`);
        }
    }

    function renderDashboard(products) {
        if (!dashboardTableBody) {
            console.error('Dashboard table body (dashboardTableBody) not found.');
            displayError('Could not display dashboard data: UI element missing.');
            return;
        }
        dashboardTableBody.innerHTML = ''; // Clear existing rows

        if (!Array.isArray(products)) {
            console.error('Dashboard data is not an array:', products);
            displayError('Received invalid data format from server.');
            return;
        }

        if (products.length === 0) {
            const row = dashboardTableBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 4; // Number of columns
            cell.textContent = 'No products found in inventory.';
            cell.style.textAlign = 'center';
            return;
        }

        products.forEach(product => {
            const row = dashboardTableBody.insertRow();
            // Check for product structure
            const productName = product && product.productName ? product.productName : 'N/A';
            const quantity = product && product.quantity !== undefined ? product.quantity : 'N/A';
            const nearestExpiry = product && product.nearestExpiry ? product.nearestExpiry : 'N/A';
            const lastUpdatedBy = product && product.lastUpdatedBy ? product.lastUpdatedBy : 'N/A';
            
            row.insertCell().textContent = productName;
            row.insertCell().textContent = quantity;
            row.insertCell().textContent = nearestExpiry;
            row.insertCell().textContent = lastUpdatedBy;
            
            // Add click event to row to navigate to product-detail.html
            if (productName !== 'N/A') { // Only make rows clickable if productName is valid
                row.style.cursor = 'pointer';
                row.addEventListener('click', () => {
                    window.location.href = `product-detail.html?productName=${encodeURIComponent(productName)}`;
                });
            }
        });
    }

    // --- Logout Handler ---
    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            clearError();
            try {
                const response = await fetch('/auth/logout', { method: 'POST' });
                const data = await response.json(); // Try to parse JSON regardless of response.ok
                
                if (response.ok) {
                    // Also sign out from Firebase client-side if it was used for login
                    if (typeof firebase !== 'undefined' && firebase.auth && typeof firebase.auth === 'function') {
                        // Check if firebase.auth().currentUser exists before calling signOut
                        if (firebase.auth().currentUser) {
                            await firebase.auth().signOut();
                        }
                    }
                    window.location.href = 'login.html';
                } else {
                    displayError(data.error || data.message || 'Logout failed.');
                }
            } catch (error) {
                console.error('Logout error:', error);
                displayError('An error occurred during logout. Check console for details.');
            }
        });
    } else {
        console.warn("Logout button (logoutButton) not found.");
    }

    // Initial data fetch
    if (document.getElementById('dashboardTableBody')) { // Only fetch if the main element is there
        fetchDashboardData();
    } else {
        console.error("Dashboard table body not found on initial load. Data fetch skipped.");
        displayError("Dashboard UI is not correctly set up.");
    }
});
