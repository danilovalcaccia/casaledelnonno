document.addEventListener('DOMContentLoaded', () => {
    // Ensure Firebase is initialized (firebase.app() should exist if SDKs are included)
    // const auth = firebase.auth(); // This will be available if firebase-auth-compat.js is included

    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const errorMessageElement = document.getElementById('errorMessage');

    // --- Utility to display errors ---
    function displayError(message) {
        if (errorMessageElement) {
            errorMessageElement.textContent = message;
            errorMessageElement.style.display = 'block';
            errorMessageElement.style.color = 'red'; // Make errors more visible
        } else {
            console.error("Error display element (errorMessage) not found. Message:", message);
        }
    }

    function clearError() {
        if (errorMessageElement) {
            errorMessageElement.textContent = '';
            errorMessageElement.style.display = 'none';
        }
    }

    // --- Login Handler ---
    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearError();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;

            if (!email || !password) {
                displayError('Email and password are required.');
                return;
            }

            try {
                // Check if firebase.auth() is available
                if (typeof firebase === 'undefined' || typeof firebase.auth === 'undefined') {
                    displayError('Firebase SDK not loaded. Please check your script includes.');
                    return;
                }
                const auth = firebase.auth();

                // 1. Sign in with Firebase client-side SDK
                const userCredential = await auth.signInWithEmailAndPassword(email, password);
                const user = userCredential.user;

                // 2. Get ID token
                const idToken = await user.getIdToken();

                // 3. Send ID token to backend to create a session
                const response = await fetch('/auth/sessionLogin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idToken: idToken })
                });

                const data = await response.json();

                if (response.ok) {
                    // Login successful, redirect to dashboard
                    window.location.href = 'dashboard.html';
                } else {
                    displayError(data.error || 'Login failed. Please try again.');
                    // Optional: Sign out from Firebase client if backend session failed
                    auth.signOut().catch(err => console.error("Error signing out from Firebase after failed backend session:", err));
                }
            } catch (error) {
                console.error('Login error:', error);
                if (error.code) { // Firebase auth error
                    switch (error.code) {
                        case 'auth/user-not-found':
                        case 'auth/wrong-password':
                        case 'auth/invalid-credential':
                            displayError('Invalid email or password.');
                            break;
                        default:
                            displayError('Login error: ' + error.message);
                    }
                } else { // Network or other errors
                    displayError('An unexpected error occurred during login. Check console for details.');
                }
            }
        });
    } else {
        console.warn("Login form (loginForm) not found.");
    }

    // --- Registration Handler ---
    if (registerForm) {
        registerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearError();
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const confirmPassword = document.getElementById('registerConfirmPassword').value;

            if (!email || !password || !confirmPassword) {
                displayError('All fields are required for registration.');
                return;
            }
            if (password !== confirmPassword) {
                displayError('Passwords do not match.');
                return;
            }
            if (password.length < 6) {
                displayError('Password must be at least 6 characters long.');
                return;
            }

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, password: password })
                });

                const data = await response.json();

                if (response.ok) {
                    alert('Registration successful! Please log in.');
                    registerForm.reset();
                    // Optionally, switch to login view if they are separate tabs/views
                    // Example: document.getElementById('showLoginFormLink').click();
                } else {
                    displayError(data.message || data.error || 'Registration failed. Please try again.');
                }
            } catch (error) {
                console.error('Registration error:', error);
                displayError('An unexpected error occurred during registration. Check console for details.');
            }
        });
    } else {
        console.warn("Registration form (registerForm) not found.");
    }

    // --- Check initial auth status ---
    // This helps redirect if the user is already logged in via a backend session
    fetch('/auth/status')
        .then(res => {
            if (!res.ok) {
                console.warn(`Auth status check failed with status: ${res.status}`);
                return null; // Don't proceed if the request itself failed
            }
            return res.json();
        })
        .then(data => {
            if (data && data.isLoggedIn) {
                // Only redirect if currently on login.html
                if (window.location.pathname.endsWith('login.html') || window.location.pathname.endsWith('/')) {
                     window.location.href = 'dashboard.html';
                }
            }
        })
        .catch(err => {
            // This error might occur if the backend is down or network issue
            console.error("Error checking auth status on login page:", err);
            // displayError("Could not verify login status. Backend might be unavailable."); // Optional: inform user
        });
});
