from jose import jwt
from datetime import datetime, timedelta
from typing import Optional

from jose.exceptions import ExpiredSignatureError, JWTError

SECRET_KEY = "supersecret"
ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 1

def create_jwt(address: str) -> str:
    payload = {
        "sub": address,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt(token: str) -> Optional[str]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (ExpiredSignatureError, JWTError) as e:
        # print("JWT decode error:", str(e))  # ✅ Debug print
        return None