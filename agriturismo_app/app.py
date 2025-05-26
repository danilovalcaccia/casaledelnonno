# --- Core Flask and Firebase Imports ---
import os
import json
from flask import Flask, request, jsonify, session, current_app
# Non importare firebase_admin qui inizialmente, lo faremo nel try-except
from functools import wraps
from datetime import datetime
import re
from werkzeug.exceptions import HTTPException

# --- Firebase Admin SDK Initialization (Modificato per Vercel) ---
firebase_app_initialized = False
db = None # Inizializza db a None

try:
    import firebase_admin # Importiamo firebase_admin qui
    from firebase_admin import credentials, initialize_app, firestore, auth # E gli specifici moduli qui

    firebase_sdk_json_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON_CONTENT')
    if not firebase_sdk_json_str:
        print("ATTENZIONE: La variabile d'ambiente FIREBASE_SERVICE_ACCOUNT_JSON_CONTENT non è impostata.")
        if os.path.exists("serviceAccountKey.json"):
            print("Trovato serviceAccountKey.json locale come fallback.")
            cred = credentials.Certificate("serviceAccountKey.json")
        else:
            raise ValueError("Credenziali Firebase non trovate: FIREBASE_SERVICE_ACCOUNT_JSON_CONTENT non impostata e serviceAccountKey.json non trovato localmente.")
    else:
        try:
            cred_json = json.loads(firebase_sdk_json_str)
            cred = credentials.Certificate(cred_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Errore nel decodificare FIREBASE_SERVICE_ACCOUNT_JSON_CONTENT: {e}")

    if not firebase_admin._apps:
        initialize_app(cred)
        print("Firebase Admin SDK inizializzato con successo.")
        firebase_app_initialized = True
    else:
        print("Firebase Admin SDK già inizializzato.")
        firebase_app_initialized = True

    if firebase_app_initialized:
        db = firestore.client() # db viene definito SOLO se l'inizializzazione ha successo
        print("Firestore client creato con successo.")
    else:
        print("ERRORE: Firebase SDK non inizializzato, db non può essere creato.")

except Exception as e:
    print(f"ERRORE CRITICO DURANTE L'INIZIALIZZAZIONE DI FIREBASE ADMIN SDK (blocco try principale): {e}")
# --- Fine Blocco Inizializzazione Firebase Modificato ---

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'mia_chiave_segreta_default_locale_da_cambiare_in_prod')
if app.secret_key == 'mia_chiave_segreta_default_locale_da_cambiare_in_prod' and os.environ.get('VERCEL_ENV') == 'production':
    print("ATTENZIONE CRITICA: FLASK_SECRET_KEY sta usando il valore di default IN PRODUZIONE!")

# --- Utility Decorator: Login Required ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        if db is None:
            return jsonify({"error": "Servizio database non disponibile al momento."}), 503
        return f(*args, **kwargs)
    return decorated_function

# --- Basic Routes ---
@app.route('/')
def hello_world():
    return 'Flask App is Running!'

