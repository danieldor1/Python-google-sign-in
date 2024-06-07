import os

from enum import Enum
from dotenv import load_dotenv
load_dotenv()


class KeysManagerInvokator(Enum):
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_url = os.getenv("GOOGLE_REDIRECT_URI")
    encryption_secret_key = os.getenv("SECRET_KEY")
    encryption_algorithm = os.getenv("ENCRYPTION_ALGORITHM")