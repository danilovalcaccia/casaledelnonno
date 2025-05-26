# Agriturismo Inventory Management System

**Description:** A web application to manage inventory for an Agriturismo, built with Flask and Firebase. It allows tracking of product movements (loading/unloading), user authentication, and provides a dashboard overview of the inventory.

**Tech Stack:**
*   **Backend:** Python (Flask)
*   **Database:** Firebase Firestore
*   **Authentication:** Firebase Authentication
*   **Frontend:** HTML, JavaScript (interacting with Firebase client SDK and backend)

**Core Features:**
*   **User Authentication:** Registration, Login, Logout, Session Management.
*   **Inventory Movement Tracking:** Record product loading ("carico") and discharging ("scarico") with details like date, quantity, price, supplier, and expiry dates.
*   **Product Stock Management:** Automatically updates product quantities in Firestore based on movements.
*   **Dashboard Overview:** Displays a summary of all products, current quantities, nearest expiry dates, and last update information.
*   **Product Details View:** Shows detailed information for a specific product, including its movement history and calculated average unit price.
*   **Protected Routes:** Ensures only authenticated users can access inventory data and operations.

**Local Setup & Running:**

**Prerequisites:**
*   Python 3.7+
*   pip (Python package installer)
*   Firebase Project:
    *   A Firebase project created with Firestore and Authentication (Email/Password method) enabled.

**Steps:**

1.  **Clone the Repository:**
    ```bash
    # If this were a real git repo, you'd clone it.
    # For this environment, the files are already present in agriturismo_app.
    ```

2.  **Create and Activate a Virtual Environment:**
    (Recommended to keep project dependencies isolated)
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Navigate to the `agriturismo_app` directory (if not already there) and run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Firebase Configuration:**

    *   **Admin SDK (Backend):**
        *   Download your Firebase project's service account key JSON file.
        *   Rename it to `serviceAccountKey.json`.
        *   Place this file in the `agriturismo_app` root directory (alongside `app.py`).
        *   **Important Security Note:** The `serviceAccountKey.json` file provides full admin access to your Firebase project. It is included in `.gitignore` to prevent accidental public commits. **Never commit this file to a public repository.**

    *   **Client-Side SDK (Frontend):**
        *   You will need your Firebase project's client-side configuration (apiKey, authDomain, projectId, etc.).
        *   This configuration needs to be included in your HTML files where the Firebase JavaScript SDKs are initialized (e.g., `login.html`, `dashboard.html`, etc., within a `<script>` tag).
        *   Example structure for Firebase client config in HTML:
            ```html
            <script>
              const firebaseConfig = {
                apiKey: "YOUR_API_KEY",
                authDomain: "YOUR_AUTH_DOMAIN",
                projectId: "YOUR_PROJECT_ID",
                storageBucket: "YOUR_STORAGE_BUCKET",
                messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
                appId: "YOUR_APP_ID"
              };
              firebase.initializeApp(firebaseConfig);
            </script>
            ```

5.  **Run the Application:**
    From the `agriturismo_app` directory:
    ```bash
    flask run
    ```
    Or, if `app.py` includes `if __name__ == '__main__': app.run(debug=True)`, you can run:
    ```bash
    python app.py
    ```
    The application will typically be available at `http://127.0.0.1:5000/`.

**API Endpoints Summary:**

*   `POST /auth/register`: User registration.
*   `POST /auth/sessionLogin`: User login, creates a server-side session.
*   `POST /auth/logout`: User logout, clears the server-side session.
*   `GET /auth/status`: Checks current user authentication status.
*   `POST /movements`: Records a new inventory movement (protected).
*   `GET /dashboard-data`: Fetches data for the inventory dashboard (protected).
*   `GET /products/<product_name>`: Fetches detailed information for a specific product (protected).
*   `GET /`: Root path, simple "Flask App is Running!" message.

**Project Structure Overview:**

*   `agriturismo_app/`
    *   `app.py`: Main Flask application file containing backend logic, routes, and API endpoints.
    *   `serviceAccountKey.json`: Firebase Admin SDK credentials (private, should not be committed if public).
    *   `requirements.txt`: Lists Python dependencies for the project.
    *   `.firebaserc`: (If using Firebase CLI for hosting) Firebase project configuration.
    *   `.gitignore`: Specifies intentionally untracked files that Git should ignore (e.g., `serviceAccountKey.json`, `__pycache__/`, `venv/`).
    *   `static/`: (User must create this directory for frontend assets)
        *   `js/`: Contains JavaScript files for frontend logic (e.g., `login.js`, `dashboard.js`, `nuovo-movimento.js`, `product-detail.js`).
        *   `css/`: (Optional) For CSS stylesheets.
    *   `templates/`: (User must create this directory for Flask to serve HTML files)
        *   Contains HTML template files (e.g., `login.html`, `dashboard.html`, `nuovo-movimento.html`, `product-detail.html`).
    *   `venv/`: (If created) Python virtual environment directory.

This `README.md` provides a good starting point for understanding, setting up, and running the project.
Remember to replace placeholder values (like `YOUR_API_KEY`) with actual Firebase project configurations.
The HTML files mentioned (e.g., `login.html`) are assumed to be created by the user and placed in the `templates` directory, and their corresponding JavaScript in the `static/js` directory.
The Firebase client SDKs (like `firebase-app.js`, `firebase-auth.js`, `firebase-firestore.js`) also need to be included in these HTML files, typically via CDN links or by installing them as project dependencies.I have added comments to `agriturismo_app/app.py` and created the `agriturismo_app/README.md` file with the specified content in the previous turns.

Both tasks are now complete:
1.  **Code Comments in `agriturismo_app/app.py`**: The file was reviewed, and comments were added to explain routes, complex logic, helper functions, and configurations.
2.  **`README.md` Creation**: The file `agriturismo_app/README.md` was created and populated with all the requested sections, including Project Title, Description, Tech Stack, Core Features, Local Setup & Running instructions, API Endpoints Summary, and Project Structure Overview. The README is formatted using Markdown.

The comments in `app.py` are designed to improve readability and make the codebase easier to understand. The `README.md` provides essential information for anyone looking to set up, run, or understand the project.
