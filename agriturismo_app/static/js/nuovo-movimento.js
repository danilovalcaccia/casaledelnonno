document.addEventListener('DOMContentLoaded', async () => {
    const movementForm = document.getElementById('movementForm');
    const formMessageElement = document.getElementById('formMessage');
    const logoutButton = document.getElementById('logoutButton'); // Optional

    // --- Utility to display messages ---
    function displayMessage(message, isError = false) {
        if (formMessageElement) {
            formMessageElement.textContent = message;
            formMessageElement.style.color = isError ? 'red' : 'green';
            formMessageElement.style.display = 'block';
        } else {
            console.error("Form message element (formMessage) not found. Message:", message);
        }
    }

    function clearMessage() {
        if (formMessageElement) {
            formMessageElement.textContent = '';
            formMessageElement.style.display = 'none';
        }
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

    // --- Movement Form Submission Handler ---
    if (movementForm) {
        movementForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearMessage();

            const formData = new FormData(movementForm);
            const movementData = {
                date: formData.get('movementDate'),
                supplier: formData.get('supplier'),
                movementType: formData.get('movementType'), // Radio button value
                productName: formData.get('productName')?.trim(),
                quantity: parseFloat(formData.get('quantity')),
                unitPrice: parseFloat(formData.get('unitPrice')), // Keep as NaN if empty or invalid for now
                expiryDate: formData.get('expiryDate') || null, // Send null if empty
                notes: formData.get('notes')?.trim()
            };

            // Basic client-side validation (more robust validation is on the server)
            if (!movementData.date || !movementData.movementType || !movementData.productName || !movementData.productName.trim() || isNaN(movementData.quantity) || movementData.quantity <= 0) {
                displayMessage('Please fill in all required fields: Date, Movement Type, Product Name (non-empty), and a valid positive Quantity.', true);
                return;
            }
            
            // Handle unitPrice: if it's not a valid positive number, set to null to let backend decide/validate
            // Server expects positive for 'carico' if provided.
            if (isNaN(movementData.unitPrice) || movementData.unitPrice < 0) {
                movementData.unitPrice = null; 
            }
            if (!movementData.expiryDate) { // Ensure empty string becomes null
                delete movementData.expiryDate;
            }


            try {
                const response = await fetch('/movements', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(movementData)
                });

                const responseData = await response.json();

                if (response.ok) {
                    displayMessage('Movement registered successfully! ID: ' + responseData.movementId, false);
                    movementForm.reset(); // Clear the form
                    // Optionally, redirect to dashboard or product detail page
                    // setTimeout(() => { window.location.href = 'dashboard.html'; }, 2000);
                } else {
                    if (response.status === 401) { // Unauthorized
                         displayMessage('Your session has expired. Redirecting to login...', true);
                         setTimeout(() => { window.location.href = 'login.html'; }, 2000);
                         return;
                    }
                    displayMessage(`Error: ${responseData.error || responseData.message || 'Failed to register movement.'}`, true);
                }
            } catch (error) {
                console.error('Error submitting movement:', error);
                displayMessage('An unexpected error occurred while registering the movement. Check console for details.', true);
            }
        });
    } else {
        console.warn("Movement form (movementForm) not found.");
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
});
