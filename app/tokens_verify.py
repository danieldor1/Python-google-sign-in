#################################################
# AUTH TOKEN
#################################################
import jwt

from typing import Optional
from jwt.exceptions import InvalidTokenError

from app.interactions_db import SessionLocal
from app.database import GoogleUser
from app.config import KeysManagerInvokator

# LOGINS TOKENS 
ENCRYPTION_ALGORITHM_SECRET_KEY = KeysManagerInvokator.encryption_secret_key.value
ENCRYPTION_ALGORITHM = KeysManagerInvokator.encryption_algorithm.value


async def verify_user(token:str) -> Optional[GoogleUser]:

    db = SessionLocal()

    try:

        decoded_token = jwt.decode(
            token,
            key=ENCRYPTION_ALGORITHM_SECRET_KEY,
            algorithms=ENCRYPTION_ALGORITHM,
        )

        email = decoded_token.get('user_email')

        if email:
            user = db.query(GoogleUser).filter(
                GoogleUser.email == email).first()
            if not user:
                return f"invalid"

        return f"valid"

    except jwt.ExpiredSignatureError:
        return f"expired"

    except (
        InvalidTokenError,
        jwt.InvalidIssuerError,
        jwt.InvalidAudienceError
    ):
        return f"invalid"
