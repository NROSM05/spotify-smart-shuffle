
import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

encryption_key = os.environ["TOKEN_ENCRYPTION_KEY"].encode()
fernet = Fernet(encryption_key)


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode()
