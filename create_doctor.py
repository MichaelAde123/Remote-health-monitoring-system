import mysql.connector
import pyotp
import qrcode
from werkzeug.security import generate_password_hash

# Connect to MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',  # Set your DB password here
    database='project4db'
)
cursor = conn.cursor()

# Doctor user details
user_id = 999  # unique ID not conflicting with patient IDs
username = 'drjane'
password = 'doc123'
role = 'doctor'
email = 'drjane@example.com'

# Generate 2FA secret and hashed password
secret = pyotp.random_base32()
hashed_password = generate_password_hash(password)

# Insert or update doctor user
cursor.execute("""
INSERT INTO users (id, username, password_hash, role, email, two_factor_secret)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    password_hash = VALUES(password_hash),
    two_factor_secret = VALUES(two_factor_secret)
""", (user_id, username, hashed_password, role, email, secret))
conn.commit()

# Generate 2FA QR code
otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="RemoteHealthApp")
qrcode.make(otp_uri).show()

# Display credentials
print("\n✅ Doctor user created!")
print(f"Username: {username}")
print(f"Password: {password}")
print("Scan the QR code above using Google Authenticator.")

cursor.close()
conn.close()
