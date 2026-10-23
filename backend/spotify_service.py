import os

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from spotipy.cache_handler import CacheHandler


class NoCacheHandler(CacheHandler):
    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        self.token_info = token_info

load_dotenv()

SPOTIFY_SCOPES = (
    "user-read-currently-playing "
    "user-read-playback-state "
    "user-modify-playback-state"
)


def create_spotify_auth(redirect_uri: str):
    return SpotifyPKCE(
        cache_handler=NoCacheHandler(),
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPES,
        open_browser=False,
    )

def get_spotify_user(access_token: str):
    spotify = spotipy.Spotify(auth=access_token)
    return spotify.current_user()

def refresh_spotify_token(refresh_token: str) -> dict:
    auth = create_spotify_auth(
        "http://127.0.0.1:8001/auth/callback"
    )

    auth.refresh_access_token(refresh_token)

    token_info = getattr(auth.cache_handler, "token_info", None)

    if not token_info or not token_info.get("access_token"):
        raise RuntimeError("Spotify token refresh failed")

    return token_info

from datetime import datetime, timedelta, timezone

from backend.security import decrypt_token, encrypt_token


def get_valid_spotify_token(user, db):
    if not user.access_token_encrypted or not user.refresh_token_encrypted:
        raise RuntimeError("Spotify account needs to reconnect")

    now = datetime.now(timezone.utc)

    if user.token_expires_at is not None:
        expires_at = user.token_expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at > now + timedelta(minutes=5):
            return decrypt_token(user.access_token_encrypted)

    refresh_token = decrypt_token(user.refresh_token_encrypted)
    token_info = refresh_spotify_token(refresh_token)

    user.access_token_encrypted = encrypt_token(token_info["access_token"])

    if token_info.get("refresh_token"):
        user.refresh_token_encrypted = encrypt_token(
            token_info["refresh_token"]
        )

    user.token_expires_at = datetime.fromtimestamp(
        token_info["expires_at"],
        tz=timezone.utc,
    )

    db.commit()

    return token_info["access_token"]