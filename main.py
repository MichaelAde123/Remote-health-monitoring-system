import mysql.connector
import pyotp
import qrcode
from werkzeug.security import generate_password_hash

# Connect to MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='project4db'
)
cursor = conn.cursor()

# Generate hashed password and 2FA
username = '1'  # same as patient_id
password_hash = generate_password_hash('123')  # patient 1 password = 123
role = 'patient'
email = 'mikeadebayo600@gmaiil.com'
secret = pyotp.random_base32()

# Create the patient user
cursor.execute("""
INSERT INTO users (id, username, password_hash, role, email, two_factor_secret)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    password_hash = VALUES(password_hash),
    two_factor_secret = VALUES(two_factor_secret)
""", (1, username, password_hash, role, email, secret))
conn.commit()

# Generate and show QR code
uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="RemoteHealthApp")
qrcode.make(uri).show()

print("\n✅ Patient 1 created!")
print("Username:", username)
print("Password: 123")
print("Scan the QR code with Google Authenticator.")

cursor.close()
conn.close()
