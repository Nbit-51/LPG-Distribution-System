import warnings
warnings.filterwarnings("ignore")
from passlib.context import CryptContext
import mysql.connector

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

conn = mysql.connector.connect(
    host="localhost", port=3306,
    database="lpg_distribution",
    user="root", password="11362"
)
cursor = conn.cursor(dictionary=True)

cursor.execute("SELECT admin_id, username, role, is_active FROM admins")
admins = cursor.fetchall()
print("Current admins:", admins)

new_hash = pwd_context.hash("admin123")
cursor.execute("UPDATE admins SET password_hash=%s WHERE is_active=TRUE", (new_hash,))
conn.commit()
print("Password reset to 'admin123' for all active admins")

cursor.close()
conn.close()
