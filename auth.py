import pyotp, qrcode
from io import BytesIO
import base64
import hashlib
from werkzeug.security import check_password_hash, generate_password_hash
from db import query_db, execute_db

def get_user_by_username(username):
    return query_db("SELECT * FROM users WHERE username = %s", (username,), one=True)

def create_user(username, password, role, email=None):
    password_hash = generate_password_hash(password)
    return execute_db("INSERT INTO users (username, password_hash, role, email) VALUES (%s, %s, %s, %s)",
                     (username, password_hash, role, email))

def verify_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

def generate_2fa_secret():
    return pyotp.random_base32()

def get_2fa_uri(username, secret):
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name="PatientMonitor")

def generate_qr_code(uri):
    img = qrcode.make(uri)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def verify_2fa_token(secret, token):
    totp = pyotp.TOTP(secret)
    return totp.verify(token)
