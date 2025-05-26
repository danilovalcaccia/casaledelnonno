# --- Core Flask and Firebase Imports ---
from flask import Flask, request, jsonify, session, current_app
from firebase_admin import credentials, initialize_app, auth, firestore
from functools import wraps # For creating decorators
from datetime import datetime # For date handling
import re # For regular expression matching (e.g., email validation)
from werkzeug.exceptions import HTTPException # For handling HTTP errors globally

# --- Flask App Initialization ---
app = Flask(__name__)
# Secret key for session management. Replace with a strong, random key in production.
app.secret_key = 'your_very_secret_key_here' 

# --- Firebase Admin SDK Initialization ---
# Loads Firebase service account credentials from the specified JSON file.
# This file must be present in the same directory as app.py or path adjusted.
cred = credentials.Certificate("serviceAccountKey.json")
# Initializes the Firebase Admin SDK, allowing interaction with Firebase services.
initialize_app(cred)
# Creates a Firestore client instance for database operations.
db = firestore.client() 

# --- Utility Decorator: Login Required ---
def login_required(f):
    """
    Decorator to ensure a user is logged in (i.e., 'user_id' is in session)
    before accessing a route. If not logged in, returns a 401 Unauthorized error.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401 # Unauthorized
        return f(*args, **kwargs)
    return decorated_function

# --- Basic Routes ---
@app.route('/') # Defines the root URL endpoint
def hello_world():
    """A simple root route to confirm the Flask app is running."""
    return 'Flask App is Running!'

# --- Authentication Routes ---
@app.route('/auth/register', methods=['POST']) # Endpoint for user registration
def register():
    """
    Handles new user registration.
    Expects JSON payload with 'email' and 'password'.
    Validates input, creates a Firebase user, and optionally stores user info in Firestore.
    """
    data = request.get_json()
    # Validate JSON payload
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400 # Bad Request

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400
    
    # Basic email format validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email format."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    try:
        user = auth.create_user(email=email, password=password)
        # Optional: Store user info in Firestore
        user_info = {'email': user.email, 'createdAt': firestore.SERVER_TIMESTAMP}
        db.collection('users').document(user.uid).set(user_info)
        return jsonify({"message": "User registered successfully.", "uid": user.uid}), 201
    except auth.EmailAlreadyExistsError:
        return jsonify({"error": "This email address is already registered."}), 409
    except auth.FirebaseAuthException as e:
        # Log specific Firebase authentication errors
        current_app.logger.error(f"Firebase auth error during registration: {e}")
        return jsonify({"error": "An error occurred during registration with authentication service."}), 500 # Internal Server Error
    except Exception as e:
        # Log any other unexpected errors
        current_app.logger.error(f"Unhandled exception during registration: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500 # Internal Server Error

@app.route('/auth/sessionLogin', methods=['POST']) # Endpoint for user login and session creation
def session_login():
    """
    Handles user login by verifying a Firebase ID token (obtained from client-side Firebase auth).
    If valid, creates a server-side session for the user.
    Expects JSON payload with 'idToken'.
    """
    data = request.get_json()
    # Validate JSON payload
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400 # Bad Request

    id_token = data.get('idToken')
    # Validate ID token presence and type
    if not id_token or not isinstance(id_token, str):
        return jsonify({"error": "ID token is required and must be a string."}), 400 # Bad Request

    try:
        # Verify the ID token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        # Store user ID in session to maintain login state
        session['user_id'] = uid
        # Optional: Could add session expiration configuration here if needed (e.g., session.permanent = True)
        return jsonify({"message": "Session login successful."}), 200 # OK
    except auth.InvalidIdTokenError:
        # Token is invalid or expired
        return jsonify({"error": "Invalid or expired ID token."}), 401 # Unauthorized
    except auth.UserDisabledError:
        # User's Firebase account is disabled
        return jsonify({"error": "This user account has been disabled."}), 403 # Forbidden
    except auth.FirebaseAuthException as e:
        # Other Firebase authentication errors
        current_app.logger.error(f"Firebase auth error during session login: {e}")
        return jsonify({"error": "Authentication failed due to a Firebase error."}), 500 # Internal Server Error
    except Exception as e:
        # Log any other unexpected errors
        current_app.logger.error(f"Unhandled exception during session login: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500 # Internal Server Error

@app.route('/auth/logout', methods=['POST']) # Endpoint for user logout
def logout():
    """
    Handles user logout by clearing the server-side session.
    """
    session.pop('user_id', None) # Remove user_id from session, effectively logging out
    return jsonify({"message": "Logged out successfully"}), 200 # OK

@app.route('/auth/status', methods=['GET']) # Endpoint to check current authentication status
def auth_status():
    """
    Checks if a user is currently logged in (based on server-side session).
    Returns login status and user ID if logged in.
    """
    if 'user_id' in session:
        return jsonify({"isLoggedIn": True, "user_id": session['user_id']}), 200 # OK
    else:
        return jsonify({"isLoggedIn": False}), 200

# Example of a protected route (optional, for testing the decorator)
@app.route('/protected_example')
@login_required
def protected_example():
    return jsonify({"message": "This is a protected area", "user_id": session['user_id']})

# --- Transactional function for product stock update ---
# --- Transactional Function for Product Stock Update ---
@firestore.transactional # Decorator to make this function a Firestore transaction
def update_product_stock_transactional(transaction, product_ref, movement_data, user_id):
    """
    Atomically updates product stock and related metadata within a Firestore transaction.
    This ensures that reads and writes are consistent.

    Args:
        transaction: The Firestore transaction object.
        product_ref: Firestore document reference for the product.
        movement_data: Dictionary containing details of the movement.
        user_id: ID of the user performing the movement.

    Raises:
        ValueError: If movement type is invalid, product not found for "scarico",
                    or insufficient stock for "scarico".
    """
    product_snapshot = transaction.get(product_ref) # Get current product data within transaction
    product_data = product_snapshot.to_dict() if product_snapshot.exists else {}
    
    movement_type = movement_data['movementType']
    quantity = movement_data['quantity']
    product_name = movement_data['productName'] # productName from movement, used to ensure consistency

    if movement_type == "carico": # Product loading
        new_quantity = product_data.get('quantity', 0) + quantity
        update_payload = {
            'quantity': new_quantity,
            'lastUpdatedBy': user_id,
            'productName': product_name # Store/update productName for consistency
        }
        # If product is new, set its creation timestamp
        if not product_snapshot.exists:
            update_payload['createdAt'] = firestore.SERVER_TIMESTAMP

        # Update nearestExpiry if new expiry date is earlier or if no current expiry
        if movement_data.get('expiryDate'):
            new_expiry_date_str = movement_data['expiryDate']
            current_expiry_str = product_data.get('nearestExpiry')
            
            should_update_expiry = False
            if not current_expiry_str: # No current expiry, so update
                should_update_expiry = True
            else:
                # Compare new expiry with current nearest expiry
                try:
                    new_expiry_dt = datetime.strptime(new_expiry_date_str, '%Y-%m-%d')
                    current_expiry_dt = datetime.strptime(current_expiry_str, '%Y-%m-%d')
                    if new_expiry_dt < current_expiry_dt:
                        should_update_expiry = True
                except ValueError:
                    # This case should ideally be caught by prior validation in the route.
                    # Logging here might be useful if it can still occur.
                    current_app.logger.warning(f"Invalid date format encountered for expiry date comparison in transaction for product {product_name}.")
                    pass # Silently ignore if format is bad, relying on route validation

            if should_update_expiry:
                update_payload['nearestExpiry'] = new_expiry_date_str
        
        # Set/update product data (merge=True creates if not exists, updates if exists)
        transaction.set(product_ref, update_payload, merge=True)
        return None # Indicates success

    elif movement_type == "scarico": # Product discharging
        if not product_snapshot.exists:
            raise ValueError("Product not found for discharge.") # Will be caught by caller
        
        current_quantity = product_data.get('quantity', 0)
        if current_quantity < quantity:
            raise ValueError("Insufficient stock.") # Will be caught by caller
        
        new_quantity = current_quantity - quantity
        # Update existing product's quantity and last updated user
        transaction.update(product_ref, {
            'quantity': new_quantity,
            'lastUpdatedBy': user_id
        })
        return None # Indicates success
    
    # Should not be reached if movementType is validated before calling
    raise ValueError("Invalid movement type in transaction")


# --- Inventory Movement Routes ---
@app.route('/movements', methods=['POST']) # Endpoint to record a new inventory movement
@login_required # Requires user to be logged in
def create_movement():
    """
    Records a new inventory movement (carico/scarico) and updates product stock.
    Expects a JSON payload with movement details (date, type, product, quantity, etc.).
    Validates input data thoroughly. Updates product stock via a Firestore transaction.
    """
    user_id = session['user_id'] # Get user ID from session
    data = request.get_json()

    # Validate JSON payload
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400 # Bad Request

    # Detailed validation for all required and optional fields
    # Ensures presence, correct data types, and valid values.
    required_fields = {"date": str, "movementType": str, "productName": str, "quantity": (int, float)}
    for field, expected_type in required_fields.items():
        value = data.get(field)
        if value is None: # Field is missing
            return jsonify({"error": f"Missing required field: {field}."}), 400
        if not isinstance(value, expected_type):
             # Special handling for quantity if it's a string that can be float
            if field == "quantity" and isinstance(value, str):
                try:
                    float(value) # check if convertible
                except ValueError:
                    return jsonify({"error": f"Invalid data type for {field}. Expected number, got '{type(value).__name__}'."}), 400
            else:
                return jsonify({"error": f"Invalid data type for {field}. Expected {expected_type}, got '{type(value).__name__}'."}), 400
        if isinstance(value, str) and not value.strip() and field in ["date", "movementType", "productName"]:
             return jsonify({"error": f"Field '{field}' must not be empty."}), 400
    
    product_name_stripped = data['productName'].strip()
    if not product_name_stripped:
        return jsonify({"error": "productName must not be empty or just whitespace."}), 400

    movement_type = data['movementType']
    if movement_type not in ["carico", "scarico"]:
        return jsonify({"error": "Invalid movementType. Must be 'carico' or 'scarico'."}), 400

    try:
        quantity = float(data['quantity'])
        if quantity <= 0:
            return jsonify({"error": "Quantity must be a positive number."}), 400
    except ValueError: # Handles if float conversion failed after initial type check (e.g. for string quantity)
        return jsonify({"error": "Invalid quantity. Must be a number."}), 400

    unit_price = None
    raw_unit_price = data.get('unitPrice')
    if raw_unit_price is not None: # unitPrice is optional
        if not isinstance(raw_unit_price, (int, float, str)): # Allow string for float conversion
             return jsonify({"error": "Invalid data type for unitPrice."}), 400
        try:
            parsed_unit_price = float(raw_unit_price)
            if parsed_unit_price <= 0:
                return jsonify({"error": "unitPrice, if provided, must be a positive number."}), 400
            unit_price = parsed_unit_price
        except ValueError:
            return jsonify({"error": "Invalid unitPrice. Must be a number if provided."}), 400
        
    total_value = 0
    if movement_type == "carico" and unit_price is not None:
        total_value = quantity * unit_price
    
    # Date validation
    date_fields_to_validate = {'date': data['date'], 'expiryDate': data.get('expiryDate')}
    for field_name, date_str in date_fields_to_validate.items():
        if date_str: # expiryDate is optional
            if not isinstance(date_str, str):
                 return jsonify({"error": f"{field_name} must be a string in YYYY-MM-DD format."}), 400
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": f"Invalid {field_name} format. Use YYYY-MM-DD."}), 400

    # Optional fields type check (supplier, notes)
    supplier = data.get("supplier")
    if supplier is not None and not isinstance(supplier, str):
        return jsonify({"error": "Invalid data type for supplier. Expected string."}), 400
    
    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "Invalid data type for notes. Expected string."}), 400

    movement_record = {
        "userId": user_id,
        "date": data['date'],
        "supplier": supplier.strip() if supplier else None,
        "movementType": movement_type,
        "productName": product_name_stripped,
        "quantity": quantity,
        "unitPrice": unit_price,
        "totalValue": total_value,
        "expiryDate": data.get("expiryDate") if data.get("expiryDate") else None, # Ensure empty string becomes null
        "notes": notes.strip() if notes else None,
        "createdAt": firestore.SERVER_TIMESTAMP
    }

    try:
        product_ref = db.collection('products').document(product_name_stripped)
        
        # Execute the transactional update: update_product_stock_transactional can raise ValueError
        db.transaction().run(update_product_stock_transactional, product_ref, movement_record, user_id)

        new_movement_ref = db.collection('movements').add(movement_record)
        return jsonify({"message": "Movement registered successfully.", "movementId": new_movement_ref[1].id}), 201

    except ValueError as ve: 
        # Specific errors from transaction or validation (like "Insufficient stock.")
        return jsonify({"error": str(ve)}), 400
    except auth.FirebaseAuthException as e:
        # Catch potential Firebase errors (less likely here unless custom token use in transaction)
        current_app.logger.error(f"Firebase error during movement processing: {e}", exc_info=True)
        return jsonify({"error": "A Firebase error occurred while processing the movement."}), 500 # Internal Server Error
    except Exception as e:
        # Catch any other unhandled errors
        current_app.logger.error(f"Unhandled exception during movement creation: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500 # Internal Server Error

# --- Dashboard Data Endpoint ---
@app.route('/dashboard-data', methods=['GET']) # Endpoint to fetch data for the main dashboard
@login_required # Requires user to be logged in
def get_dashboard_data():
    """
    Fetches a summary of all products for display on the dashboard.
    Includes product name, quantity, nearest expiry date, and last updated user.
    """
    try:
        products_ref = db.collection('products') # Reference to the 'products' collection
        all_products_docs = products_ref.stream() # Stream all product documents

        dashboard_items = []
        for doc in all_products_docs:
            product_data = doc.to_dict()
            item = {
                # Use productName field, fallback to document ID if field is missing
                "productName": product_data.get("productName", doc.id), 
                "quantity": product_data.get("quantity"),
                # Default to None (null in JSON) if nearestExpiry is not set
                "nearestExpiry": product_data.get("nearestExpiry", None), 
                "lastUpdatedBy": product_data.get("lastUpdatedBy")
            }
            # Basic data integrity check before adding to response
            if item["productName"] is not None and item["quantity"] is not None and item["lastUpdatedBy"] is not None:
                dashboard_items.append(item)
            else:
                # Log if a product document is missing essential data for the dashboard
                current_app.logger.warning(f"Product document {doc.id} missing essential data for dashboard: {item}")

        return jsonify(dashboard_items), 200 # OK
    except Exception as e:
        # Log any errors during data fetching
        current_app.logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred while fetching dashboard data."}), 500 # Internal Server Error

# --- Product Detail Endpoint ---
@app.route('/products/<string:product_name>', methods=['GET']) # Endpoint for specific product details
@login_required # Requires user to be logged in
def get_product_detail(product_name_from_url):
    """
    Fetches detailed information for a specific product, including its current stock,
    average unit price (from "carico" movements), expiration date history, and all its movements.
    The 'product_name' is passed as a URL parameter.
    """
    # Validate product_name from URL parameter
    if not product_name_from_url or not product_name_from_url.strip():
        return jsonify({"error": "Product name parameter is required and cannot be empty."}), 400 # Bad Request
    
    # Use stripped version for consistent lookup. Assumes product names are stored stripped or handled as such.
    product_name_lookup = product_name_from_url.strip()

    try:
        # 1. Fetch Product Summary from 'products' collection
        product_ref = db.collection('products').document(product_name_lookup)
        product_snapshot = product_ref.get()

        if not product_snapshot.exists:
            return jsonify({"error": f"Product '{product_name_lookup}' not found."}), 404 # Not Found

        product_data = product_snapshot.to_dict()
        # Validate and get current stock quantity
        total_quantity_in_stock = product_data.get('quantity', 0)
        if not isinstance(total_quantity_in_stock, (int, float)):
             current_app.logger.warning(f"Product '{product_name_lookup}' has invalid quantity type in DB: {total_quantity_in_stock}")
             total_quantity_in_stock = 0 # Default to 0 or handle as error

        # 2. Fetch All Movements for this product from 'movements' collection
        # Ordered by date descending to show recent movements first.
        movements_query = db.collection('movements') \
                            .where('productName', '==', product_name_lookup) \
                            .order_by('date', direction=firestore.Query.DESCENDING) # type: ignore
        movements_docs = movements_query.stream()

        movements_list = []
        total_value_of_loads = 0
        total_quantity_of_loads = 0
        expiration_dates_set = set()

        for doc in movements_docs:
            movement = doc.to_dict()
            movement_id = doc.id 

            # Convert Firestore Timestamps (like 'createdAt') to ISO strings
            if 'createdAt' in movement and hasattr(movement['createdAt'], 'isoformat'):
                movement['createdAt'] = movement['createdAt'].isoformat()
            else: # If createdAt is missing or not a timestamp, ensure it's null or a placeholder
                movement['createdAt'] = None 
            
            movement['movementId'] = movement_id
            movements_list.append(movement)

            if movement.get('movementType') == 'carico':
                unit_price = movement.get('unitPrice')
                quantity = movement.get('quantity')
                # Ensure these are numbers before calculation
                if isinstance(unit_price, (int, float)) and unit_price > 0 and \
                   isinstance(quantity, (int, float)) and quantity > 0:
                    total_value_of_loads += unit_price * quantity
                    total_quantity_of_loads += quantity
                
                expiry_date = movement.get('expiryDate')
                if expiry_date and isinstance(expiry_date, str) and expiry_date.strip():
                    expiration_dates_set.add(expiry_date.strip())
        
        average_unit_price = 0.0
        if total_quantity_of_loads > 0:
            average_unit_price = total_value_of_loads / total_quantity_of_loads
        
        sorted_expiration_dates = sorted(list(expiration_dates_set))


        response_data = {
            "productName": product_name_lookup, # Use the name used for lookup
            "totalQuantityInStock": total_quantity_in_stock,
            "averageUnitPrice": round(average_unit_price, 2), # Round to 2 decimal places
            "expirationDateHistory": sorted_expiration_dates,
            "movements": movements_list
        }

        return jsonify(response_data), 200
    
    except auth.FirebaseAuthException as e:
        # Catch potential Firebase errors during database operations
        current_app.logger.error(f"Firebase error fetching product details for {product_name_lookup}: {e}", exc_info=True)
        return jsonify({"error": "A Firebase error occurred while fetching product details."}), 500 # Internal Server Error
    except Exception as e:
        # Catch any other unhandled errors
        current_app.logger.error(f"Error fetching product details for {product_name_lookup}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500 # Internal Server Error

# --- Global Error Handler ---
@app.errorhandler(Exception) # Registers this function to handle all unhandled exceptions
def handle_generic_exception(e):
    """
    Global error handler for the Flask application.
    Catches any unhandled exceptions from routes.
    If the exception is an HTTPException (e.g., 404, 405), it uses its code and description.
    Otherwise, it logs the error and returns a generic 500 Internal Server Error.
    """
    # If the exception is an HTTPException (e.g., Flask's own 404, 405 errors)
    if isinstance(e, HTTPException):
        return jsonify(error=e.description), e.code

    # For any other non-HTTPException, log it and return a generic 500 error
    current_app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "An unexpected internal server error occurred."}), 500 # Internal Server Error


# --- Main Application Runner ---
if __name__ == '__main__':
    # Enables debug mode for development, which provides more detailed error pages
    # and auto-reloads the server when code changes.
    # For production, use a proper WSGI server (e.g., Gunicorn, uWSGI) and set debug=False.
    app.run(debug=True)
