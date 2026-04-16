import requests
from src.config import FIREBASE_API_KEY

def sign_in_with_email_password(email, password):
    """Sign in using Firebase REST API."""
    if not FIREBASE_API_KEY:
        return {"error": "Missing Firebase API Key"}

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    try:
        res = requests.post(url, json=payload, timeout=15)
        data = res.json()
        if "error" in data:
            return {"error": data["error"].get("message", "Login failed")}
        return {
            "token": data["idToken"],
            "email": data["email"],
            "localId": data["localId"]
        }
    except Exception as e:
        return {"error": str(e)}


def sign_up_with_email_password(email: str, password: str) -> dict:
    """Create a Firebase user via REST signUp.

    Returns the same token shape as sign_in_with_email_password (idToken/idToken-like).
    """
    if not FIREBASE_API_KEY:
        return {"error": "Missing Firebase API Key"}

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}

    try:
        res = requests.post(url, json=payload, timeout=15)
        data = res.json()
        if "error" in data:
            return {"error": data["error"].get("message", "Sign up failed")}
        return {
            "token": data.get("idToken"),
            "email": data.get("email"),
            "localId": data.get("localId"),
        }
    except Exception as e:
        return {"error": str(e)}

def get_user_info(id_token):
    """Get user info from token using Firebase REST API"""
    if not FIREBASE_API_KEY:
        return None

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}"
    try:
        res = requests.post(url, json={"idToken": id_token}, timeout=15)
        data = res.json()
        if "users" in data and len(data["users"]) > 0:
            return data["users"][0]
        return None
    except Exception:
        return None


def sign_in_with_google_id_token(id_token: str) -> dict:
    """Accept an ID token produced by the Firebase JS frontend and verify it via Firebase REST."""
    user_info = get_user_info(id_token)
    if not user_info:
        return {"error": "Unable to validate Google sign-in token"}
    return {
        "token": id_token,
        "email": user_info.get("email"),
        "localId": user_info.get("localId"),
        "provider": "google",
    }

def send_password_reset_email(email: str) -> dict:
    """Send a password reset email using Firebase REST API."""
    if not FIREBASE_API_KEY:
        return {"error": "Missing Firebase API Key"}

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email
    }
    
    try:
        res = requests.post(url, json=payload, timeout=15)
        data = res.json()
        if "error" in data:
            return {"error": data["error"].get("message", "Failed to send reset email")}
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
