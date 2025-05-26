document.addEventListener('DOMContentLoaded', async () => {
    const productNameDisplay = document.getElementById('productNameDisplay');
    const totalQuantityInStockDisplay = document.getElementById('totalQuantityInStock');
    const averageUnitPriceDisplay = document.getElementById('averageUnitPrice');
    const expirationDateHistoryDisplay = document.getElementById('expirationDateHistory');
    const movementsTableBody = document.getElementById('movementsTableBody');
    const logoutButton = document.getElementById('logoutButton'); // Optional
    const messageElement = document.getElementById('messageElement');
    const loadingMessageElement = document.getElementById('loadingMessage');

    // --- Utility functions ---
    function displayMessage(message, isError = false) {
        if (messageElement) {
            messageElement.textContent = message;
            messageElement.style.color = isError ? 'red' : 'green';
            messageElement.style.display = 'block';
        }
        if (loadingMessageElement) loadingMessageElement.style.display = 'none';
    }

    function clearMessage() {
        if (messageElement) {
            messageElement.textContent = '';
            messageElement.style.display = 'none';
        }
    }

    function showLoading() {
        clearMessage();
        if (loadingMessageElement) loadingMessageElement.style.display = 'block';
        if (movementsTableBody) movementsTableBody.innerHTML = '';
        // Clear other displays too
        if (productNameDisplay) productNameDisplay.textContent = '';
        if (totalQuantityInStockDisplay) totalQuantityInStockDisplay.textContent = '--';
        if (averageUnitPriceDisplay) averageUnitPriceDisplay.textContent = '--';
        if (expirationDateHistoryDisplay) expirationDateHistoryDisplay.textContent = '--';
    }

    function hideLoading() {
        if (loadingMessageElement) loadingMessageElement.style.display = 'none';
    }

    // --- Authentication Check ---
    try {
        const authResponse = await fetch('/auth/status');
        if (!authResponse.ok) { // Handles HTTP errors like 500, 404 etc.
            let errorMsg = `Authentication status check failed: ${authResponse.status}`;
             try {
                const errorData = await authResponse.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore if response is not json */ }
            displayMessage(errorMsg + '. Redirecting to login.', true);
            setTimeout(() => { window.location.href = 'login.html'; }, 3000);
            return;
        }
        const authData = await authResponse.json();
        if (!authData.isLoggedIn) {
            window.location.href = 'login.html';
            return; // Stop further execution
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        displayMessage('Authentication check failed due to network error. Redirecting to login.', true);
        setTimeout(() => { window.location.href = 'login.html'; }, 3000);
        return;
    }

    // --- Get Product Name from URL ---
    const urlParams = new URLSearchParams(window.location.search);
    const productName = urlParams.get('productName');

    if (!productName) {
        displayMessage('No product name specified in URL.', true);
        // Potentially hide main content display areas if productName is missing
        if (productNameDisplay) productNameDisplay.textContent = 'Error: Product not specified';
        return;
    }
    if (productNameDisplay) productNameDisplay.textContent = productName;


    // --- Fetch and Display Product Details ---
    async function fetchProductDetails() {
        if (!productName) return; // Already handled, but good for safety
        showLoading();
        try {
            const response = await fetch(`/products/${encodeURIComponent(productName)}`);
            if (!response.ok) {
                if (response.status === 401) { // Unauthorized
                    displayMessage('Your session has expired. Redirecting to login...', true);
                    setTimeout(() => { window.location.href = 'login.html'; }, 2000);
                    return;
                }
                if (response.status === 404) {
                     displayMessage(`Product "${productName}" not found. Check if the name is correct or if it has been removed.`, true);
                     if (productNameDisplay) productNameDisplay.textContent = `Product: ${productName} (Not Found)`;
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
            renderProductDetails(data);
        } catch (error) {
            console.error(`Error fetching details for ${productName}:`, error);
            displayMessage(`Failed to load details for ${productName}: ${error.message}`, true);
            if (productNameDisplay) productNameDisplay.textContent = `Product: ${productName} (Error)`;
        }
    }

    function renderProductDetails(data) {
        if (totalQuantityInStockDisplay) totalQuantityInStockDisplay.textContent = data.totalQuantityInStock !== undefined ? String(data.totalQuantityInStock) : 'N/A';
        if (averageUnitPriceDisplay) averageUnitPriceDisplay.textContent = data.averageUnitPrice !== undefined ? data.averageUnitPrice.toFixed(2) : 'N/A';
        if (expirationDateHistoryDisplay) expirationDateHistoryDisplay.textContent = data.expirationDateHistory && data.expirationDateHistory.length > 0 ? data.expirationDateHistory.join(', ') : 'None';

        if (!movementsTableBody) {
            console.error('Movements table body (movementsTableBody) not found.');
            displayMessage('UI Error: Could not display movements table.', true);
            return;
        }
        movementsTableBody.innerHTML = ''; // Clear existing rows

        if (!data.movements || data.movements.length === 0) {
            const row = movementsTableBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 9; // Number of columns in movements table
            cell.textContent = 'No movements found for this product.';
            cell.style.textAlign = 'center';
            return;
        }

        data.movements.forEach(mov => {
            const row = movementsTableBody.insertRow();
            // Ensure mov.date is treated as a string YYYY-MM-DD or full ISO if from server (like createdAt)
            // If mov.date is just YYYY-MM-DD from movement record, it might not need complex parsing,
            // but if it's a full timestamp string, new Date().toLocaleDateString() is fine.
            // Assuming 'date' field from movement record is already YYYY-MM-DD string.
            row.insertCell().textContent = mov.date || 'N/A'; 
            row.insertCell().textContent = mov.movementType || 'N/A';
            row.insertCell().textContent = mov.quantity !== undefined ? String(mov.quantity) : 'N/A';
            row.insertCell().textContent = mov.unitPrice !== undefined && mov.unitPrice !== null ? mov.unitPrice.toFixed(2) : 'N/A';
            row.insertCell().textContent = mov.totalValue !== undefined && mov.totalValue !== null ? mov.totalValue.toFixed(2) : 'N/A';
            row.insertCell().textContent = mov.supplier || 'N/A';
            row.insertCell().textContent = mov.expiryDate || 'N/A';
            row.insertCell().textContent = mov.notes || 'N/A';
            row.insertCell().textContent = mov.userId ? mov.userId.substring(0, 8) + '...' : 'N/A'; // Shorten UserID
        });
    }

    // --- Logout Handler (if a logout button is specific to this page) ---
    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            clearMessage();
            try {
                const logoutResponse = await fetch('/auth/logout', { method: 'POST' });
                // Try to sign out from Firebase client-side as well
                if (typeof firebase !== 'undefined' && firebase.auth && typeof firebase.auth === 'function') {
                     if (firebase.auth().currentUser) {
                        await firebase.auth().signOut();
                    }
                }
                // Check response status from backend logout
                if (logoutResponse.ok) {
                    window.location.href = 'login.html';
                } else {
                    const errorData = await logoutResponse.json().catch(() => ({})); // catch if not json
                    displayMessage(errorData.error || errorData.message || 'Logout failed on server.', true);
                }
            } catch (err) {
                console.error('Logout error:', err);
                displayMessage('Logout failed due to a network error or client-side issue.', true);
            }
        });
    } else {
         console.warn("Logout button (logoutButton) for this page not found. Assuming global navigation handles logout.");
    }

    // Initial data fetch
    if (productName && document.getElementById('movementsTableBody')) { // Ensure product name is present and table exists
        fetchProductDetails();
    } else if (!productName) {
        // Error already displayed if productName is missing.
        // No need to call fetchProductDetails.
    } else {
        // productName is present, but table body is not.
        console.error("Movements table body not found on initial load. Data fetch skipped for product:", productName);
        displayMessage("Product Detail UI is not correctly set up.", true);
    }
});
