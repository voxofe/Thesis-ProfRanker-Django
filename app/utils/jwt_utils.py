import jwt
from django.conf import settings
from datetime import datetime, timedelta, timezone

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def generate_jwt(user_id):
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "exp": now + timedelta(hours=24),
        "iat": now
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None