# --- Authentication Routes ---
@app.route('/auth/register', methods=['POST'])
def register():
    if db is None: return jsonify({"error": "Servizio database non disponibile."}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email format."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    try:
        user = auth.create_user(email=email, password=password)
        user_info = {'email': user.email, 'createdAt': firestore.SERVER_TIMESTAMP}
        db.collection('users').document(user.uid).set(user_info)
        return jsonify({"message": "User registered successfully.", "uid": user.uid}), 201
    except auth.EmailAlreadyExistsError:
        return jsonify({"error": "This email address is already registered."}), 409
    except auth.FirebaseAuthException as e:
        current_app.logger.error(f"Firebase auth error during registration: {e}")
        return jsonify({"error": "An error occurred during registration with authentication service."}), 500
    except Exception as e:
        current_app.logger.error(f"Unhandled exception during registration: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/auth/sessionLogin', methods=['POST'])
def session_login():
    if not firebase_app_initialized:
         return jsonify({"error": "Servizio di autenticazione non disponibile."}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400
    id_token = data.get('idToken')
    if not id_token or not isinstance(id_token, str):
        return jsonify({"error": "ID token is required and must be a string."}), 400
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        session['user_id'] = uid
        return jsonify({"message": "Session login successful."}), 200
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid or expired ID token."}), 401
    except auth.UserDisabledError:
        return jsonify({"error": "This user account has been disabled."}), 403
    except auth.FirebaseAuthException as e:
        current_app.logger.error(f"Firebase auth error during session login: {e}")
        return jsonify({"error": "Authentication failed due to a Firebase error."}), 500
    except Exception as e:
        current_app.logger.error(f"Unhandled exception during session login: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        return jsonify({"isLoggedIn": True, "user_id": session['user_id']}), 200
    else:
        return jsonify({"isLoggedIn": False}), 200

@app.route('/protected_example')
@login_required
def protected_example():
    return jsonify({"message": "This is a protected area", "user_id": session['user_id']})

@firestore.transactional
def update_product_stock_transactional(transaction, product_ref, movement_data, user_id):
    product_snapshot = transaction.get(product_ref)
    product_data = product_snapshot.to_dict() if product_snapshot.exists else {}
    movement_type = movement_data['movementType']
    quantity = movement_data['quantity']
    product_name = movement_data['productName']
    if movement_type == "carico":
        new_quantity = product_data.get('quantity', 0) + quantity
        update_payload = {
            'quantity': new_quantity,
            'lastUpdatedBy': user_id,
            'productName': product_name
        }
        if not product_snapshot.exists:
            update_payload['createdAt'] = firestore.SERVER_TIMESTAMP
        if movement_data.get('expiryDate'):
            new_expiry_date_str = movement_data['expiryDate']
            current_expiry_str = product_data.get('nearestExpiry')
            should_update_expiry = False
            if not current_expiry_str:
                should_update_expiry = True
            else:
                try:
                    new_expiry_dt = datetime.strptime(new_expiry_date_str, '%Y-%m-%d')
                    current_expiry_dt = datetime.strptime(current_expiry_str, '%Y-%m-%d')
                    if new_expiry_dt < current_expiry_dt:
                        should_update_expiry = True
                except ValueError:
                    current_app.logger.warning(f"Invalid date format for expiry date in transaction for {product_name}.")
                    pass
            if should_update_expiry:
                update_payload['nearestExpiry'] = new_expiry_date_str
        transaction.set(product_ref, update_payload, merge=True)
        return None
    elif movement_type == "scarico":
        if not product_snapshot.exists:
            raise ValueError("Product not found for discharge.")
        current_quantity = product_data.get('quantity', 0)
        if current_quantity < quantity:
            raise ValueError("Insufficient stock.")
        new_quantity = current_quantity - quantity
        transaction.update(product_ref, {
            'quantity': new_quantity,
            'lastUpdatedBy': user_id
        })
        return None
    raise ValueError("Invalid movement type in transaction")

@app.route('/movements', methods=['POST'])
@login_required
def create_movement():
    user_id = session['user_id']
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    required_fields = {"date": str, "movementType": str, "productName": str, "quantity": (int, float)}
    for field, expected_type in required_fields.items():
        value = data.get(field)
        if value is None:
            return jsonify({"error": f"Missing required field: {field}."}), 400
        if not isinstance(value, expected_type):
            if field == "quantity" and isinstance(value, str):
                try:
                    float(value)
                except ValueError:
                    return jsonify({"error": f"Invalid data type for {field}. Expected number."}), 400
            else:
                return jsonify({"error": f"Invalid data type for {field}. Expected {expected_type}."}), 400
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
    except ValueError:
        return jsonify({"error": "Invalid quantity. Must be a number."}), 400
    unit_price = None
    raw_unit_price = data.get('unitPrice')
    if raw_unit_price is not None:
        if not isinstance(raw_unit_price, (int, float, str)):
             return jsonify({"error": "Invalid data type for unitPrice."}), 400
        try:
            parsed_unit_price = float(raw_unit_price)
            if parsed_unit_price < 0:
                 return jsonify({"error": "unitPrice, if provided, must not be negative."}), 400
            unit_price = parsed_unit_price
        except ValueError:
            return jsonify({"error": "Invalid unitPrice. Must be a number if provided."}), 400
    total_value = 0
    if movement_type == "carico" and unit_price is not None and unit_price > 0:
        total_value = quantity * unit_price
    date_fields_to_validate = {'date': data['date'], 'expiryDate': data.get('expiryDate')}
    for field_name, date_str in date_fields_to_validate.items():
        if date_str:
            if not isinstance(date_str, str):
                 return jsonify({"error": f"{field_name} must be a string in YYYY-MM-DD format."}), 400
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": f"Invalid {field_name} format. Use YYYY-MM-DD."}), 400
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
        "expiryDate": data.get("expiryDate") if data.get("expiryDate") else None,
        "notes": notes.strip() if notes else None,
        "createdAt": firestore.SERVER_TIMESTAMP
    }
    try:
        product_ref = db.collection('products').document(product_name_stripped)
        if db is None:
            raise Exception("Firestore client (db) is not initialized.")
        db.transaction().run(update_product_stock_transactional, product_ref, movement_record, user_id)
        new_movement_ref = db.collection('movements').add(movement_record)
        return jsonify({"message": "Movement registered successfully.", "movementId": new_movement_ref[1].id}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except auth.FirebaseAuthException as e:
        current_app.logger.error(f"Firebase error during movement processing: {e}", exc_info=True)
        return jsonify({"error": "A Firebase error occurred while processing the movement."}), 500
    except Exception as e:
        current_app.logger.error(f"Unhandled exception during movement creation: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/dashboard-data', methods=['GET'])
@login_required
def get_dashboard_data():
    try:
        products_ref = db.collection('products')
        all_products_docs = products_ref.stream()
        dashboard_items = []
        for doc in all_products_docs:
            product_data = doc.to_dict()
            item = {
                "productName": product_data.get("productName", doc.id),
                "quantity": product_data.get("quantity"),
                "nearestExpiry": product_data.get("nearestExpiry", None),
                "lastUpdatedBy": product_data.get("lastUpdatedBy")
            }
            if item["productName"] is not None and item["quantity"] is not None and item["lastUpdatedBy"] is not None:
                dashboard_items.append(item)
            else:
                current_app.logger.warning(f"Product document {doc.id} missing essential data for dashboard: {item}")
        return jsonify(dashboard_items), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred while fetching dashboard data."}), 500

@app.route('/products/<string:product_name_from_url>', methods=['GET'])
@login_required
def get_product_detail(product_name_from_url):
    if not product_name_from_url or not product_name_from_url.strip():
        return jsonify({"error": "Product name parameter is required and cannot be empty."}), 400
    product_name_lookup = product_name_from_url.strip()
    try:
        product_ref = db.collection('products').document(product_name_lookup)
        product_snapshot = product_ref.get()
        if not product_snapshot.exists:
            return jsonify({"error": f"Product '{product_name_lookup}' not found."}), 404
        product_data = product_snapshot.to_dict()
        total_quantity_in_stock = product_data.get('quantity', 0)
        if not isinstance(total_quantity_in_stock, (int, float)):
             current_app.logger.warning(f"Product '{product_name_lookup}' has invalid quantity type in DB: {total_quantity_in_stock}")
             total_quantity_in_stock = 0
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
            if 'createdAt' in movement and hasattr(movement['createdAt'], 'isoformat'):
                movement['createdAt'] = movement['createdAt'].isoformat()
            else:
                movement['createdAt'] = None
            movement['movementId'] = movement_id
            movements_list.append(movement)
            if movement.get('movementType') == 'carico':
                unit_price = movement.get('unitPrice')
                quantity = movement.get('quantity')
                if isinstance(unit_price, (int, float)) and unit_price >= 0 and \
                   isinstance(quantity, (int, float)) and quantity > 0:
                    if unit_price > 0 :
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
            "productName": product_name_lookup,
            "totalQuantityInStock": total_quantity_in_stock,
            "averageUnitPrice": round(average_unit_price, 2),
            "expirationDateHistory": sorted_expiration_dates,
            "movements": movements_list
        }
        return jsonify(response_data), 200
    except auth.FirebaseAuthException as e:
        current_app.logger.error(f"Firebase error fetching product details for {product_name_lookup}: {e}", exc_info=True)
        return jsonify({"error": "A Firebase error occurred while fetching product details."}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching product details for {product_name_lookup}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500

@app.errorhandler(Exception)
def handle_generic_exception(e):
    if isinstance(e, HTTPException):
        return jsonify(error=e.description), e.code
    current_app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "An unexpected internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True)
Dopo aver aggiornato app.py con questo codice:

Assicurati che casaledelnonno/agriturismo_app/requirements.txt esista e contenga:
Flask==2.2.0
firebase-admin==6.0.1
Werkzeug==2.2.2
gunicorn==20.1.0
Assicurati che casaledelnonno/agriturismo_app/vercel.json esista e contenga:
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "15mb", "runtime": "python3.9" }
    }
  ],
  "routes": [
    { "src": "/static/(.*)", "dest": "/static/$1" },
    { "src": "/(.*)", "dest": "app.py" }
  ]
}
